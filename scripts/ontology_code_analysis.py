"""根据 OWL 本体分析 Beneh 代码优化方向"""
from rdflib import Graph
import sqlite3, pathlib

g = Graph()
g.parse("D:/open_claw_agent/Beneh/GA/ontology_full.ttl", format="turtle")

print("=" * 60)
print("Beneh 代码分析 - 基于 OWL 本体 + CodeGraph")
print("=" * 60)

# 1. 高耦合模块（被最多模块 import）
print("\n--- 1. 高耦合模块 (被最多 import) ---")
q1 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?target (COUNT(?source) AS ?cnt) WHERE {
        ?source ont:imports ?target .
    } GROUP BY ?target ORDER BY DESC(?cnt) LIMIT 5
""")
for r in q1:
    name = str(r.target).rsplit("_", 1)[-1]
    print(f"  被 {r.cnt} 个模块引用: {name}")

# 2. 孤立模块（无 import 关系）
print("\n--- 2. 孤立模块 (无 import 也无被 import) ---")
q2 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?mod WHERE {
        ?mod a ont:Module .
        FILTER NOT EXISTS { ?mod ont:imports|^ont:imports ?any . }
    } LIMIT 10
""")
for r in q2:
    name = str(r.mod).rsplit("_", 1)[-1]
    print(f"  孤立: {name}")

# 3. 热点函数 (call 入度)
print("\n--- 3. 热点函数 (被最多调用) ---")
q3 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?target (COUNT(?source) AS ?cnt) WHERE {
        ?source ont:calls ?target .
    } GROUP BY ?target ORDER BY DESC(?cnt) LIMIT 10
""")
for r in q3:
    name = str(r.target).rsplit("_", 1)[-1]
    print(f"  被调用 {r.cnt} 次: {name}")

# 4. 继承链深度
print("\n--- 4. 继承关系 ---")
q4 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?sub ?sup WHERE {
        ?sub ont:extends ?sup .
    } ORDER BY ?sub LIMIT 10
""")
for r in q4:
    sub = str(r.sub).rsplit("_", 1)[-1]
    sup = str(r.sup).rsplit("_", 1)[-1]
    print(f"  {sub} -> {sup}")

# 5. 用 CG 查最大文件
print("\n--- 5. 最大文件 (CodeGraph 统计) ---")
conn = sqlite3.connect("D:/open_claw_agent/Beneh/GA/.codegraph/codegraph.db")
c = conn.cursor()
c.execute("SELECT path FROM files ORDER BY LENGTH(path) DESC LIMIT 5")
for (path,) in c.fetchall():
    c2 = conn.cursor()
    c2.execute("SELECT COUNT(*) FROM nodes WHERE file_path=?", (path,))
    n = c2.fetchone()[0]
    print(f"  {n} 节点: {path}")
conn.close()

# 6. 建议
print("\n" + "=" * 60)
print("优化建议")
print("=" * 60)
print("""
1. 解耦: 高耦合模块应考虑拆分为子模块
2. 清理: 孤立模块检查是否可删
3. 缓存: 热点函数考虑缓存策略
4. 合并: 短继承链可考虑合并
5. 拆分: 大文件考虑拆分
""")
