# Brainstorm: 多Agent本体论与系统诊断

> 日期: 2026-05-23 | 基于 GenericAgent_mqtt 现有 MQTT 通信层

---

## 一、多Agent 本体论 (Ontology)

### 核心问题

```
多Agent 系统中，Agent 如何理解彼此的能力、状态、意图？
MQTT 主题空间如何映射为"本体知识图谱"？
```

### 当前体系

| 层级 | 技术 | 说明 |
|------|------|------|
| 通信 | MQTT Pub/Sub | topic = 地址空间 |
| 注册 | BoardService register | JWT 身份绑定 |
| 能力 | Retain CapabilityRegistry | `node/{id}/capability` retain |
| 状态 | Heartbeat | `node/{id}/heartbeat` + `node/{id}/status` |
| 任务 | Board task routing | `agent/board/task/{id}/*` |
| 白板 | StateKV / Whiteboard | KV 共享状态 + CAS |

### 本体论层次

```python
# 三层本体模型

# Layer 1: 身份本体 (Who)
{
    "agent_id": "agent_alpha",
    "type": "WorkerAgent | BoardService | Gateway",
    "version": "0.1.0",
    "owner": "user",
    "capabilities": ["task_execute", "file_process", "web_search"],
    "status": "online | busy | idle | offline"
}

# Layer 2: 知识本体 (What)
{
    "domain": "rust_development | docker | ...",
    "skills": {
        "rust_development": {"level": "rev6", "score": 97},
        "docker_compose": {"level": "rev3", "score": 92}
    },
    "experiences": ["BoardService RS migration"],
    "sops": ["git_push_sop", "board_stress_sop"]
}

# Layer 3: 关系本体 (How)
{
    "dependencies": ["BoardService", "mqtt_broker"],
    "subordinates": ["worker_agent_01", "worker_agent_02"],
    "conversations": [
        {"with": "agent_beta", "topic": "task_assign", "status": "active"}
    ]
}
```

### MQTT 本体映射方案

```python
# topic = 路径 = 本体层级
agent/ontology/{agent_id}/identity      # Layer 1: 身份 (retain)
agent/ontology/{agent_id}/capability    # Layer 1: 能力 (retain) ← 已有
agent/ontology/{agent_id}/knowledge     # Layer 2: 知识 (retain)
agent/ontology/{agent_id}/relations     # Layer 3: 关系 (retain)
agent/ontology/{agent_id}/status       # 实时状态 (LWT)

# 查询: board/ontology/query
# 响应: board/ontology/query/response/{corr_id}

# 跨Agent发现:
# subscribe node/+/ontology/identity
# → 发现谁在线、谁能做什么
```

---

## 二、系统诊断 (System Diagnosis)

### 诊断金字塔

```
                  /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
                 /   Prognosis (预测)      \
                /    "未来30分钟会崩溃?"     \
               /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
              /  Root Cause (根因)           \
             /   "MariaDB 连接池耗尽导致"      \
            /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
           /   Anomaly (异常检测)              \
          /    "延迟从 70ms 飙升到 500ms"       \
         /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
        /   Monitoring (监控)                   \
       /    "BoardService 延迟 70ms, P99 108ms" \
      /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
     /   Metrics & Logs (观测性)                 \
    /    "请求延迟 P50, P95, P99, 错误率"         \
   /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
```

### 当前诊断能力

| 能力 | 状态 | 说明 |
|------|------|------|
| Metrics (P50/P95/P99) | ✅ | 压测脚本输出 |
| Healthcheck MQTT | ✅ | `system/healthcheck/*` Rust BoardService |
| LWT 离线通知 | ✅ | 进程退出自动发布 `node/{id}/status = offline` |
| SIGTERM 优雅关闭 | ✅ | Rust BoardService |
| 结构化日志 | ⚠️ | `tools/observability.py` 已创建但未集成 |
| Prometheus | ⚠️ | 同上，HTTP server 可启动 |
| 根因分析 | ❌ | 无自动关联分析 |
| 预测性诊断 | ❌ | 无趋势分析 |

### 诊断 Agent 概念设计

