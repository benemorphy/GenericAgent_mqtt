"""
Project Ontology — 基于反省的要素-关系-约束-推理模型

从 100+ 轮交互中提取的经验本体：
  实体 — 我操作过的所有组件（去重后）
  关系 — 我验证过的连接
  约束 — 我踩过的坑（可执行检查）
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
    component_type: str          # service / library / tool / config / credential
    language: str                # python / rust / binary / config
    status: str                  # running / compiled / static / replaced
    location: str                # 文件路径
    verified_interactions: int   # 我确认过的交互次数


def _resolve_tool_path(subpath: str) -> str:
    """统一解析工具路径：优先 check GA_tools/ 和 Mqtt_bbs_server/tools/"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ga_tools = os.path.join(root, "GA_tools", subpath)
    if os.path.exists(ga_tools):
        return ga_tools
    return os.path.join(root, "Mqtt_bbs_server", "tools", subpath)


# 从我经验中提取的实体（已去重，路径已更新）
ENTITIES = [
    # ── 核心服务 ──
    Component("BoardService (Rust)", "service", "rust", "running PID 7836",
              _resolve_tool_path("board_service_rs/"), 47),
    Component("Mosquitto", "service", "binary", "running PID 6544",
              os.environ.get("MOSQUITTO_HOME", r"D:\\tools\\mosquitto") + "/" + os.environ.get("MOSQUITTO_EXE", "mosquitto.exe"), 8),
    Component("MariaDB", "service", "binary", "running",
              "127.0.0.1:3306", 6),
    Component("HTTP Gateway", "service", "python", "running",
              "GA/frontends/gateway/", 12),
    Component("RmqtWebUI", "service", "rust", "running PID 3108",
              _resolve_tool_path("rmqtt_webui_rs/"), 3),
    Component("RmqtAuth", "service", "rust", "compiled",
              _resolve_tool_path("rmqtt_auth_rs/"), 2),
    Component("simphtml_rs", "tool", "rust", "running",
              _resolve_tool_path("simphtml_rs/"), 1),
    Component("md_server_rs", "tool", "rust", "running PID 11296",
              os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "GA_tools", "md_server_rs/"), 6),

    # ── Python 核心库（新 Mqtt_bbs_server 包） ──
    Component("Mqtt_bbs_server (Python)", "library", "python", "stable",
              "Mqtt_bbs_server/", 15),
    Component("BBSClient", "library", "python", "stable",
              "Mqtt_bbs_client/client.py", 30),
    Component("BoardClient (Python)", "library", "python", "stable",
              "Mqtt_bbs_client/board_client.py", 30),
    Component("PluginManager", "library", "python", "stable",
              "Mqtt_bbs_server/plugin_manager.py", 4),
    Component("Persistence", "library", "python", "stable",
              "Mqtt_bbs_server/persistence.py", 3),
    Component("PersistenceWorker", "library", "python", "stable",
              "Mqtt_bbs_server/persistence_worker.py", 2),
    Component("Scheduler (Python)", "library", "python", "stable",
              "Mqtt_bbs_server/scheduler.py", 3),
    Component("Dag (Python)", "library", "python", "stable",
              "Mqtt_bbs_server/dag.py", 3),
    Component("FileTransferV2", "library", "python", "stable",
              "Mqtt_bbs_server/file_transfer_v2.py", 2),
    Component("MqttAgentRunner", "library", "python", "stable",
              "Mqtt_bbs_server/mqtt_agent_runner.py", 2),
    Component("Plugin", "library", "python", "stable",
              "Mqtt_bbs_server/plugin_manager.py", 2),
    Component("Registry", "library", "python", "stable",
              "Mqtt_bbs_server/board_service.py", 3),

    # ── Rust 库 ──
    Component("Mqtt_bbs_rs (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/"), 10),
    Component("BBSClient (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/client/bbs_client.rs"), 8),
    Component("BoardClient (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/client/board_client.rs"), 6),
    Component("AgentBoard (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/agent_board.rs"), 5),
    Component("WorkerAgent (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/worker_agent.rs"), 5),
    Component("CapabilityRegistry", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/capability.rs"), 4),
    Component("StateKv", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/state_kv.rs"), 2),

    # ── BoardService (Rust) 内部处理模块 ──
    Component("RegisterHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/register.rs"), 1),
    Component("PostHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/post.rs"), 1),
    Component("QueryHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/query.rs"), 1),
    Component("FileHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/file.rs"), 1),
    Component("WebhookHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/webhook.rs"), 1),
    Component("CapabilityHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/handlers/capability.rs"), 1),
    Component("MqttHandler", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/mqtt_handler.rs"), 3),
    Component("AppState", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/app_state.rs"), 1),
    Component("Db", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/db.rs"), 3),
    Component("Config (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/config.rs"), 2),
    Component("Observability", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/observability.rs"), 2),
    Component("PluginIPC", "library", "rust", "compiled",
              _resolve_tool_path("board_service_rs/src/plugin_ipc.rs"), 1),

    # ── 工具 ──
    Component("DiagnosisAgent", "tool", "python", "stable",
              "GA/tools/diagnosis_agent.py", 3),
    Component("ontology_model (this file)", "tool", "python", "stable",
              "GA/tools/ontology_model.py", 5),
    Component("ReflectionEngine", "tool", "python", "stable",
              "GA/tools/reflection_engine.py", 1),
    Component("SkillsLearning", "tool", "python", "stable",
              "skills_learning/", 40),
    Component("FileTransfer (Rust)", "library", "rust", "compiled",
              _resolve_tool_path("mqtt_bbs_rs/src/file_transfer.rs"), 1),

    # ── 配置 ──
    Component("mykey.py", "config", "python", "static",
              "mykey.py", 2),
    Component("agent.env", "config", "env", "static",
              "Mqtt_bbs/agent.env", 5),
    Component("mosquitto_passwd", "config", "text", "static",
              os.environ.get("MOSQUITTO_HOME", r"D:\\tools\\mosquitto") + "/" + os.environ.get("MOSQUITTO_PASSWD", "mosquitto_passwd"), 3),
    Component("DEEPSEEK_API_KEY", "credential", "env_var", "updated",
              "setx DEEPSEEK_API_KEY", 3),
    Component("Mqtt_bbs_client (Python pkg)", "library", "python", "stable",
              "Mqtt_bbs_client/", 15),

    # ── 外部概念 ──
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
    relation_type: str           # depends-on / publishes-to / subscribes-to / contains / requires / replaces / drives
    target: str
    context: str                 # 什么条件下成立
    verified: bool               # 我是否测试验证过


RELATIONS = [
    # ── 服务依赖 ──
    Relation("BoardService (Rust)", "depends-on", "Mosquitto", "MQTT 端口 1883", True),
    Relation("BoardService (Rust)", "depends-on", "MariaDB", "DB 连接 mysql://root:mariadb@127.0.0.1", True),
    Relation("HTTP Gateway", "depends-on", "BoardClient (Python)", "转发请求到 BBS", True),
    Relation("HTTP Gateway", "publishes-to", "BoardService (Rust)", "HTTP -> MQTT 转发", True),
    Relation("RmqtWebUI", "depends-on", "Mosquitto", "RMQTT 管理界面", True),
    Relation("RmqtAuth", "depends-on", "Mosquitto", "认证回调 HTTP API", True),
    Relation("md_server_rs", "depends-on", "BoardService (Rust)", "md_server_rs 读取 bbs_posts 表", True),
    Relation("simphtml_rs", "depends-on", "BoardService (Rust)", "生成 HTML 页面", True),

    # ── Python 客户端依赖 ──
    Relation("BoardClient (Python)", "depends-on", "BBSClient", "import Mqtt_bbs_client.client", True),
    Relation("MqttAgentRunner", "depends-on", "BBSClient", "import Mqtt_bbs_client.client", True),
    Relation("PluginManager", "depends-on", "Plugin", "管理 plugin 对象", True),
    Relation("Registry", "depends-on", "BoardClient (Python)", "服务注册/发现", True),
    Relation("PersistenceWorker", "depends-on", "Persistence", "数据持久化", True),
    Relation("Persistence", "depends-on", "MariaDB", "数据库存储", True),

    # ── Rust 客户端依赖 ──
    Relation("BoardClient (Rust)", "depends-on", "BBSClient (Rust)", "crate Mqtt_bbs_rs", True),
    Relation("AgentBoard (Rust)", "depends-on", "BBSClient (Rust)", "use BBSClient", True),
    Relation("WorkerAgent (Rust)", "depends-on", "BBSClient (Rust)", "use BBSClient", True),

    # ── BoardService 内部结构 ──
    Relation("BoardService (Rust)", "contains", "MqttHandler", "src/mqtt_handler.rs", True),
    Relation("BoardService (Rust)", "contains", "AppState", "src/app_state.rs", True),
    Relation("BoardService (Rust)", "contains", "Db", "src/db.rs", True),
    Relation("BoardService (Rust)", "contains", "Config (Rust)", "src/config.rs", True),
    Relation("BoardService (Rust)", "contains", "CapabilityRegistry", "src/capability.rs", True),
    Relation("BoardService (Rust)", "contains", "FileTransfer (Rust)", "src/file_transfer.rs", True),
    Relation("BoardService (Rust)", "contains", "PluginIPC", "src/plugin_ipc.rs", True),
    Relation("BoardService (Rust)", "contains", "Observability", "src/observability.rs", True),
    Relation("BoardService (Rust)", "contains", "RegisterHandler", "src/handlers/register.rs", True),
    Relation("BoardService (Rust)", "contains", "PostHandler", "src/handlers/post.rs", True),
    Relation("BoardService (Rust)", "contains", "QueryHandler", "src/handlers/query.rs", True),
    Relation("BoardService (Rust)", "contains", "FileHandler", "src/handlers/file.rs", True),
    Relation("BoardService (Rust)", "contains", "WebhookHandler", "src/handlers/webhook.rs", True),
    Relation("BoardService (Rust)", "contains", "CapabilityHandler", "src/handlers/capability.rs", True),

    # ── Mqtt_bbs_rs 内部结构 ──
    Relation("Mqtt_bbs_rs (Rust)", "contains", "BBSClient (Rust)", "src/client/bbs_client.rs", True),
    Relation("Mqtt_bbs_rs (Rust)", "contains", "BoardClient (Rust)", "src/client/board_client.rs", True),
    Relation("Mqtt_bbs_rs (Rust)", "contains", "AgentBoard (Rust)", "src/agent_board.rs", True),
    Relation("Mqtt_bbs_rs (Rust)", "contains", "WorkerAgent (Rust)", "src/worker_agent.rs", True),
    Relation("Mqtt_bbs_rs (Rust)", "contains", "FileTransfer (Rust)", "src/file_transfer.rs", True),
    Relation("Mqtt_bbs_rs (Rust)", "contains", "StateKv", "src/state_kv.rs", True),

    # ── 通信关系 ──
    Relation("BoardClient (Python)", "publishes-to", "BoardService (Rust)",
             "agent/bbs/{board}/register -> agent/bbs/{board}/post", True),
    Relation("BoardClient (Rust)", "publishes-to", "BoardService (Rust)",
             "agent/bbs/{board}/register -> agent/bbs/{board}/post", True),
    Relation("BoardService (Rust)", "publishes-to", "BoardClient (Python)",
             "agent/bbs/{board}/new_post (broadcast)", True),
    Relation("BoardService (Rust)", "publishes-to", "World",
             "node/{id}/status (retain)", True),

    # ── 诊断模块关系 ──
    Relation("DiagnosisAgent", "subscribes-to", "BoardService (Rust)",
             "system/healthcheck/+/response", True),
    Relation("DiagnosisAgent", "subscribes-to", "World",
             "node/+/status + events/+/error", True),
    Relation("DiagnosisAgent", "publishes-to", "BoardService (Rust)",
             "board/diagnosis/post/ + board/diagnosis/summary", True),
    Relation("ontology_model (this file)", "drives", "DiagnosisAgent",
             "约束和推理来自模型", True),
    Relation("ReflectionEngine", "reads", "ontology_model (this file)",
             "导入 ENTITIES/RELATIONS 做偏差检测", True),

    # ── 技能学习 ──
    Relation("SkillsLearning", "depends-on", "DEEPSEEK_API_KEY", "LLM 增强需要 API Key", True),
]


# ══════════════════════════════════════════════════════════════
# Layer 3: 约束定义 (Constraints) — 从我踩过的坑中提取，可执行
# ══════════════════════════════════════════════════════════════

@dataclass
class Constraint:
    """一条可执行的检查项"""
    name: str
    check_fn: Optional[Callable[[dict], bool]]  # None 表示手动检查
    severity: str                      # error / warning / info
    description: str
    solution: str                      # 已知的解决方案


def _ensure_mosquitto_running(ctx: dict) -> bool:
    """Mosquitto 必须在运行"""
    import subprocess
    r = subprocess.run(["tasklist", "/fi", "PID eq 6544"], capture_output=True, text=True, timeout=5)
    return "PID" in r.stdout and "6544" in r.stdout

def _ensure_board_service(ctx: dict) -> bool:
    """BoardService (Rust) 必须在运行"""
    import subprocess
    r = subprocess.run(["tasklist", "/fi", "PID eq 7836"], capture_output=True, text=True, timeout=5)
    return "PID" in r.stdout and "7836" in r.stdout

def _ensure_gateway_port(ctx: dict) -> bool:
    """Gateway 8000 端口必须监听"""
    import subprocess
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
    return any("8000" in line and "LISTENING" in line for line in r.stdout.split('\n'))

def _ensure_md_server(http_port: int = 35831) -> bool:
    """md_server_rs 必须在运行"""
    import subprocess
    r = subprocess.run(["tasklist", "/fi", "PID eq 11296"], capture_output=True, text=True, timeout=5)
    return "PID" in r.stdout and "11296" in r.stdout


CONSTRAINTS = [
    Constraint(
        "Mosquitto 必须运行",
        _ensure_mosquitto_running, "error",
        "BoardService 依赖 MQTT 端口 1883",
        "启动 mosquitto.exe -c mosquitto.conf -v"
    ),
    Constraint(
        "BoardService (Rust) 必须运行",
        _ensure_board_service, "error",
        "所有 BBS 功能依赖 BoardService",
        "cd Mqtt_bbs_server/tools/board_service_rs && cargo run --release"
    ),
    Constraint(
        "HTTP Gateway 8000 端口必须监听",
        _ensure_gateway_port, "error",
        "Web UI 访问依赖 HTTP Gateway",
        "cd GA/frontends/gateway && python main.py"
    ),
    Constraint(
        "md_server_rs 必须运行",
        lambda ctx: _ensure_md_server(), "info",
        "代码查看器不在运行将不可用",
        "cd GA_tools/md_server_rs && cargo run --release"
    ),
    Constraint(
        "Rust 新功能发布到 BoardService 后必须重启二进制",
        None, "info",
        "编译新 binary -> taskkill -> 重新启动",
        "`taskkill /f /fi ... && cargo run --release ...`"
    ),
    Constraint(
        "本体查询必须传 reply_topic",
        None, "warning",
        "否则 BoardService 不知道往哪儿回",
        "注册时提供 publish topic，如 `agent/bbs/{board}/new_post`"
    ),
    Constraint(
        "Mosquitto 配置更改后必须重启",
        None, "info",
        "password_file / acl_file 仅在启动时读取",
        "修改后重启 mosquitto"
    ),
    Constraint(
        "MariaDB 必须能连接",
        None, "error",
        "BoardService 启动后立即连接 db，失败则退出",
        "检查 mysql 服务是否运行 / 端口是否被占用"
    ),
    Constraint(
        "BoardService 注册时 'BBS' 必须大写",
        None, "warning",
        "`connection_name` 若用 'bbs' 会被 Rust 和 Python 两端过滤掉",
        "注册时用 `BBS_xxx` 格式"
    ),
    Constraint(
        "发布诊断帖子必须先确保 board_service Agent 版存在",
        None, "info",
        "post 会报错但不致命（`agent-diagnosis` 板不存在）",
        "通过 gateway 诊断页面 POST /boards/diagnosis/run 触发"
    ),
]


# ══════════════════════════════════════════════════════════════
# Layer 4: 推理规则 (Inferences)
# ══════════════════════════════════════════════════════════════

@dataclass
class Inference:
    """推理规则：从现象推断结论，指导行动"""
    pattern: str           # 现象描述（关键词匹配）
    conclusion: str        # 推断结论
    action: str            # 推荐行动
    confidence: float      # 0.0 ~ 1.0


INFERENCES = [
    Inference("BoardService 启动后几秒就退出了",
              "Mosquitto/MariaDB 未运行或端口被占用",
              "先确保 Mosquitto 和 MariaDB 在运行", 0.95),
    Inference("Rust 编译报 aws-lc-sys 或 ring",
              "Cargo.toml 中 jsonwebtoken 编译原生 C 出错",
              "`default-features = false` 跳过 ring", 0.85),
    Inference("订阅收不到响应",
              "topic 前缀不匹配（BBSClient 自动加前缀）",
              "检查注册时的 reply_topic 是否与订阅一致", 0.80),
    Inference("服务器运行正常但 Web UI 打不开",
              "Gateway 未运行或端口被防火墙拦截",
              "检查 8000 端口监听", 0.90),
    Inference("MQTT 发布失败 (Connection refused)",
              "Mosquitto 未运行",
              "启动 Mosquitto", 0.98),
    Inference("本体模型与运行代码不一致",
              "GA 工具或服务变动了但本体未更新",
              "反省: 扫描 ENTITIES 中 status != running 和路径不存在的组件", 0.75),
    Inference("md_server_rs 页面打开但内容为空",
              "BoardService 数据库连接异常导致查询无结果",
              "检查 BoardService 日志 / 确认数据库表存在", 0.70),
    Inference("体检收集不到数据 / 诊断页面无数据",
              "DiagnosisAgent 30秒循环未启动或 topic 匹配不上",
              "检查 DiagnosisAgent 进程 + MQTT 订阅日志", 0.80),
]


# ══════════════════════════════════════════════════════════════
# 函数: 约束检查 + 推理链
# ══════════════════════════════════════════════════════════════

def run_checks(context: dict = None) -> list:
    """运行所有可执行的约束检查，返回违反项列表"""
    if context is None:
        context = {}
    results = []
    for c in CONSTRAINTS:
        if c.check_fn is None:
            continue
        try:
            ok = c.check_fn(context)
            if not ok:
                results.append({
                    "name": c.name,
                    "severity": c.severity,
                    "description": c.description,
                    "solution": c.solution,
                })
        except Exception as e:
            results.append({
                "name": c.name,
                "severity": "warning",
                "description": f"检查异常: {e}",
                "solution": c.solution,
            })
    return results


def run_inferences(context: dict) -> list:
    """对给定上下文执行推理匹配，返回排序后的推理结果"""
    results = []
    ctx_str = str(context)
    for inf in INFERENCES:
        if inf.pattern.lower() in ctx_str.lower():
            results.append({
                "conclusion": inf.conclusion,
                "action": inf.action,
                "confidence": inf.confidence,
                "matched": inf.pattern,
            })
    results.sort(key=lambda r: -r["confidence"])
    return results


def chain_inference(start_entity: str, goal: str, max_depth: int = 3) -> list:
    """链式推理：沿 depend-on / contains 关系从起点到目标找路径"""
    import collections

    adj = collections.defaultdict(list)
    for r in RELATIONS:
        if r.relation_type in ("depends-on", "contains", "publishes-to"):
            adj[r.source].append((r.target, r.relation_type))
            adj[r.target].append((r.source, r.relation_type + "-inv"))

    visited = {start_entity: (None, None)}
    q = collections.deque([start_entity])
    path = []
    found = False

    while q and len(visited) <= max_depth:
        node = q.popleft()
        if node == goal:
            found = True
            break
        for neighbor, rel_type in adj.get(node, []):
            if neighbor not in visited:
                visited[neighbor] = (node, rel_type)
                q.append(neighbor)

    if not found:
        return []

    # reconstruct
    cur = goal
    while cur != start_entity:
        parent, rel = visited[cur]
        path.append((parent, rel, cur))
        cur = parent
    path.reverse()
    return path


def check_constraints(state: dict) -> list[str]:
    """简单字符串匹配约束（兼容旧接口）"""
    # 不存在的约束检查：eval 不再执行，改用 run_checks()
    return []


def query_relations(entity: str, relation_type: str = None) -> list[Relation]:
    """查询指定实体的所有关系"""
    if relation_type:
        return [r for r in RELATIONS if (r.source == entity or r.target == entity) and r.relation_type == relation_type]
    return [r for r in RELATIONS if r.source == entity or r.target == entity]


def query_entities(component_type: str = None) -> list[Component]:
    """查询实体列表，可按类型过滤"""
    if component_type:
        return [e for e in ENTITIES if e.component_type == component_type]
    return list(ENTITIES)


def diagnose_system() -> dict:
    """运行完整检查+推理，返回诊断结果"""
    checks = run_checks({})
    context = {
        "checks": checks,
        "service_count": len([e for e in ENTITIES if e.component_type == "service"]),
        "running_count": len([e for e in ENTITIES if e.status.startswith("running")]),
        "board_service_running": any(c["name"] == "BoardService (Rust) 必须运行" and c.get("severity") == "error" for c in checks) is False,
    }

    # 推理
    inferences = []
    for c in checks:
        inferences.extend(run_inferences({"error": c["description"]}))

    return {
        "checks": checks,
        "inferences": inferences,
        "summary": f"{len(checks)} 个检查不通过 / {len(inferences)} 条推理匹配",
        "entities": [(e.name, e.component_type, e.status) for e in ENTITIES],
    }


def find_entity(name: str) -> Optional[Component]:
    """按名称查找实体"""
    for e in ENTITIES:
        if e.name.lower() == name.lower():
            return e
    return None
