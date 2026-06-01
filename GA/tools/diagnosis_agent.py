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

        # LLM — 尝试用统一 LLM Provider 工厂
        self._llm = None
        self._llm_available = False
        self._init_llm()

    def _init_llm(self):
        """初始化 LLM — 优先使用统一的 LLM Provider 工厂"""
        enabled = os.environ.get("SKILL_LLM_ENABLE", "0") == "1"
        if not enabled:
            return
        try:
            # 尝试从 LLM Provider 工厂加载
            from GA.tools.llm_provider_factory import get_llm
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
            self._llm = get_llm(provider="deepseek", api_key=api_key)
            self._llm_available = True
            print("[LLM] 已通过 Provider 工厂初始化")
        except ImportError:
            # 降级到直接 urllib
            self._llm_available = bool(os.environ.get("LLM_API_KEY", ""))
            print(f"[LLM] Provider 工厂不可用，降级 urllib; {'可用' if self._llm_available else '不可用'}")
        except Exception as e:
            print(f"[LLM] 初始化失败: {e}")

    def _llm_analyze(self, context: str) -> str:
        """LLM 根因分析 — 使用统一接口或降级"""
        if not self._llm_available:
            return "LLM 不可用，使用规则诊断"

        # 统一接口
        if self._llm is not None and hasattr(self._llm, 'chat'):
            try:
                resp = self._llm.chat([
                    {"role": "system", "content": "你是 IT 系统诊断专家，用中文回答。"},
                    {"role": "user", "content": f"分析以下系统状态，给出根因和建议：\n{context}\n\n格式：根因: ... 建议: ..."}
                ])
                return str(resp)[:500]
            except Exception as e:
                return f"LLM 分析失败: {e}"

        # 降级: urllib 直接调用
        try:
            import urllib.request
            api_key = os.environ.get("LLM_API_KEY", "")
            prompt = f"你是一个系统诊断专家。分析以下系统状态，给出根因和建议：\n{context}\n\n格式：根因: ... 建议: ..."
            data = json.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是 IT 系统诊断专家，用中文回答。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"][:500]
        except Exception as e:
            return f"LLM 调用失败: {e}"

    def start(self):
        """启动诊断循环"""
        self.bbs.connect()
        info = self.bbs.register("Diagnosis Agent v3")
        self.token = info.get("token", "")
        self.client.connect()

        # 订阅真实数据源 — 使用最新的 topic 格式
        self.client.subscribe("system/healthcheck/+/response", self._on_healthcheck)
        self.client.subscribe("node/+/status", self._on_node_status)
        self.client.subscribe("events/+/error", self._on_error_event)
        # 额外订阅 BoardService 心跳
        self.client.subscribe("system/healthcheck/+/request", self._on_healthcheck)

        print(f"[Diagnosis v3] 注册成功, board={self.board}")
        print("[Diagnosis v3] 数据源: healthcheck / node-status / error-events")
        print(f"[Diagnosis v3] LLM: {'启用' if self._llm_available else '未启用(规则降级)'}")

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
                "component": topic.split('/')[2],
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
        if self._llm_available:
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
        """基于真实数据的约束检查"""
        issues = []

        # 健康检查
        if self._health_data:
            last = self._health_data[-1]
            if last.get("status") not in ("ok", "ready"):
                issues.append({
                    "type": "anomaly", "severity": "critical",
                    "source": "real_data", "component": "BoardService",
                    "status": "down",
                    "detail": f"BoardService healthcheck: {last.get('status')}",
                    "count": sum(1 for h in self._health_data if h.get('status') not in ('ok', 'ready'))
                })

            # 延迟分析 (3-sigma)
            if len(self._health_data) > 3:
                latencies = [h.get('time', 0) for h in self._health_data[-10:]]
                if len(latencies) > 3:
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

        # 节点状态
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

        # 错误事件
        if self._error_events:
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
        analysis = self._llm_analyze(context)

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
        self.client.publish("board/diagnosis/summary", summary, retain=True)


def main():
    agent = DiagnosisAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
        print("\n[Diagnosis] 已停止")


if __name__ == "__main__":
    main()
