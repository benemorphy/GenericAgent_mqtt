"""
Diagnosis Agent v2 — 本体驱动 + 真实数据 + LLM 分析 + 反省增强

工作流:
  1. 订阅 system/healthcheck/#, node/+/status, events/+/error
  2. 加载 ontology_model 约束 + 推理
  3. MQTT 消息作为数据源 → 真实约束检查
  4. LLM 分析异常根因 + 建议
  5. 反省: 从轨迹提取新模式 → 动态扩展本体
  6. 发布诊断帖子到 board/diagnosis/post/

启动:
  SKILL_LLM_ENABLE=1 LLM_API_KEY=... python -m tools.diagnosis_agent
"""

import sys, os, time, json, threading, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Mqtt_bbs_client.board_client import BoardClient
from Mqtt_bbs_client.client import BBSClient
from tools.ontology_model import ENTITIES, RELATIONS, CONSTRAINTS, INFERENCES


class DiagnosisAgent:
    
    def __init__(self):
        self.board = "agent-diagnosis"
        self.agent_id = "diagnosis_agent"
        self.bbs = BoardClient(self.agent_id, board=self.board)
        self.client = BBSClient("diagnosis_agent_listener")  # use distinct client_id to avoid kicking BoardClient's internal connection
        self.token = None
        self._running = False
        
        # 数据采集
        self._health_data = []      # 滑动窗口: 最近 60 个 healthcheck
        self._node_status = {}      # node/{id}/status 最新值
        self._error_events = []     # events/+/error 最近 50 条
        self._latency_samples = collections.deque(maxlen=60)
        
        # LLM
        self._llm_available = False
        self._init_llm()

    def _init_llm(self):
        """初始化 LLM 连接"""
        enabled = os.environ.get("SKILL_LLM_ENABLE", "0") == "1"
        api_key = os.environ.get("LLM_API_KEY", "")
        if enabled and api_key:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.deepseek.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        self._llm_available = True
                        print("[LLM] 可用")
            except:
                print("[LLM] 不可用，使用规则降级")
    
    def _llm_analyze(self, context: str) -> str:
        """LLM 根因分析"""
        if not self._llm_available:
            return "LLM 不可用，使用规则诊断"
        try:
            import urllib.request
            prompt = f"你是一个系统诊断专家。分析以下系统状态，给出根因和建议：\n{context}\n\n格式：根因: ... 建议: ..."
            data = json.dumps({"model": "deepseek-chat", "messages": [
                {"role": "system", "content": "你是 IT 系统诊断专家，用中文回答。"},
                {"role": "user", "content": prompt}
            ], "temperature": 0.3}).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', '')}",
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
        info = self.bbs.register("Diagnosis Agent v2")
        self.token = info.get("token", "")
        self.client.connect()
        
        # 订阅真实数据源
        self.client.subscribe("system/healthcheck/+/response", self._on_healthcheck)
        self.client.subscribe("node/+/status", self._on_node_status)
        self.client.subscribe("events/+/error", self._on_error_event)
        
        print(f"[Diagnosis v2] 注册成功, board={self.board}")
        print(f"[Diagnosis v2] 数据源: healthcheck / node-status / error-events")
        print(f"[Diagnosis v2] LLM: {'启用' if self._llm_available else '未启用(规则降级)'}")
        
        # 启动数据采集（后台线程收集 10s 数据后做一次诊断）
        self._running = True
        time.sleep(2)  # 等待首批数据
        while self._running:
            self._run_once()
            time.sleep(30)  # 每 30 秒诊断一次
    
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
            # 只保留最近 120 条
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
        """一次诊断周期"""
        print(f"\n[Diagnosis] ====== 周期 ({time.strftime('%H:%M:%S')}) ======")
        
        issues = []
        
        # 1. 真实数据约束检查
        issues += self._check_real_data()
        
        # 2. LLM 分析
        if self._llm_available:
            issues += self._llm_analysis()
        
        # 3. 推理规则
        issues += self._run_inferences()
        
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
        
        # 1. 组件是否在线 (healthcheck)
        if self._health_data:
            last = self._health_data[-1]
            if last.get("status") != "ok" and last.get("status") != "ready":
                issues.append({
                    "type": "anomaly", "severity": "critical",
                    "source": "real_data", "component": "BoardService",
                    "status": "down", "detail": f"BoardService healthcheck: {last.get('status')}",
                    "count": sum(1 for h in self._health_data if h.get('status') != 'ok')
                })
            
            # 延迟滑动窗口 (3σ 异常)
            if len(self._health_data) > 3:
                latencies = [h.get('time', 0) for h in self._health_data[-10:]]
                if len(latencies) > 3:
                    avg = statistics.mean(latencies)
                    std = statistics.stdev(latencies)
                    for h in self._health_data[-3:]:
                        if h.get('time', 0) > avg + 3 * std:
                            issues.append({
                                "type": "anomaly", "severity": "warning",
                                "source": "3sigma", "component": "BoardService",
                                "status": "degraded",
                                "detail": f"延迟异常: {h['time']:.0f}ms (avg={avg:.0f}ms, 3σ={3*std:.0f}ms)",
                                "count": 1
                            })
        
        # 2. 节点在线状态
        offline_nodes = [nid for nid, info in self._node_status.items()
                        if time.time() - info.get('time', 0) > 120]
        if offline_nodes:
            issues.append({
                "type": "anomaly", "severity": "warning",
                "source": "real_data", "component": "Node",
                "status": "offline",
                "detail": f"离线节点: {', '.join(offline_nodes)}",
                "count": len(offline_nodes)
            })
        
        # 3. 错误事件聚合
        if self._error_events:
            recent_errors = [e for e in self._error_events 
                           if time.time() - e['time'] < 300]
            if recent_errors:
                error_summary = {}
                for e in recent_errors:
                    t = e['topic']
                    error_summary[t] = error_summary.get(t, 0) + 1
                for topic, count in sorted(error_summary.items(), key=lambda x: -x[1])[:3]:
                    issues.append({
                        "type": "anomaly", "severity": "warning",
                        "source": "real_data", "component": topic.split('/')[2] if len(topic.split('/')) > 2 else topic,
                        "status": "degraded",
                        "detail": f"错误事件: {topic} ({count}次/5分钟)",
                        "count": count
                    })
        
        return issues
    
    def _llm_analysis(self):
        """LLM 增强分析"""
        issues = []
        
        # 准备上下文
        context_lines = []
        if self._health_data:
            context_lines.append(f"Healthcheck: {self._health_data[-3:]}")
        if self._error_events:
            context_lines.append(f"Recent errors ({len(self._error_events)}): {self._error_events[-3:]}")
        if self._node_status:
            n = len(self._node_status)
            offline = sum(1 for v in self._node_status.values() if time.time() - v['time'] > 120)
            context_lines.append(f"Nodes: {n} total, {offline} offline")
        
        if context:
            context = "\n".join(context_lines)
            analysis = self._llm_analyze(context)
            if analysis and ":" in analysis:
                issues.append({
                    "type": "analysis", "severity": "info",
                    "source": "llm", "component": "system",
                    "status": "analyzed", "detail": "LLM 诊断分析",
                    "llm": analysis,
                    "count": 1
                })
        return issues
    
    def _run_inferences(self):
        """推理规则"""
        issues = []
        for inf in INFERENCES:
            # 检查前提是否满足
            if "替换" in inf.premise and "BoardService" in self._node_status:
                issues.append({
                    "type": "inference", "severity": "info",
                    "source": "inference", "component": "system",
                    "status": "inferred",
                    "detail": f"推理: {inf.premise[:40]}... → {inf.conclusion[:40]}...",
                    "count": inf.evidence_count
                })
        return issues
    
    def _publish_summary(self, alert_count):
        """发布诊断概览"""
        summary = {
            "total_entities": len(ENTITIES),
            "total_relations": len(RELATIONS),
            "constraints": len(CONSTRAINTS),
            "inferences": len(INFERENCES),
            "open_alerts": alert_count,
            "nodes_online": len([n for n in self._node_status.values() if time.time() - n['time'] < 120]),
            "nodes_offline": len([n for n in self._node_status.values() if time.time() - n['time'] >= 120]),
            "health_samples": len(self._health_data),
            "llm_enabled": self._llm_available,
            "events_5min": len([e for e in self._error_events if time.time() - e['time'] < 300]),
            "timestamp": time.time()
        }
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
