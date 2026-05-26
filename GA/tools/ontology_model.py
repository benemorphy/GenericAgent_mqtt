"""
Project Ontology — 基于反省的要素-关系-约束-推理模型

从 100+ 轮交互中提取的经验本体：
  实体 — 我操作过的所有组件
  关系 — 我验证过的连接
  约束 — 我踩过的坑
  推理 — 我从失败中总结的规律
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
import os


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
              os.environ.get("MOSQUITTO_HOME", r"D:\\tools\\mosquitto") + "/" + os.environ.get("MOSQUITTO_EXE", "mosquitto.exe"), 8),
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
              os.environ.get("MOSQUITTO_HOME", r"D:\\tools\\mosquitto") + "/" + os.environ.get("MOSQUITTO_PASSWD", "mosquitto_passwd"), 3),
    Component("DEEPSEEK_API_KEY", "credential", "env_var", "updated",
              "setx DEEPSEEK_API_KEY", 3),
    # ── 反省发现: 代码中存在但本体缺失的实体 ──
    Component("DiagnosisAgent", "tool", "python", "stable",
              "tools/diagnosis_agent.py", 1),
    Component("ReflectionEngine", "tool", "python", "stable",
              "tools/reflection_engine.py", 1),
    Component("ontology_model", "library", "python", "stable",
              "tools/ontology_model.py", 2),
    Component("Bbs", "library", "python", "stable",
              "mqtt_bbs/bbs.py", 5),
    Component("Dag", "library", "python", "stable",
              "mqtt_bbs/dag.py", 2),
    Component("Scheduler", "library", "python", "stable",
              "mqtt_bbs/scheduler.py", 1),
    Component("Whiteboard", "library", "python", "stable",
              "mqtt_bbs/whiteboard.py", 1),
    Component("FileTransferV2", "library", "python", "stable",
              "mqtt_bbs/file_transfer_v2.py", 1),
    Component("Persistence", "library", "python", "stable",
              "mqtt_bbs/persistence.py", 3),
    Component("PersistenceWorker", "library", "python", "stable",
              "mqtt_bbs/persistence_worker.py", 1),
    Component("StateKV", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/state_kv.rs", 2),
    Component("FileTransferRS", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/file_transfer.rs", 1),
    Component("DAGWorkflowRS", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/dag.rs", 1),
    Component("SchedulerRS", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/src/scheduler.rs", 1),
    Component("Config", "config", "python", "stable",
              "mqtt_bbs/config.py", 3),
    Component("Client", "library", "python", "stable",
              "mqtt_bbs/client.py", 15),
    Component("boards.json", "config", "json", "static",
              "boards.json", 2),
    # ── 前端界面 ──
    Component("FeishuBot", "service", "python", "running",
              "frontends/fsapp.py", 1),
    Component("GatewayMonitor", "service", "python", "running",
              "frontends/dashboard_mqtt.py", 1),
    Component("ChatAppCommon", "library", "python", "stable",
              "frontends/chatapp_common.py", 4),
    # ── 关键工具 ──
    Component("DreamEngine", "tool", "python", "stable",
              "tools/dream_engine.py", 3),
    Component("InspirationBoard", "tool", "python", "stable",
              "tools/inspiration_board.py", 2),
    Component("MetasoSearch", "tool", "python", "stable",
              "tools/metaso_search.py", 2),
    Component("CuriosityEngine", "tool", "python", "stable",
              "tools/curiosity_trigger.py + curiosity_hooks.py", 1),
    Component("BrainstormSwarm", "tool", "python", "stable",
              "tools/brainstorm_swarm.py", 1),
    Component("FailureTracker", "tool", "python", "stable",
              "tools/failure_tracker.py", 2),
    Component("Observability", "tool", "python", "stable",
              "tools/observability.py", 1),
    Component("PiiMasker", "tool", "python", "stable",
              "tools/pii_masker.py", 1),
    Component("FeishuReminder", "tool", "python", "stable",
              "tools/feishu_reminder.py", 1),
    # ── skill 学习系统 ──
    Component("SkillsLearning", "library", "python", "stable",
              "skills_learning/", 3),
    # ── Rust BoardService 内部处理模块 ──
    Component("RegisterHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/handlers/register.rs", 1),
    Component("PostHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/handlers/post.rs", 1),
    Component("QueryHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/handlers/query.rs", 1),
    Component("FileHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/handlers/file.rs", 1),
    Component("WebhookHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/handlers/webhook.rs", 1),
    Component("Models", "library", "rust", "compiled",
              "tools/board_service_rs/src/models.rs", 1),
    Component("PluginIPC", "library", "rust", "compiled",
              "tools/board_service_rs/src/plugin_ipc.rs", 1),
    # ── 反省检测: mqtt_bbs Python 缺失模块 ──
    Component("BBSClient (Python)", "library", "python", "stable",
              "mqtt_bbs/client.py", 30),
    Component("MqttAgentRunner", "library", "python", "stable",
              "mqtt_bbs/mqtt_agent_runner.py", 2),
    Component("Plugin", "library", "python", "stable",
              "mqtt_bbs/plugin.py", 2),
    Component("Registry", "library", "python", "stable",
              "mqtt_bbs/registry.py", 3),
    # ── 反省检测: board_service_rs Rust 模块 ──
    Component("MqttHandler", "library", "rust", "compiled",
              "tools/board_service_rs/src/mqtt_handler.rs", 2),
    Component("AppState", "library", "rust", "compiled",
              "tools/board_service_rs/src/app_state.rs", 1),
    Component("Db", "library", "rust", "compiled",
              "tools/board_service_rs/src/db.rs", 2),
    Component("Capability", "library", "rust", "compiled",
              "tools/board_service_rs/src/capability.rs", 1),
    Component("FileTransfer (Rust)", "library", "rust", "compiled",
              "tools/board_service_rs/src/file_transfer.rs", 1),
    # ── 运行服务 ──
    Component("Gateway", "service", "python", "running",
              "frontends/gateway/main.py", 3),
    # ── 修复断裂关系: 实体别名 ──
    Component("board_service_rs", "library", "rust", "compiled",
              "tools/board_service_rs/", 47),
    Component("BoardClient (Python)", "library", "python", "stable",
              "mqtt_bbs/board_client.py", 15),
    Component("BoardService (Rust)", "service", "rust", "running",
              "tools/board_service_rs/", 47),
    Component("skills_learning", "library", "python", "stable",
              "skills_learning/", 40),
    Component("mqtt_bbs_rs", "library", "rust", "compiled",
              "tools/mqtt_bbs_rs/", 8),
    Component("mqtt_bbs", "library", "python", "stable",
              "mqtt_bbs/", 15),
    Component("Observation", "tool", "python", "stable",
              "tools/observability.py", 1),
    Component("World", "service", "concept", "reference",
              "外部系统与数据源", 1),
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
    Relation("Gateway", "depends-on", "BoardClient (Python)", "转发请求到 BBS", True),
    # ── 新增: mqtt_bbs Python 模块依赖 ──
    Relation("MqttAgentRunner", "depends-on", "BBSClient (Python)", "import mqtt_bbs.client", True),
    Relation("PluginManager", "depends-on", "Plugin", "管理 plugin.py 插件", True),
    Relation("Registry", "depends-on", "BBSClient (Python)", "服务注册/发现", True),
    # ── 新增: board_service_rs 内部结构 ──
    Relation("board_service_rs", "contains", "MqttHandler", "src/mqtt_handler.rs", True),
    Relation("board_service_rs", "contains", "AppState", "src/app_state.rs", True),
    Relation("board_service_rs", "contains", "Db", "src/db.rs", True),
    Relation("board_service_rs", "contains", "Capability", "src/capability.rs", True),
    Relation("board_service_rs", "contains", "FileTransfer (Rust)", "src/file_transfer.rs", True),
    # ── 新增: Gateway 数据流 ──
    Relation("Gateway", "publishes-to", "BoardService", "HTTP → MQTT 转发", True),
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
    # ── 反省发现: 诊断与反省模块的关系 ──
    Relation("DiagnosisAgent", "subscribes-to", "BoardService",
             "system/healthcheck/+/response", True),
    Relation("DiagnosisAgent", "subscribes-to", "World",
             "node/+/status + events/+/error", True),
    Relation("ReflectionEngine", "reads", "ontology_model",
             "导入 ENTITIES/RELATIONS 做偏差检测", True),
    Relation("ReflectionEngine", "reads", "mqtt_bbs", "扫描 Python 模块", True),
    Relation("DiagnosisAgent", "publishes-to", "BoardService",
             "board/diagnosis/post/ + board/diagnosis/summary", True),
    Relation("ontology_model", "drives", "DiagnosisAgent",
             "约束和推理来自模型", True),
    Relation("ontology_model", "drives", "ReflectionEngine",
             "偏差检测基准来自模型", True),
    Relation("ReflectionEngine", "updates", "ontology_model",
             "偏差发现后自动更新实体列表", True),
    # ── 前端 → 后端 ──
    Relation("FeishuBot", "depends-on", "Mosquitto", "MQTT BBS BoardClient 推送", True),
    Relation("FeishuBot", "depends-on", "BoardClient (Python)", "import mqtt_bbs.board_client", True),
    Relation("GatewayMonitor", "depends-on", "Mosquitto", "MQTT 实时推送 Dashboard", True),
    # ── 工具 → 基础设施 ──
    Relation("DreamEngine", "depends-on", "BoardClient (Python)", "发布梦境帖子到 BBS", True),
    Relation("InspirationBoard", "depends-on", "BoardService", "BBS 后端支持", True),
    Relation("MetasoSearch", "depends-on", "DEEPSEEK_API_KEY", "LLM 增强搜索需要 API Key", True),
    Relation("CuriosityEngine", "depends-on", "BoardClient (Python)", "好奇心帖子通过 BBS 发布", True),
    Relation("BrainstormSwarm", "depends-on", "BoardClient (Python)", "多智能体讨论发帖", True),
    Relation("FailureTracker", "depends-on", "Mosquitto", "跟踪 MQTT 消息失败模式", True),
    Relation("PiiMasker", "depends-on", "Observation", "日志隐写需要观测数据源", False),
    # ── 诊断体系 ──
    Relation("DiagnosisAgent", "depends-on", "CuriosityEngine",
             "好奇心触发是诊断的前置探测", True),
    Relation("DiagnosisAgent", "depends-on", "DreamEngine",
             "梦境引擎提供联想发散，辅助诊断", True),
    Relation("SkillsLearning", "depends-on", "DEEPSEEK_API_KEY",
             "技能学习依赖 LLM 推理", True),
    Relation("SkillsLearning", "depends-on", "ontology_model",
             "技能知识点应注册到本体", False),
    # ── Rust BoardService 内部包含关系 ──
    Relation("board_service_rs", "contains", "RegisterHandler",
             "src/handlers/register.rs", True),
    Relation("board_service_rs", "contains", "PostHandler",
             "src/handlers/post.rs", True),
    Relation("board_service_rs", "contains", "QueryHandler",
             "src/handlers/query.rs", True),
    Relation("board_service_rs", "contains", "FileHandler",
             "src/handlers/file.rs", True),
    Relation("board_service_rs", "contains", "WebhookHandler",
             "src/handlers/webhook.rs", True),
    Relation("board_service_rs", "contains", "Models",
             "src/models.rs", True),
    Relation("board_service_rs", "contains", "PluginIPC",
             "src/plugin_ipc.rs", True),
    Relation("RegisterHandler", "publishes-to", "BoardClient (Python)",
             "注册成功后广播 agent/bbs/{board}/registered", True),
    Relation("PostHandler", "publishes-to", "BoardClient (Python)",
             "新帖广播 agent/bbs/{board}/new_post", True),
]



# ══════════════════════════════════════════════════════════════
# Layer 3: 约束定义 (Constraints) — 从我踩过的坑中提取
# ══════════════════════════════════════════════════════════════

@dataclass
class Constraint:
    """必须成立的条件 — 不满足时系统异常"""
    description: str
    predicate: str               # 可检查的条件表达式（向后兼容，eval 执行）
    severity: str                # error / warning / info
    source: str                  # 从哪次失败中提取的
    fix: str                     # 修复方式
    check_fn: Optional[Callable] = None  # 可执行检查函数（优先于 predicate 字符串）


def run_checks(context: dict) -> list:
    """运行所有约束检查，返回 [ (约束, 通过/失败, 详情) ] 列表
    
    Args:
        context: 包含检查所需变量的字典
                 
                 
    Returns:
        每个元素: (constraint, passed: bool, detail: str)
    """
    results = []
    for c in CONSTRAINTS:
        try:
            if c.check_fn is not None:
                # 使用可执行函数（优先）
                passed = c.check_fn(context)
            else:
                # 向后兼容：eval 字符串表达式
                passed = eval(c.predicate, {"__builtins__": {}}, context)
            results.append((c, bool(passed), ""))
        except Exception as e:
            results.append((c, False, f"检查异常: {e}"))
    return results


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
        'board/ontology/query 请求中应含 "reply_to": "board/ontology/query/response/"',
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


def register_skills(skills_dir: str = None) -> tuple:
    """扫描 skills_learning/ 目录，将每个技能注册为实体+关系
    
    Args:
        skills_dir: skills_learning 目录路径（默认自动查找）
    
    Returns:
        (new_entities, new_relations) 动态生成的实体和关系列表
    """
    if skills_dir is None:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        skills_dir = os.path.join(_root, 'skills_learning')
    
    if not os.path.isdir(skills_dir):
        return [], []
    
    existing_names = set(e.name for e in ENTITIES)
    new_entities = []
    new_relations = []
    
    for skill_name in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, skill_name)
        if not os.path.isdir(skill_path):
            continue
        if skill_name in existing_names:
            continue
        
        n_files = sum(1 for f in os.listdir(skill_path) 
                     if os.path.isfile(os.path.join(skill_path, f)))
        entity = Component(
            name=skill_name,
            component_type="knowledge",
            language="text",
            status="learned",
            location=skill_path,
            verified_interactions=max(1, n_files)
        )
        new_entities.append(entity)
        new_relations.append(Relation(
            skill_name, "depends-on", "DEEPSEEK_API_KEY",
            "LLM 增强技能学习", True
        ))
        new_relations.append(Relation(
            "SkillsLearning", "contains", skill_name,
            skill_path, True
        ))
    
    return new_entities, new_relations
