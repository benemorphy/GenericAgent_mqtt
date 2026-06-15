"""甲骨文本体模型 — Schema 定义"""
# 四层本体架构：Glyph → Component → Grapheme → Sense
# 存储后端：Neo4j (首选) + RDF/JSON (可移植备份)

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "neo4j"  # 默认密码，需确认
