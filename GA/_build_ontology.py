"""CodeGraph -> OWL 本体生成"""
import subprocess, json, sys
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL

NS = Namespace("http://beneh.ga/ontology/")
g = Graph()
g.bind("ont", NS)

# 1. 定义类
g.add((NS.CodeComponent, RDF.type, OWL.Class))
g.add((NS.Function, RDF.type, OWL.Class))
g.add((NS.Module, RDF.type, OWL.Class))
g.add((NS.Class_, RDF.type, OWL.Class))  # Class_ to avoid Python keyword
g.add((NS.Variable, RDF.type, OWL.Class))

# 2. 属性
for p, t in [("imports", OWL.ObjectProperty), ("calls", OWL.ObjectProperty), 
             ("dependsOn", OWL.ObjectProperty), ("defines", OWL.ObjectProperty)]:
    g.add((NS[p], RDF.type, t))

g.add((NS.dependsOn, RDF.type, OWL.TransitiveProperty))

# 3. 从 CodeGraph 获取数据 - 用 sqlite3 直接查
import sqlite3, pathlib
cg_db = pathlib.Path(".codegraph/codegraph.db")
if cg_db.exists():
    conn = sqlite3.connect(str(cg_db))
    cursor = conn.cursor()
    
    # 查所有文件
    cursor.execute("SELECT path FROM files LIMIT 50")
    files = cursor.fetchall()
    for (fpath,) in files:
        uri = NS[fpath.replace(".", "_").replace("/", "_").replace("\\", "_")]
        g.add((uri, RDF.type, NS.Module))
        g.add((uri, RDFS.label, Literal(fpath)))
    
    # 查 edges 中的 import 关系（kind='import' 的边）
    cursor.execute("""
        SELECT DISTINCT e.source, e.target FROM edges e
        WHERE e.kind = 'imports'
        LIMIT 100
    """)
    imports = cursor.fetchall()
    print(f"Edges imports: {len(imports)} 条")
    for src, tgt in imports[:10]:
        s = NS[src.replace(".", "_").replace("/", "_").replace("\\", "_")]
        t = NS[tgt.replace(".", "_").replace("/", "_").replace("\\", "_")]
        g.add((s, NS.imports, t))
    
    # 文件与 import 的关系: contains 边
    cursor.execute("""
        SELECT e.source, e.target FROM edges e
        WHERE e.kind = 'contains'
        LIMIT 50
    """)
    contains = cursor.fetchall()
    print(f"Edges contains: {len(contains)} 条")
    for src, tgt in contains[:10]:
        s = NS[src.replace(".", "_").replace("/", "_").replace("\\", "_")]
        t = NS[tgt.replace(".", "_").replace("/", "_").replace("\\", "_")]
        g.add((s, NS.defines, t))
    
    # 用 nodes 表
    cursor.execute("SELECT DISTINCT file_path FROM nodes LIMIT 50")
    files = cursor.fetchall()
    for (fpath,) in files:
        uri = NS[fpath.replace(".", "_").replace("/", "_").replace("\\", "_")]
        g.add((uri, RDF.type, NS.Module))
        g.add((uri, RDFS.label, Literal(fpath)))
    
    conn.close()
    print(f"查询: {len(imports)} import 关系, {len(files)} 文件")

# 4. 推理: imports + transitive = dependsOn
# RDFLib 自动支持传递性

# 5. SPARQL 查询示例
q = """
PREFIX ont: <http://beneh.ga/ontology/>
SELECT ?module ?import WHERE {
    ?module ont:imports ?import .
} LIMIT 10
"""
for row in g.query(q):
    print(f"  {row[0].split('/')[-1]} -> {row[1].split('/')[-1]}")

import pathlib as pl
out = pl.Path("D:/open_claw_agent/Beneh/GA/ontology_combined.ttl")
g.serialize(str(out), format="turtle")
print(f"\n保存: {out} ({len(g)} triples)")
