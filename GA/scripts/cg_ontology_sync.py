"""Step 3: CG-OWL 自动同步管线"""
import sqlite3, pathlib, re, json
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL

NS = Namespace("http://beneh.ga/ontology/")

def build_ontology(db_path, ttl_path, limit=500):
    g = Graph()
    g.bind("ont", NS)
    
    def su(text):
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
        safe = re.sub(r'_+', '_', safe).strip('_')
        return NS[safe] if safe else NS[f"n_{abs(hash(text))}"]
    
    # 类+属性
    for cls in ["Module","Function","Class_","Variable","Import","Risk"]:
        g.add((NS[cls], RDF.type, OWL.Class))
    for prop in ["imports","calls","dependsOn","defines","references","contains","extends","instantiates"]:
        g.add((NS[prop], RDF.type, OWL.ObjectProperty))
    g.add((NS.dependsOn, RDF.type, OWL.TransitiveProperty))
    
    # 从 CG DB 读取
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    for kind in ["imports","calls","contains","extends","instantiates","references"]:
        c.execute("SELECT source, target FROM edges WHERE kind=? LIMIT ?", (kind, limit))
        for src, tgt in c.fetchall():
            g.add((su(src), NS[kind], su(tgt)))
    
    c.execute("SELECT path FROM files")
    for (path,) in c.fetchall():
        uri = su(path)
        g.add((uri, RDF.type, NS.Module))
        g.add((uri, RDFS.label, Literal(path)))
    
    conn.close()
    g.serialize(str(ttl_path), format="turtle")
    return len(g)

if __name__ == "__main__":
    cg_db = pathlib.Path("D:/open_claw_agent/Beneh/GA/.codegraph/codegraph.db")
    ttl_out = pathlib.Path("D:/open_claw_agent/Beneh/GA/ontology_full.ttl")
    n = build_ontology(cg_db, ttl_out)
    print(f"同步完成: {n} 三员组 -> {ttl_out}")
    print("历史变化 (简化): 本次新增全部6种 edge kinds")
