"""
Diagnosis Agent v3 — 本体驱动 + 真实数据 + LLM 分析(统一接口) + 反省增强

工作流:
  1. 订阅 BoardService 实际 topic 格式
  2. 加载 ontology_model 约束 + 推理（导入新的 run_checks / run_inferences）
  3. MQTT 消息作为数据源 -> 真实约束检查
  4. LLM 分析异常根因 + 建议（复用统一 LLM Provider 工厂）
  5. 通知周期 + 手动触发协调
  6. 发布诊断帖子到 board/diagnosis/post/

启动:
  SKILL_LLM_ENABLE=1 LLM_API_KEY=... python -m tools.diagnosis_agent
"""

import sys
import os
import time
import json
import statistics
import collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Mqtt_bbs_client.board_client import BoardClient
from Mqtt_bbs_client.client import BBSClient
from tools.ontology_model import (
    diagnose_system,
)
from tools._llm import DiagnosisLLM


class DiagnosisAgent:

    def __init__(self):
        self.board = "agent-diagnosis"
        self.agent_id = "diagnosis_agent"
        self.bbs = BoardClient(self.agent_id, board=self.board)
        self.client = BBSClient("diagnosis_agent_listener")
        self.token = None
        self._running = False

        # 数据采集
        self._health_data = []
        self._node_status = {}
        self._error_events = []
        self._latency_samples = collections.deque(maxlen=60)

        # LLM — 统一接口模块
        self._llm = DiagnosisLLM()

    def _llm_analysis(self):
        """LLM 分析当前系统状态"""
        issues = []

        # 汇总状态
        context_lines = ["=== 系统状态摘要 ==="]
        context_lines.append(f"运行中服务: {sum(1 for h in self._health_data if h.get('status') in ('ok', 'ready'))}/{len(self._health_data)}")
        context_lines.append(f"在线节点: {len([n for n, s in self._node_status.items() if isinstance(s.get('status'), dict) and s['status'].get('status') != 'offline'])}")
        context_lines.append(f"错误事件 (5分钟): {len([e for e in self._error_events if time.time() - e['time'] < 300])}")

        if self._health_data:
            context_lines.append(f"最新 healthcheck: {json.dumps(self._health_data[-1], ensure_ascii=False)}")

        context = "\n".join(context_lines)
        analysis = self._llm.analyze(context)

        if analysis and "LLM 不可用" not in analysis and "失败" not in analysis:
            issues.append({
                "type": "llm_analysis", "severity": "info",
                "source": "llm", "component": "system",
                "status": "analyzed",
                "detail": "LLM 分析完成",
                "llm": analysis,
                "count": 1
            })

        return issues

    def start(self):
        """启动诊断 Agent — 订阅 agent/bbs/ topic 格式"""
        self.client.connect()
        self.bbs.connect()

        self.board = self.bbs.register(self.agent_id, "diagnosis_agent")

        # 订阅数据源 — agent/bbs/ topic 格式 (对齐 Rust 版)
        self.client.subscribe("agent/bbs/+/healthcheck/response", self._on_healthcheck)
        self.client.subscribe("agent/bbs/+/node/status", self._on_node_status)
        self.client.subscribe("agent/bbs/+/events/error", self._on_error_event)

        print(f"[Diagnosis v3] 注册成功, board={self.board}")
        print("[Diagnosis v3] 数据源: healthcheck / node-status / error-events (agent/bbs/)")
        print(f"[Diagnosis v3] LLM: {'启用' if self._llm.available else '未启用(规则降级)'}")

        self._running = True
        time.sleep(2)
        while self._running:
            self._run_once()
            time.sleep(60)  # 每 60 秒诊断一次

    def stop(self):
        self._running = False
        self.client.disconnect()
        self.bbs.disconnect()

    def _on_healthcheck(self, topic, payload):
        """采集 healthcheck 响应"""
        if isinstance(payload, dict):
            self._health_data.append({
                "time": time.time(),
                "component": topic.split('/')[3],  # agent/bbs/{board}/healthcheck/response
                "status": payload.get("status"),
                "mqtt": payload.get("mqtt"),
                "db": payload.get("db")
            })
            if len(self._health_data) > 120:
                self._health_data = self._health_data[-120:]

    def _on_node_status(self, topic, payload):
        """采集节点状态"""
        node_id = topic.split('/')[1]
        self._node_status[node_id] = {
            "status": payload,
            "time": time.time()
        }

    def _on_error_event(self, topic, payload):
        """采集错误事件"""
        self._error_events.append({
            "time": time.time(),
            "topic": topic,
            "payload": payload
        })
        if len(self._error_events) > 50:
            self._error_events = self._error_events[-50:]

    def _run_once(self):
        """一次诊断周期 — 使用 ontology_model 的 diagnose_system()"""
        print(f"\n[Diagnosis] ====== 周期 ({time.strftime('%H:%M:%S')}) ======")

        issues = []

        # 1. 运行本体模型的约束检查
        ontology_result = diagnose_system()
        for check in ontology_result.get("checks", []):
            issues.append({
                "type": "constraint_violation",
                "severity": check.get("severity", "warning"),
                "source": "ontology",
                "component": check.get("name", "system"),
                "status": "violated",
                "detail": check.get("description", ""),
                "llm": "",
                "count": 1
            })
        for inference in ontology_result.get("inferences", []):
            issues.append({
                "type": "inference_match",
                "severity": "info",
                "source": "ontology",
                "component": "system",
                "status": "suggested",
                "detail": inference.get("conclusion", "") + " -> " + inference.get("action", ""),
                "llm": "",
                "count": 1
            })

        # 2. 真实数据约束检查
        issues += self._check_real_data()

        # 3. LLM 分析
        if self._llm.available:
            issues += self._llm_analysis()

        # 4. 发布诊断帖子
        for issue in issues:
            content = json.dumps({
                "type": issue["type"],
                "severity": issue["severity"],
                "source": issue["source"],
                "component": issue.get("component", "system"),
                "status": issue.get("status", "degraded"),
                "detail": issue["detail"],
                "llm_analysis": issue.get("llm", ""),
                "evidence_count": issue.get("count", 1),
                "timestamp": time.time()
            })
            self.bbs.post(content, self.token)
            print(f"  [{issue['severity'].upper()}] {issue['detail'][:60]}")

        # 5. 发布概览
        self._publish_summary(len(issues))
        print(f"  [SUMMARY] {len(issues)} 个诊断项")

    def _check_real_data(self):
        """基于真实数据的约束检查 (委托子检查)"""
        issues = []
        issues += self._check_health_status()
        issues += self._check_latency_anomaly()
        issues += self._check_offline_nodes()
        issues += self._check_error_events()
        return issues

    def _check_health_status(self):
        """检查 BoardService 健康状态"""
        issues = []
        if not self._health_data:
            return issues
        last = self._health_data[-1]
        if last.get("status") not in ("ok", "ready"):
            issues.append({
                "type": "anomaly", "severity": "critical",
                "source": "real_data", "component":
...[Truncated]...
        return issues

    def _check_latency_anomaly(self):
        """3-sigma 延迟异常检测"""
        issues = []
        if len(self._health_data) < 4:
            return issues
        latencies = [h.get('time', 0) for h in self._health_data[-10:]]
        if len(latencies) <= 3:
            return issues
        avg = statistics.mean(latencies)
        std = statistics.stdev(latencies)
        for h in self._health_data[-3:]:
            if h.get('time', 0) > avg + 3 * std:
                issues.append({
                    "type": "anomaly", "severity": "warning",
                    "source": "real_data", "component": h.get("component", "unknown"),
                    "status": "slow",
                    "detail": f"延迟异常 {h.get('time', 0):.2f}s (均值 {avg:.2f}s + 3sigma {3*std:.2f}s)",
                    "count": 1
                })
        return issues

    def _check_offline_nodes(self):
        """检查离线节点"""
        issues = []
        offline_nodes = [nid for nid, st in self._node_status.items()
                         if isinstance(st.get("status"), dict)
                         and st["status"].get("status") in ("offline", "disconnected", "error")]
        if offline_nodes:
            issues.append({
                "type": "anomaly", "severity": "warning",
                "source": "real_data", "component": ",".join(offline_nodes[:5]),
                "status": "offline",
                "detail": f"{len(offline_nodes)} 个节点离线: {', '.join(offline_nodes[:5])}",
                "count": len(offline_nodes)
            })
        return issues

    def _check_error_events(self):
        """检查最近错误事件"""
        issues = []
        if not self._error_events:
            return issues
        recent_errors = [e for e in self._error_events if time.time() - e["time"] < 300]
        if recent_errors:
            issues.append({
                "type": "error_event", "severity": "error",
                "source": "real_data", "component": "system",
                "status": "error",
                "detail": f"最近 5 分钟有 {len(recent_errors)} 个错误事件",
                "count": len(recent_errors)
            })
        return issues

    def _llm_analysis(self):
        """LLM 分析当前系统状态"""
        issues = []

        # 汇总状态
        context_lines = ["=== 系统状态摘要 ==="]
        context_lines.append(f"运行中服务: {sum(1 for h in self._health_data if h.get('status') in ('ok', 'ready'))}/{len(self._health_data)}")
        context_lines.append(f"在线节点: {len([n for n, s in self._node_status.items() if isinstance(s.get('status'), dict) and s['status'].get('status') != 'offline'])}")
        context_lines.append(f"错误事件 (5分钟): {len([e for e in self._error_events if time.time() - e['time'] < 300])}")

        if self._health_data:
            context_lines.append(f"最新 healthcheck: {json.dumps(self._health_data[-1], ensure_ascii=False)}")

        context = "\n".join(context_lines)
        analysis = self._llm.analyze(context)

        if analysis and "LLM 不可用" not in analysis and "失败" not in analysis:
            issues.append({
                "type": "llm_analysis", "severity": "info",
                "source": "llm", "component": "system",
                "status": "analyzed",
                "detail": "LLM 分析完成",
                "llm": analysis,
                "count": 1
            })

        return issues

    def _publish_summary(self, alert_count):
        """发布诊断概览"""
        summary = json.dumps({
            "alert_count": alert_count,
            "online_services": [h.get("component") for h in self._health_data[-3:] if h.get("status") in ("ok", "ready")],
            "offline_nodes": [nid for nid, st in self._node_status.items()
                              if isinstance(st.get("status"), dict)
                              and st["status"].get("status") in ("offline", "disconnected", "error")],
            "error_count_5min": len([e for e in self._error_events if time.time() - e['time'] < 300]),
            "timestamp": time.time()
        })
        self.client.publish("agent/bbs/diagnosis/summary", summary, retain=True)


def main():
    agent = DiagnosisAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
        print("\n[Diagnosis] 已停止")


if __name__ == "__main__":
    main()
