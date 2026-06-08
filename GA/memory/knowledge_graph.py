"""
Knowledge Graph -- 从 L2 global_mem.txt 提取的实体关系知识图谱

提供 query_entity() API 查询实体属性和关系。
基于 SQLite 存储，零依赖。

Usage:
    from memory.knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    entity = kg.query_entity("GATEWAY")
    rels = kg.query_relations("MQTT_BBS")
"""

import os
import re
import sqlite3
from typing import Optional, List, Dict, Any

# -- 路径配置 --
_MEMORY_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_MEMORY_DIR, ".knowledge_graph.db")
_L2_PATH = os.path.join(_MEMORY_DIR, "global_mem.txt")


class KnowledgeGraph:
    """从 L2 global_mem.txt 构建的实体关系知识图谱。"""

    DB_SCHEMA = """
    CREATE TABLE IF NOT EXISTS entities (
        name        TEXT PRIMARY KEY,
        section     TEXT NOT NULL,
        description TEXT DEFAULT '',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS properties (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        entity   TEXT NOT NULL REFERENCES entities(name),
        key      TEXT NOT NULL,
        value    TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS relations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        source      TEXT NOT NULL REFERENCES entities(name),
        target      TEXT NOT NULL REFERENCES entities(name),
        relation    TEXT NOT NULL,
        weight      REAL DEFAULT 1.0,
        description TEXT DEFAULT '',
        UNIQUE(source, target, relation)
    );
    CREATE INDEX IF NOT EXISTS idx_properties_entity ON properties(entity);
    CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source);
    CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target);
    """

    def __init__(self, rebuild: bool = False):
        self.db_path = _DB_PATH
        if rebuild:
            self._drop_db()
        self._init_db()
        # 检查是否需要重建
        if self._count_entities() == 0:
            self._build_from_l2()

    # ---- 内部数据库操作 ----

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(self.DB_SCHEMA)
        conn.commit()
        conn.close()

    def _drop_db(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _count_entities(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        conn.close()
        return row[0] if row else 0

    def _count_relations(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM relations").fetchone()
        conn.close()
        return row[0] if row else 0

    # ---- 从 L2 构建 ----

    def _build_from_l2(self):
        if not os.path.isfile(_L2_PATH):
            return

        with open(_L2_PATH, encoding="utf-8") as f:
            text = f.read()

        # 解析 section
        section_pattern = re.compile(r"^##\s+\[(\w+)\]", re.MULTILINE)
        section_matches = list(section_pattern.finditer(text))

        entities_data = {}

        for i, m in enumerate(section_matches):
            sec_name = m.group(1)
            start = m.end()
            end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
            section_text = text[start:end].strip()

            # 提取描述（第一行非空非注释文本）
            desc_lines = []
            for line in section_text.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    desc_lines.append(line)
                    break
            description = desc_lines[0][:200] if desc_lines else ""

            # 提取 key=value 属性
            properties = {}
            for kv_match in re.finditer(
                r"^(\w+(?:\.\w+)*)\s*=\s*(.+)$", section_text, re.MULTILINE
            ):
                properties[kv_match.group(1)] = kv_match.group(2).strip()

            entities_data[sec_name] = {
                "description": description,
                "properties": properties,
            }

        # 写入数据库
        conn = self._get_conn()
        for name, data in entities_data.items():
            conn.execute(
                "INSERT OR IGNORE INTO entities (name, section, description) VALUES (?, ?, ?)",
                (name, "L2", data["description"]),
            )
            for k, v in data["properties"].items():
                conn.execute(
                    "INSERT INTO properties (entity, key, value) VALUES (?, ?, ?)",
                    (name, k, v[:500]),
                )
        conn.commit()

        # 提取关系
        relations = set()
        for name, data in entities_data.items():
            section_text = self._get_section_text(name)
            if section_text:
                for rel in self._extract_relations(name, section_text, entities_data):
                    relations.add(rel)

        for src, tgt, rel, weight, desc in relations:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO relations (source, target, relation, weight, description) VALUES (?, ?, ?, ?, ?)",
                    (src, tgt, rel, weight, desc),
                )
            except Exception:
                pass
        conn.commit()
        conn.close()

    def _get_section_text(self, section_name: str) -> Optional[str]:
        """从 L2 文件中提取指定 section 的文本。"""
        if not os.path.isfile(_L2_PATH):
            return None
        with open(_L2_PATH, encoding="utf-8") as f:
            text = f.read()
        pattern = re.compile(
            r"^##\s+\[" + re.escape(section_name) + r"\](.*?)(?=^##\s+\[|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(text)
        return m.group(1).strip() if m else None

    def _extract_relations(
        self, source_entity: str, section_text: str, entities: dict
    ) -> List[tuple]:
        """从 section 文本中提取实体关系。"""
        relations = []
        entity_names = list(entities.keys())
        rel_patterns = [
            (r"依赖\s*(.+?)(?:，|\)|$)", "depends_on"),
            (r"基于\s*(.+?)(?:构建|实现|开发|的)", "based_on"),
            (r"使用\s*(.+?)(?:作为|来|实现|通信|连接)", "uses"),
            (r"连接\s*(.+?)(?:，|\)|$)", "connects_to"),
            (r"运行于\s*(.+?)(?:上|)", "runs_on"),
            (r"提供\s*(.+?)(?:服务|API|接口)", "provides"),
            (r"调用\s*(.+?)(?:API|服务|接口)", "calls"),
            (r"发送到\s*(.+?)(?:，|\)|$)", "sends_to"),
            (r"订阅\s*(.+?)(?:topic|主题)", "subscribes_to"),
        ]

        for pattern, rel_type in rel_patterns:
            for match in re.finditer(pattern, section_text):
                target_text = match.group(1).strip()
                for ent_name in entity_names:
                    if (
                        ent_name != source_entity
                        and ent_name.lower() in target_text.lower()
                    ):
                        relations.append(
                            (
                                source_entity,
                                ent_name,
                                rel_type,
                                0.8,
                                f"detected via pattern '{rel_type}': {target_text[:50]}",
                            )
                        )

        # 跨实体引用检测
        desc = entities[source_entity]["description"].lower()
        for other in entity_names:
            if other != source_entity and other.lower() in desc:
                relations.append(
                    (source_entity, other, "references", 0.5, "cross-reference in description")
                )

        return relations

    # ---- 公开 API ----

    def query_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """查询单个实体。"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT name, section, description FROM entities WHERE name = ?",
            (name.upper(),),
        ).fetchone()
        if not row:
            conn.close()
            return None

        props = conn.execute(
            "SELECT key, value FROM properties WHERE entity = ?", (name.upper(),)
        ).fetchall()

        result = dict(row)
        result["properties"] = [(p["key"], p["value"]) for p in props]
        conn.close()
        return result

    def query_relations(self, name: str) -> List[Dict[str, Any]]:
        """查询实体的所有关系。"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT source, target, relation, weight, description
               FROM relations
               WHERE source = ? OR target = ?
               ORDER BY weight DESC""",
            (name.upper(), name.upper()),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


    def extend_from_codegraph(self) -> int:
        """从 CodeGraph 索引注入符号到知识图谱"""
        count = 0
        try:
            from tools.codegraph_mcp import codegraph_call
            
            # 获取关键符号
            for query in ['class', 'def', 'route', 'app', 'main', 'config']:
                try:
                    raw = codegraph_call("codegraph_search", {"query": query}, workspace=r"D:\open_claw_agent\Beneh\GA")
                    if isinstance(raw, dict) and raw.get("status") == "success":
                        data = raw.get("data", [])
                        if isinstance(data, list):
                            for item in data[:20]:
                                node = item.get("node", item)
                                name = node.get("name") or node.get("qualifiedName")
                                if name and not self.query_entity(name.upper()):
                                    conn = self._get_conn()
                                    conn.execute(
                                        "INSERT OR IGNORE INTO entities (name, section, description) VALUES (?, ?, ?)",
                                        (name.upper(), "CODEGRAPH", f"{node.get('kind','?')}: {node.get('filePath','')}")
                                    )
                                    conn.commit()
                                    conn.close()
                                    count += 1
                except Exception:
                    pass
        except Exception:
            pass
        return count

    def list_entities(self) -> List[str]:
        """列出所有实体名称。"""
        conn = self._get_conn()
        rows = conn.execute("SELECT name FROM entities ORDER BY name").fetchall()
        conn.close()
        return [r["name"] for r in rows]

    def search_entities(self, keyword: str) -> List[Dict[str, Any]]:
        """按关键词搜索实体。"""
        conn = self._get_conn()
        pattern = f"%{keyword}%"
        rows = conn.execute(
            """SELECT e.name, e.description,
                      GROUP_CONCAT(DISTINCT p.key || '=' || p.value, '; ') as props_sample
               FROM entities e
               LEFT JOIN properties p ON p.entity = e.name
               WHERE e.name LIKE ? OR e.description LIKE ? OR p.key LIKE ? OR p.value LIKE ?
               GROUP BY e.name
               LIMIT 20""",
            (pattern, pattern, pattern, pattern),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ---- 便捷函数 ----
def query_entity(name: str) -> Optional[Dict[str, Any]]:
    """便捷函数：查询实体。"""
    return KnowledgeGraph().query_entity(name)


def query_relations(name: str) -> List[Dict[str, Any]]:
    """便捷函数：查询关系。"""
    return KnowledgeGraph().query_relations(name)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rebuild = "--rebuild" in sys.argv
    if rebuild:
        sys.argv.remove("--rebuild")

    kg = KnowledgeGraph(rebuild=rebuild)

    if len(sys.argv) > 1:
        entity = sys.argv[1].upper()
        ent = kg.query_entity(entity)
        if ent:
            props_str = "; ".join(f"{k}={v}" for k, v in ent["properties"][:5])
            print(f"=== Entity: [{ent['name']}] ===")
            print(f"  Description: {ent['description'][:120]}")
            print(f"  Properties: {props_str}")
            rels = kg.query_relations(entity)
            if rels:
                print(f"  Relations ({len(rels)}):")
                for r in rels[:8]:
                    arrow = "-->"
                    if r["source"] == entity:
                        arrow = "-->"
                    else:
                        arrow = "<--"
                    print(f"    {r['source']} {arrow} {r['target']}  [{r['relation']}]")
        else:
            print(f"Entity [{entity}] not found")
            entities = kg.list_entities()
            print(f"Available ({len(entities)}): {', '.join(entities[:15])}")
    else:
        entities = kg.list_entities()
        print(f"=== Knowledge Graph ===")
        print(f"  Entities: {len(entities)}")
        print(f"  Relations: {kg._count_relations()}")
        print(f"  DB: {_DB_PATH}")
        print(f"\nUse: python knowledge_graph.py <ENTITY_NAME>")
        print(f"Example: python knowledge_graph.py GATEWAY")
        print(f"  --rebuild to rebuild from scratch")
        print(f"\nEntities: {', '.join(entities[:20])}")