```python
class DiagnosisAgent:
    """专职诊断 Agent —— 持续监控 + 异常检测 + 根因分析"""

    def __init__(self):
        self.subscribe("system/healthcheck/+/response", self._on_health_response)
        self.subscribe("node/+/status", self._on_node_status)
        self.subscribe("events/#", self._on_event)
        self._metrics_history = deque(maxlen=1000)  # 滚动窗口

    def _on_health_response(self, topic, payload):
        """收集各组件 healthcheck 响应"""
        component = self._parse_component(topic)
        self._metrics_history.append({
            "time": time.time(),
            "component": component,
            "data": payload,
        })
        self._detect_anomaly(component, payload)

    def _detect_anomaly(self, component, payload):
        """简单规则检测 + 滑动窗口分析"""
        latency = payload.get("latency_ms", 0)
        recent = [m for m in self._metrics_history 
                  if m["component"] == component][-50:]
        avg_latency = sum(m["data"].get("latency_ms", 0) 
                         for m in recent) / max(len(recent), 1)

        if latency > avg_latency * 3:  # 3σ 异常
            self._trigger_diagnosis(component, {
                "type": "latency_spike",
                "value": latency,
                "baseline": avg_latency,
                "time": time.time()
            })

    def _trigger_diagnosis(self, component, anomaly):
        """触发根因分析 → 发布诊断报告到 board/diagnosis/"""
        diagnosis = self._correlate_events(component, anomaly["time"] - 30)
        self.publish(f"board/diagnosis/report", {
            "component": component,
            "anomaly": anomaly,
            "correlated_events": diagnosis,
            "suggested_action": self._suggest_action(diagnosis),
        })

    def _suggest_action(self, diagnosis):
        """规则引擎 → 建议行动"""
        if "db_timeout" in diagnosis:
            return "restart_board_service"
        if "mqtt_disconnect" in diagnosis:
            return "restart_mosquitto"
        return "investigate"
```

### 多Agent 协作诊断

```
┌──────────┐   system/healthcheck   ┌────────────┐
│ BoardSvc │ ─────────────────────→ │Diagnosis   │
│  (Rust)  │                        │  Agent     │
└──────────┘                        │ (观察者)   │
                                    └─────┬──────┘
┌──────────┐   node/+/status              │
│ Worker-1 │ ────────────────────────────→│
└──────────┘                              │
                                          │  board/diagnosis/report
┌──────────┐   events/+/error             │
│  Plugin  │ ────────────────────────────→│
└──────────┘                              │
                                          ▼
                                   ┌──────────────┐
                                   │  Insight     │
                                   │  Board       │
                                   │ (存诊断报告)  │
                                   └──────────────┘
```

### 本体论 + 诊断 = 自我认知

```python
# Agent 的"自我认知"实体
{
    "id": "agent_alpha",
    "identity": {        # 我是谁 —— 本体论 Layer 1
        "type": "diagnosis_agent",
        "capabilities": ["anomaly_detection", "root_cause", "healthcheck"]
    },
    "health": {           # 我好不好 —— 诊断
        "status": "healthy",
        "last_check": "2026-05-23T17:00:00Z",
        "metrics": {
            "cpu": 23, "mem_mb": 45,
            "msg_rate": 14, "error_rate": 0.001
        }
    },
    "context": {          # 我看到什么 —— 环境感知
        "known_agents": ["board_service", "worker_1", "worker_2"],
        "known_boards": ["agent-bbs-test", "agent-inspiration"],
        "alerts": ["latency_spike at 16:55 (resolved)"]
    }
}
```

---

## 三、实现路径

### P0: 诊断 Agent MVP (2h)

```python
# 最小可行: 订阅 healthcheck + status 主题
# 输出: 异常日志 + 诊断报告到 board/diagnosis/
# 依赖: 已有 tools/observability.py
```

| 项 | 工时 | 说明 |
|----|------|------|
| DiagnosisAgent 类 | 1h | 订阅/异常检测/报告发布 |
| 规则引擎 | 0.5h | 3σ + 滑动窗口 |
| 集成到现有系统 | 0.5h | 作为 Plugin 注册到 BoardService |

### P1: 本体论集成 (3h)

| 项 | 工时 | 说明 |
|----|------|------|
| 本体主题空间 | 1h | `agent/ontology/**` 发布自治 |
| Capability 增强 | 1h | 当前 retain 能力扩展到三层本体 |
| 跨Agent发现 | 1h | 查询 `+` 通配符本体主题 |

### P2: 预测诊断 (4h)

| 项 | 工时 | 说明 |
|----|------|------|
| 趋势分析 | 2h | 线性回归预测 30min 后状态 |
| 自动恢复 | 2h | system/action 发布恢复指令 |

---

## 四、关键问题

1. **本体更新频率**: retain 消息更新时应保留版本，Agent 可判断信息是否过时
2. **诊断 Agent 单点故障**: 诊断本身也需要诊断——可双实例互检
3. **隐私边界**: 一个 Agent 的本体信息可能暴露内部状态给其他 Agent，需权限控制
4. **指标存储**: 历史指标存在 MariaDB？Redis？还是 MQTT retained（仅最新）？
