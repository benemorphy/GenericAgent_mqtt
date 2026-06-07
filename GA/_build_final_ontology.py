"""最终版 OWL 本体构建 - 含全部6种 edge kinds"""
import sqlite3, pathlib, re
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL

NS = Namespace("http://beneh.ga/ontology/")
g = Graph()
g.bind("ont", NS)

def su(text):
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
    safe = re.sub(r'_+', '_', safe).strip('_')
    return NS[safe] if safe else NS[f"node_{abs(hash(text))}"]

# 类
for cls in ["CodeComponent","Function","Module","Class_","Variable","ImportStatement","Risk"]:
    g.add((NS[cls], RDF.type, OWL.Class))

# 属性
for prop in ["imports","calls","dependsOn","defines","extends","instantiates","references","contains"]:
    g.add((NS[prop], RDF.type, OWL.ObjectProperty))
g.add((NS.dependsOn, RDF.type, OWL.TransitiveProperty))

# 从 CG DB
cg_db = pathlib.Path("D:/open_claw_agent/Beneh/GA/.codegraph/codegraph.db")
conn = sqlite3.connect(str(cg_db))
c = conn.cursor()

for kind in ["imports","calls","contains","extends","instantiates","references"]:
    c.execute("SELECT source, target FROM edges WHERE kind=? LIMIT 200", (kind,))
    edges = c.fetchall()
    prop = NS[kind]
    for src, tgt in edges:
        g.add((su(src), prop, su(tgt)))
    print(f"  {kind}: {len(edges)}")

# 文件模块
c.execute("SELECT path FROM files LIMIT 100")
for (path,) in c.fetchall():
    uri = su(path)
    g.add((uri, RDF.type, NS.Module))
    g.add((uri, RDFS.label, Literal(path)))

conn.close()
print(f"\n三员组: {len(g)}")

out = pathlib.Path("D:/open_claw_agent/Beneh/GA/ontology_full.ttl")
g.serialize(str(out), format="turtle")
print(f"保存: {out}")
