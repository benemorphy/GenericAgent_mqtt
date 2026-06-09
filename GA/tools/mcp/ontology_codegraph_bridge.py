"""
ontology_codegraph_bridge — CodeGraph 活体代码图谱 → 本体模型的查询桥接层

核心功能：
  1. 自动从 CodeGraph DB 发现组件（实体），替代手写 ENTITIES 列表
  2. 自动从调用/导入边生成关系，替代手写 RELATIONS 列表
  3. 支持缓存 + TTL，减轻重复查询压力
  4. 当 CodeGraph 不可用时静默回退到静态数据

映射规则：
  - Python 包 (有 __init__.py 的目录) → library
  - Rust 项目 (有 Cargo.toml + main.rs) → service
  - 前端入口 (gateway, agentmain, launch.pyw) → service
  - tools 目录下的独立模块 → tool
  - imports/calls/instantiates 跨包边 → depends-on
  - 目录包含关系 → contains
"""

import os, sys, time, json, re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CG_DB_PATH = os.path.join(_GA_ROOT, ".codegraph", "codegraph.db")

# ── 缓存 ──────────────────────────────────────────────────
_cache = {}  # {key: (timestamp, data)}
_CACHE_TTL = 300  # 5 分钟


def _cache_get(key: str):
    """取缓存（过期返回 None）"""
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, data):
    _cache[key] = (time.time(), data)


# ── DB 连接 ────────────────────────────────────────────────

