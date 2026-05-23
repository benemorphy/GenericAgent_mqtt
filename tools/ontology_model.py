"""
Project Ontology — 基于反省的要素-关系-约束-推理模型

从 100+ 轮交互中提取的经验本体：
  实体 — 我操作过的所有组件
  关系 — 我验证过的连接
  约束 — 我踩过的坑
  推理 — 我从失败中总结的规律
"""

from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# Layer 1: 实体定义 (Entities)
# ══════════════════════════════════════════════════════════════

@dataclass
class Component:
    """系统中存在的可识别组件"""
    name: str
    component_type: str          # service / library / tool / config
    language: str                # python / rust / toml / json
    status: str                  # running / compiled / static
    location: str                # 文件路径
    verified_interactions: int   # 我确认过的交互次数


# 从我经验中提取的实体
ENTITIES = [
    Component("BoardService", "service", "rust", "running PID 1032",
              "tools/board_service_rs/", 47),
    Component("BoardService (Python)", "service", "python", "replaced",
              "mqtt_bbs/board_service.py", 12),
    Component("Mosquitto", "service", "binary", "running",
              "D:\tools\mosquitto\mosquitto.exe", 8),
    Component("MariaDB", "service", "binary", "running",
              "127.0.0.1:3306", 6),
    Component("HTTP Gateway", "service", "python", "running",
              "frontends/gateway/", 3),
    Component("BBSClient", "library", "python", "stable",
              "mqtt_bbs/client.py", 25),
    Component("BoardClient", "library", "python", "stable",
              "mqtt_bbs/board_client.py", 30),
    Component("BBSClient (Rust)", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/", 8),
    Component("BoardClient (Rust)", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/client/board_client.rs", 6),
    Component("AgentBoard", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/agent_board.rs", 5),
    Component("WorkerAgent", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/worker_agent.rs", 5),
    Component("CapabilityRegistry", "library", "rust", "compiled",
              "tools/board_service_rs/src/capability.rs", 4),
    Component("PluginManager", "library", "python", "stable",
              "mqtt_bbs/plugin_manager.py", 2),
    Component("mykey.py", "config", "python", "static",
              "mykey.py", 2),
    Component("agent.env", "config", "env", "static",
              "mqtt_bbs/agent.env", 5),
    Component("mosquitto_passwd", "config", "text", "static",
              "D:\tools\mosquitto\mosquitto_passwd", 3),
    Component("DEEPSEEK_API_KEY", "credential", "env_var", "updated",
              "setx DEEPSEEK_API_KEY", 3),
]


# ══════════════════════════════════════════════════════════════
# Layer 2: 关系定义 (Relations)
# ══════════════════════════════════════════════════════════════

@dataclass
class Relation:
    """两个实体之间的逻辑联系"""
    source: str
    relation_type: str           # depends-on / publishes-to / subscribes-to / contains / requires / replaces
    target: str
    context: str                 # 什么条件下成立
    verified: bool               # 我是否测试验证过


RELATIONS = [
    # ── 依赖关系 ──
    Relation("BoardService", "depends-on", "Mosquitto", "MQTT 端口 1883", True),
    Relation("BoardService", "depends-on", "MariaDB", "DB 连接 mysql://root:mariadb@127.0.0.1", True),
    Relation("BoardClient (Python)", "depends-on", "BBSClient (Python)", "import mqtt_bbs.client", True),
    Relation("BoardClient (Rust)", "depends-on", "BBSClient (Rust)", "crate mqtt_bbs_rs", True),
    Relation("AgentBoard", "depends-on", "BBSClient (Rust)", "use BBSClient", True),
    Relation("WorkerAgent", "depends-on", "BBSClient (Rust)", "use BBSClient", True),
    Relation("HTTP Gateway", "depends-on", "BoardClient (Python)", "转发请求", True),
    Relation("skills_learning", "depends-on", "DEEPSEEK_API_KEY", "LLM 增强需要 API Key", True),

    # ── 通信关系 ──
    Relation("BoardClient (Python)", "publishes-to", "BoardService",
             "agent/bbs/{board}/register → agent/bbs/{board}/post", True),
    Relation("BoardClient (Rust)", "publishes-to", "BoardService",
             "agent/bbs/{board}/register → agent/bbs/{board}/post", True),
    Relation("BoardService", "publishes-to", "BoardClient (Python)",
             "agent/bbs/{board}/new_post (广播)", True),
    Relation("BoardService", "publishes-to", "World",
             "node/{id}/status (retain)", True),
    
    # ── 替换关系 ──
    Relation("BoardService (Rust)", "replaces", "BoardService (Python)",
             "测试验证 10/10 功能点通过", True),

    # ── 包含关系 ──
    Relation("mqtt_bbs_rs", "contains", "BBSClient (Rust)", "src/client/bbs_client.rs", True),
    Relation("mqtt_bbs_rs", "contains", "BoardClient (Rust)", "src/client/board_client.rs", True),
    Relation("board_service_rs", "contains", "CapabilityRegistry", "src/capability.rs", True),
]


# ══════════════════════════════════════════════════════════════
# Layer 3: 约束定义 (Constraints) — 从我踩过的坑中提取
# ══════════════════════════════════════════════════════════════

@dataclass
class Constraint:
    """必须成立的条件 — 不满足时系统异常"""
    description: str
    predicate: str               # 可检查的条件表达式
    severity: str                # error / warning / info
    source: str                  # 从哪次失败中提取的
    fix: str                     # 修复方式


CONSTRAINTS = [
    Constraint(
        "Mosquitto 密码文件不能有空行或明文密码",
        "all(line.strip() and ':' in line for line in password_file)",
        "error",
        "PR #101: Corrupt password file at line 8",
        "`mosquitto_passwd -b` 重新添加用户，删除空白行"
    ),
    Constraint(
        "Mosquitto 密码文件修改后必须全杀进程重启",
        "not('net stop/start' in last_operation)",
        "error",
        "PR #101: net stop/start 不重载密码文件",
        "`taskkill /f /im mosquitto.exe && mosquitto.exe -c config`"
    ),
    Constraint(
        "Rust 闭包回调必须用 Arc::new() 包裹，不能用 as Callback 转换",
        "subscribe 调用使用 Arc::new(move |...| {}) 而非 |...| {} as Callback",
        "error",
        "PR #99: Rust 编译时类型推断失败",
        "用 `Arc::new(move |topic: String, payload: Value| {...})`"
    ),
    Constraint(
        "publish_response 的 await 不能遗漏",
        "publish_response(...).await 而非 publish_response(...)",
        "error",
        "PR #101: file.rs publish_response 缺少 .await",
        "`cargo fix --bin board_service_rs` 自动修复"
    ),
    Constraint(
        "MQTT 主题通配符长度必须匹配",
        "agent/ontology/# (3+层) 而非 agent/ontology/+ (仅3层)",
        "warning",
        "PR #106: ontology query 返回 0 agents",
        "用 `#` 而不是 `+` 匹配多层主题"
    ),
    Constraint(
        "BoardService 启动必须传 broker 认证",
        "--broker-username 和 --broker-password 不能为空",
        "error",
        "第一次启动时 ConnectionRefused",
        "从 agent.env 读取 MASTER_PASSWORD 传入"
    ),
    Constraint(
        "jsonwebtoken 在 Windows GNU 下不能用默认 feature",
        "Cargo.toml: jsonwebtoken = { version = ..., default-features = false }",
        "error",
        "PR #100: ring/aws-lc-sys 原生 C 编译失败",
        "添加 `default-features = false` 跳过 ring"
    ),
    Constraint(
        "Rust 新功能发布到 BoardService 后必须重启二进制",
        "编译新 binary → taskkill → 重新启动",
        "info",
        "Phase 1 测试: ontology handler 未生效",
        "`taskkill /f /fi ... && cargo run --release ...`"
    ),
    Constraint(
        "本体查询必须传 reply_to 字段",
        "board/ontology/query 请求中应含 \"reply_to\": \"board/ontology/query/response/\"",
        "warning",
        "PR #105: query 响应主题不匹配",
        "默认 fallback 到 board/ontology/query/response/"
    ),
]


# ══════════════════════════════════════════════════════════════
# Layer 4: 推理规则 (Inferences) — 从经验中总结的规律
# ══════════════════════════════════════════════════════════════

@dataclass
class Inference:
    """已知前提 → 可推导结论"""
    premise: str
    conclusion: str
    confidence: float            # 0.0 ~ 1.0
    evidence_count: int          # 验证次数
    example: str


INFERENCES = [
    Inference(
        "BoardService(Rust) 替换 Python 版",
        "吞吐量从 14 → 599 posts/s (提升 42x)",
        0.95, 2,
        "压力测试: 5并发 × 40帖"
    ),
    Inference(
        "LLM 增强技能学习",
        "模式数从 9 → 17 (增加 89%)",
        0.85, 3,
        "ontology_modeling rev1(规则) vs rev6(LLM)"
    ),
    Inference(
        "配置文件修改后服务未重启",
        "新配置不生效",
        0.99, 5,
        "mosquitto_passwd / BoardService 替换"
    ),
    Inference(
        "Mosquitto 密码文件损坏",
        "所有客户端认证失败",
        0.95, 2,
        "空白行导致 Corrupt password file"
    ),
    Inference(
        "Rust 编译需要 self-contained dlltool",
        "设置 PATH 指向 rustlib/.../self-contained",
        0.90, 3,
        "getrandom: Invalid bfd target"
    ),
    Inference(
        "密码文件修改后仅 taskkill 重启有效",
        "net stop/start 不重新加载",
        0.90, 2,
        "auth 修复 3 次失败后才找到根因"
    ),
]


# ══════════════════════════════════════════════════════════════
# 验证工具: 检查推理规则
# ══════════════════════════════════════════════════════════════

def check_constraints(state: dict) -> list[str]:
    """运行时检查约束条件是否满足"""
    violations = []
    for c in CONSTRAINTS:
        try:
            result = eval(c.predicate, {"__builtins__": {}}, state)
            if not result:
                violations.append(f"[{c.severity}] {c.description}")
        except Exception as e:
            violations.append(f"[{c.severity}] {c.description} (检查失败: {e})")
    return violations


def query_relations(entity: str, relation_type: str = None) -> list[Relation]:
    """查询实体的所有关系"""
    results = []
    for r in RELATIONS:
        if r.source == entity or r.target == entity:
            if relation_type is None or r.relation_type == relation_type:
                results.append(r)
    return results


def chain_inference(premise: str) -> list[Inference]:
    """根据前提推理结论"""
    return [i for i in INFERENCES if i.premise.lower() in premise.lower()]
