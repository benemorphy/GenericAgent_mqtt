"""CG->OWL: 任意项目代码图 → OWL 本体建模工具"""
import sys, os, pathlib, sqlite3, subprocess, re, json
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL

def build_ontology(project_path, output=None, reset_cg=False):
    p = pathlib.Path(project_path).resolve()
    if not p.exists():
        print(f"路径不存在: {p}"); return
    
    # 1. 确保 CodeGraph 已索引
    cg_dir = p / ".codegraph"
    if not cg_dir.exists() or reset_cg:
        print(f"初始化 CodeGraph: {p}")
        subprocess.run(["codegraph", "init", "-i", str(p)],
            cwd=str(p), capture_output=True, text=True, timeout=120)
    
    # 2. 验证索引
    db = cg_dir / "codegraph.db"
    if not db.exists():
        print(f"CodeGraph DB 未找到: {db}"); return
    
    # 3. 读取 DB 构建本体
    proj_name = p.name
    ns_base = f"http://codegraph.ontology/{proj_name}/"
    NS = Namespace(ns_base)
    
    g = Graph()
    g.bind("ont", NS)
    g.add((NS.Project, RDF.type, OWL.Class))
    g.add((NS.File, RDF.type, OWL.Class))
    g.add((NS.Function, RDF.type, OWL.Class))
    g.add((NS.Class_, RDF.type, OWL.Class))
    g.add((NS.Module, RDF.type, OWL.Class))
    g.add((NS.Variable, RDF.type, OWL.Class))
    g.add((NS.Route, RDF.type, OWL.Class))
    
    for pname in ["imports", "calls", "contains", "extends", "instantiates", "references", "defines"]:
        prop = NS[pname]
        g.add((prop, RDF.type, OWL.ObjectProperty))
    
    g.add((NS.dependsOn, RDF.type, OWL.TransitiveProperty))
    g.add((NS.dependsOn, RDFS.subPropertyOf, NS.imports))
    
    # 项目实例
    g.add((NS[proj_name], RDF.type, NS.Project))
    g.add((NS[proj_name], RDFS.label, Literal(proj_name)))
    
    def su(text):
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', str(text))
        safe = re.sub(r'_+', '_', safe).strip('_')
        return NS[safe] if safe else NS[f"n{abs(hash(text))}"]
    
    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    
    # 文件
    c.execute("SELECT path FROM files")
    for (path,) in c.fetchall():
        uri = su(path)
        g.add((uri, RDF.type, NS.File))
        g.add((uri, RDFS.label, Literal(path)))
        g.add((su(proj_name), NS.contains, uri))
    
    # edges
    for kind in ["imports", "calls", "contains", "extends", "instantiates", "references"]:
        c.execute("SELECT source, target FROM edges WHERE kind=? LIMIT 200", (kind,))
        edges = c.fetchall()
        for src, tgt in edges:
            g.add((su(src), NS[kind], su(tgt)))
    
    conn.close()
    
    # 4. 输出
    if not output:
        out_dir = pathlib.Path(__file__).parent.parent / "ontology_models"
        out_dir.mkdir(exist_ok=True)
        output = out_dir / f"{proj_name}_ontology.ttl"
    
    g.serialize(str(output), format="turtle")
    print(f"本体已保存: {output}")
    print(f"  项目: {proj_name}")
    print(f"  类: 6, 属性: 7 (含传递性 dependsOn)")
    print(f"  文件: {len(list(g.triples((None, RDF.type, NS.File))))}")
    print(f"  三员组: {len(g)}")
    return g

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python cg_ontology_builder.py <项目路径> [输出路径]")
        print("示例: python cg_ontology_builder.py D:/open_claw_agent/A-supply-analysis")
        sys.exit(1)
    
    output = sys.argv[2] if len(sys.argv) > 2 else None
    build_ontology(sys.argv[1], output)