def _connect() -> Optional[object]:
    """sqlite3 connection or None"""
    try:
        import sqlite3
        conn = sqlite3.connect(_CG_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def db_available() -> bool:
    return os.path.exists(_CG_DB_PATH)


# ── 组件发现 ────────────────────────────────────────────────

# 已知的手动组件名 → CodeGraph 路径前缀映射
# 用于将 CG 节点名统一回 ontology 的手写命名
_KNOWN_COMPONENTS = {
    "MQTT Broker":          {"path_patterns": ["mosquitto", "rmqtt"], "type": "service"},
    "BoardService":         {"path_patterns": ["board_service_rs", "Mqtt_bbs_server"], "type": "service"},
    "HTTP Gateway":         {"path_patterns": ["web_ui/main.py", "web_ui"], "type": "gateway"},
    "LLM Core":            {"path_patterns": ["llmcore.py"], "type": "library"},
    "Agent Main":          {"path_patterns": ["agentmain.py"], "type": "service"},
    "TMWebDriver":         {"path_patterns": ["TMWebDriver.py"], "type": "tool"},
    "Fluentd":             {"path_patterns": ["fluentd"], "type": "service"},
    "QQ Bot":              {"path_patterns": ["qq_bot", "napcat"], "type": "service"},
    "飞书 Bot":            {"path_patterns": ["feishu", "fsapp.py", "lark"], "type": "service"},
    "Dashboard MQTT":      {"path_patterns": ["dashboard_mqtt.py"], "type": "tool"},
    "CodeGraph DB":        {"path_patterns": ["codegraph_db.py"], "type": "tool"},
    "GUIVision":           {"path_patterns": ["gui_vision.py"], "type": "tool"},
    "BBS Client":          {"path_patterns": ["Mqtt_bbs_client", "bbs_client"], "type": "library"},
    "Persistence":         {"path_patterns": ["persistence.py","Mqtt_bbs_server/persistence"], "type": "library"},
    "Mermaid Prerender":   {"path_patterns": ["mermaid_prerender.py"], "type": "tool"},
    "Courseware Pipeline": {"path_patterns": ["generate_courseware.py", "cell_diagram.py"], "type": "tool"},
    "CDP Search":          {"path_patterns": ["cdp_search"], "type": "tool"},
    "Goal Hive":           {"path_patterns": ["goal_hive","goal_mode","goal_nexus"], "type": "service"},
    "Rust MQTT Client":    {"path_patterns": ["mqtt_client_rs"], "type": "library"},
    "Inspiration Board":   {"path_patterns": ["inspiration_board.py"], "type": "tool"},
    "St App":              {"path_patterns": ["stapp.py"], "type": "service"},
    "IDE Connector":       {"path_patterns": ["continue_cmd.py","history_cmd.py"], "type": "tool"},
    "WebView App":         {"path_patterns": ["desktop_pet_v2.pyw"], "type": "service"},
    "聊天 App Common":     {"path_patterns": ["chatapp_common.py"], "type": "library"},
}


def _classify_component(file_path: str, node_kind: str, language: str) -> dict:
    """根据文件路径和节点信息自动分类组件类型"""
    fp = file_path.replace("\\", "/")
    base = os.path.basename(fp)
    dirname = os.path.dirname(fp).replace("\\", "/")

    # 检查已知组件映射
    for comp_name, info in _KNOWN_COMPONENTS.items():
        for pat in info["path_patterns"]:
            if pat in fp or pat in base or pat in dirname:
                return {"name": comp_name, "type": info["type"], "path": fp}

    # 自动分类规则
    # Rust 项目
    if language == "rust":
        if base == "main.rs":
            return {"name": os.path.basename(os.path.dirname(fp)), "type": "service", "path": fp}
        return {"name": os.path.basename(os.path.dirname(fp)), "type": "library", "path": fp}

    # Python 入口文件
    if base in ("agentmain.py", "launch.pyw", "main.py", "__main__.py"):
        dir_name = os.path.basename(os.path.dirname(fp))
        name = dir_name if dir_name and dir_name != "GA" else base.replace(".py", "")
        return {"name": name, "type": "service", "path": fp}

    # 工具目录
    if "tools" in dirname.split("/"):
        name = base.replace(".py", "").replace("_", " ").title()
        return {"name": name, "type": "tool", "path": fp}

    # 测试文件
    if "test" in dirname.split("/") or base.startswith("test_"):
        return {"name": base.replace(".py", ""), "type": "script", "path": fp}

    # 前端目录
    if "frontends" in dirname.split("/"):
        name = base.replace(".py", "").replace("_", " ").title()
        return {"name": name, "type": "service" if "__main__" in base else "tool", "path": fp}

    # Python package __init__
    if base == "__init__.py":
        name = os.path.basename(dirname).replace("_", " ").title()
        return {"name": name, "type": "library", "path": fp}

    # 通用: 将文件名作为组件名
    name = base.replace(".py", "").replace(".rs", "").replace("_", " ").title()
    return {"name": name, "type": "script", "path": fp}


# ── 查询函数 ────────────────────────────────────────────────

def discover_entities() -> list:
    """从 CodeGraph 文件扫描自动发现所有组件

    返回 Component 格式的 dict 列表:
        [{"name", "component_type", "path", "codegraph_nodes": [...], ...}]
    """
    cached = _cache_get("discover_entities")
    if cached:
        return cached

    conn = _connect()
    if not conn:
        _cache_set("discover_entities", [])
        return []

    try:
        cur = conn.cursor()
        # 获取所有文件 + 统计每个文件关联的节点/边
        cur.execute("""
            SELECT f.path, f.language, f.node_count, f.size,
                   (SELECT COUNT(*) FROM edges e 
                    JOIN nodes n ON e.source = n.id 
                    WHERE n.file_path = f.path AND e.kind = 'calls') AS call_edges,
                   (SELECT COUNT(*) FROM edges e 
                    JOIN nodes n ON e.source = n.id 
                    WHERE n.file_path = f.path AND e.kind = 'imports') AS import_edges
            FROM files f
            WHERE f.node_count > 0
            ORDER BY f.node_count DESC
        """)
        rows = cur.fetchall()

        # 按自动分类聚合组件
        comp_map = {}  # name -> aggregated info
        for row in rows:
            fp = row["path"]
            classification = _classify_component(fp, "file", row["language"] or "python")
            cname = classification["name"]

            if cname not in comp_map:
                comp_map[cname] = {
                    "name": cname,
                    "component_type": classification["type"],
                    "path": classification["path"],
                    "language": row["language"] or "python",
                    "files": [],
                    "total_nodes": 0,
                    "total_calls": 0,
                    "total_imports": 0,
                }

            entry = comp_map[cname]
            entry["files"].append(fp)
            entry["total_nodes"] += row["node_count"] or 0
            entry["total_calls"] += row["call_edges"] or 0
            entry["total_imports"] += row["import_edges"] or 0

        # 也检查 Rust 项目结构
        _scan_rust_projects(cur, comp_map)
        _scan_python_packages(cur, comp_map)

        result = list(comp_map.values())
        _cache_set("discover_entities", result)
        return result

    finally:
        conn.close()


def _scan_rust_projects(cur, comp_map: dict):
    """扫描 Rust Cargo.toml 项目作为 service"""
    try:
        cur.execute("""
            SELECT DISTINCT n.file_path, n.language
            FROM nodes n
            WHERE n.language = 'rust' AND n.kind = 'struct'
            LIMIT 50
        """)
        for row in cur.fetchall():
            fp = row["file_path"]
            if "target" in fp or ".cargo" in fp:
                continue
            # 提取项目名: .../project_name/src/...
            parts = fp.replace("\\", "/").split("/")
            for i, p in enumerate(parts):
                if p == "src" and i > 0:
                    proj_name = parts[i - 1]
                    if proj_name not in comp_map:
                        comp_map[proj_name] = {
                            "name": proj_name,
                            "component_type": "service",
                            "path": f"Mqtt_bbs_server/{proj_name}",
                            "language": "rust",
                            "files": [fp],
                            "total_nodes": 0,
                            "total_calls": 0,
                            "total_imports": 0,
                        }
                    elif fp not in comp_map[proj_name]["files"]:
                        comp_map[proj_name]["files"].append(fp)
                    break
    except Exception:
        pass  # 可有可无的补充扫描


def _scan_python_packages(cur, comp_map: dict):
    """扫描 Python __init__.py 包作为 library"""
    try:
        cur.execute("""
            SELECT DISTINCT n.file_path
            FROM nodes n
            WHERE n.name = '__init__' AND n.kind = 'function'
            LIMIT 50
        """)
        for row in cur.fetchall():
            fp = row["file_path"]
            pkg_dir = os.path.dirname(fp).replace("\\", "/")
            pkg_name = os.path.basename(pkg_dir).replace("_", " ").title()
            if pkg_name not in comp_map and pkg_name not in ("", "G"):
                comp_map[pkg_name] = {
                    "name": pkg_name,
                    "component_type": "library",
                    "path": pkg_dir,
                    "language": "python",
                    "files": [fp],
                    "total_nodes": 0,
                    "total_calls": 0,
                    "total_imports": 0,
                }
    except Exception:
        pass


def discover_relations() -> list:
    """从 CodeGraph 边数据自动发现组件间关系

    返回 Relation 格式的 dict 列表:
        [{"source", "target", "relation_type", "metadata", "evidence": [...]}]
    """
    cached = _cache_get("discover_relations")
    if cached:
        return cached

    # 先获取实体列表建立 name ↔ file_paths 映射
    entities = discover_entities()
    if not entities:
        _cache_set("discover_relations", [])
        return []

    # 构建 file_path → component_name 反向映射
    path_to_comp = {}
    for e in entities:
        for fp in e.get("files", []):
            path_to_comp[fp] = e["name"]

    conn = _connect()
    if not conn:
        _cache_set("discover_relations", [])
        return []

    try:
        cur = conn.cursor()
        # 找到所有跨组件的调用边
        cur.execute("""
            SELECT e.kind, e.line, 
                   n1.file_path AS source_file, n1.name AS source_name,
                   n2.file_path AS target_file, n2.name AS target_name
            FROM edges e
            JOIN nodes n1 ON e.source = n1.id
            JOIN nodes n2 ON e.target = n2.id
            WHERE e.kind IN ('calls', 'imports', 'instantiates', 'extends')
              AND n1.file_path != n2.file_path
              AND n1.file_path IS NOT NULL AND n2.file_path IS NOT NULL
            LIMIT 2000
        """)
        rows = cur.fetchall()

        # 聚合为组件间关系
        relation_map = {}  # (src_comp, tgt_comp, kind) -> aggregated info
        for row in rows:
            src_comp = path_to_comp.get(row["source_file"])
            tgt_comp = path_to_comp.get(row["target_file"])
            if not src_comp or not tgt_comp or src_comp == tgt_comp:
                continue

            key = (src_comp, tgt_comp, row["kind"])
            if key not in relation_map:
                relation_map[key] = {
                    "source": src_comp,
                    "target": tgt_comp,
                    "relation_type": "depends-on" if row["kind"] != "extends" else "extends",
                    "metadata": f"via {row['kind']}",
                    "evidence": [],
                    "count": 0,
                }
            relation_map[key]["count"] += 1
            if len(relation_map[key]["evidence"]) < 5:
                relation_map[key]["evidence"].append(
                    f"{row['source_name']} ({os.path.basename(row['source_file'])}) -> "
                    f"{row['target_name']} ({os.path.basename(row['target_file'])}):{row['line']}"
                )

        # 添加 contains 关系 (基于文件路径层级)
        _add_contains_relations(cur, path_to_comp, relation_map)

        # 加入已知的手动关系作为补充
        _merge_known_relations(relation_map)

        result = []
        for key, data in relation_map.items():
            data["weight"] = min(data["count"], 100)
            result.append(data)

        result.sort(key=lambda r: r["weight"], reverse=True)
        _cache_set("discover_relations", result)
        return result

    finally:
        conn.close()


def _add_contains_relations(cur, path_to_comp: dict, relation_map: dict):
    """从文件目录结构推断 contains 关系"""
    try:
        cur.execute("""
            SELECT DISTINCT n.file_path FROM nodes n WHERE n.kind = 'file'
            LIMIT 500
        """)
        # 构建前缀树
        comp_paths = {}
        for fp, cname in path_to_comp.items():
            for prefix, other_name in path_to_comp.items():
                if (
                    fp != prefix
                    and fp.startswith(prefix + "/") or fp.startswith(prefix + "\\")
                ):
                    key = (other_name, cname, "contains")
                    if key not in relation_map:
                        relation_map[key] = {
                            "source": other_name,
                            "target": cname,
                            "relation_type": "contains",
                            "metadata": "file hierarchy",
                            "evidence": [f"{prefix} -> {fp}"],
                            "count": 1,
                        }
                    else:
                        relation_map[key]["count"] += 1
                        if len(relation_map[key]["evidence"]) < 3:
                            relation_map[key]["evidence"].append(f"{prefix} -> {fp}")
                    break
    except Exception:
        pass


_MANUAL_RELATIONS = [
    # (source, target, type) — 补充 CodeGraph 无法直接捕获的运行时关系
    ("BoardService", "MQTT Broker", "connects-to"),
    ("HTTP Gateway", "BoardService", "connects-to"),
    ("飞书 Bot", "BoardService", "connects-to"),
    ("QQ Bot", "BoardService", "connects-to"),
    ("Dashboard MQTT", "MQTT Broker", "connects-to"),
    ("Agent Main", "HTTP Gateway", "connects-to"),
    ("LLM Core", "CodeGraph DB", "depends-on"),
    ("Agent Main", "LLM Core", "depends-on"),
    ("BoardService", "Persistence", "depends-on"),
]


def _merge_known_relations(relation_map: dict):
    """合并已知的运行时关系（不依赖静态代码分析）"""
    for src, tgt, rtype in _MANUAL_RELATIONS:
        key = (src, tgt, rtype)
        if key not in relation_map:
            relation_map[key] = {
                "source": src,
                "target": tgt,
                "relation_type": rtype,
                "metadata": f"runtime {rtype}",
                "evidence": ["known runtime dependency"],
                "count": 1,
                "weight": 5,
            }


# ── 状态检测 ────────────────────────────────────────────────

def _detect_process_running(name_part: str) -> bool:
    """检查进程列表中是否包含指定名称"""
    try:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        return name_part.lower() in result.stdout.lower()
    except Exception:
        return False


def check_component_status(name: str, path: str) -> str:
    """检测组件运行状态"""
    # 已知的服务进程检测模式
    service_patterns = {
        "MQTT Broker": ["mosquitto.exe", "rmqtt.exe"],
        "BoardService": ["board_service", "board_service_rs"],
        "HTTP Gateway": ["python", "gateway"],
        "飞书 Bot": ["python", "fsapp"],
        "QQ Bot": ["napcat", "qq_bot"],
        "Dashboard MQTT": ["python", "dashboard_mqtt"],
        "Agent Main": ["python", "agentmain"],
    }

    patterns = service_patterns.get(name, [os.path.basename(path).replace(".py", "")])
    for pat in patterns:
        if _detect_process_running(pat):
            return "running"
    return "stopped"


# ── 统一接口 ────────────────────────────────────────────────

def get_cg_entities() -> list:
    """获取 CodeGraph 发现的实体列表（与 ontology_model.Component 兼容格式）"""
    return discover_entities()


def get_cg_relations() -> list:
    """获取 CodeGraph 发现的关系列表（与 ontology_model.Relation 兼容格式）"""
    return discover_relations()


def get_cg_summary() -> dict:
    """获取 CodeGraph 本体摘要"""
    entities = discover_entities()
    relations = discover_relations()
    return {
        "source": "codegraph",
        "db_path": _CG_DB_PATH,
        "entities_count": len(entities),
        "relations_count": len(relations),
        "total_cg_nodes": 0,
        "total_cg_edges": 0,
        "entities": entities[:5] if entities else [],
        "sample_relations": relations[:5] if relations else [],
    }


def invalidate_cache():
    """手动清除缓存（在 codegraph sync 后调用）"""
    _cache.clear()


# ── 自测 ────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print(f"CodeGraph DB: {_CG_DB_PATH} (exists={db_available()})")
    print()

    if db_available():
        entities = discover_entities()
        print(f"=== Discovered Entities ({len(entities)}) ===")
        for e in sorted(entities, key=lambda x: x["total_nodes"], reverse=True)[:30]:
            print(f"  [{e['component_type']:8s}] {e['name']:25s}  "
                  f"nodes={e['total_nodes']:>4d}  calls={e['total_calls']:>3d}  "
                  f"imports={e['total_imports']:>3d}  files={len(e['files'])}")

        relations = discover_relations()
        print(f"\n=== Discovered Relations ({len(relations)}) ===")
        for r in sorted(relations, key=lambda x: x["count"], reverse=True)[:30]:
            print(f"  {r['source']:25s} --[{r['relation_type']:12s}]--> {r['target']:25s}  "
                  f"(x{r['count']})")
    else:
        print("CodeGraph DB not available - will use static fallback")
