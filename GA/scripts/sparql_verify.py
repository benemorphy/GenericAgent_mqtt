"""Step 4: SPARQL 查询验证"""
from rdflib import Graph
g = Graph()
g.parse("D:/open_claw_agent/Beneh/GA/ontology_full.ttl", format="turtle")

print("=== SPARQL 验证结果 ===")

q1 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?a ?b WHERE { ?a ont:imports ?b . } LIMIT 5
""")
print(f"1. imports 关系: {len(q1)} 条")
for r in list(q1)[:3]:
    print(f"   {str(r.a).split('/')[-1][:30]} -> {str(r.b).split('/')[-1][:30]}")

q2 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?a ?b WHERE { ?a ont:calls ?b . } LIMIT 5
""")
print(f"2. calls 关系: {len(q2)} 条")

q3 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT (COUNT(?m) AS ?cnt) WHERE { ?m rdf:type ont:Module . }
""")
for r in q3: print(f"3. 模块数: {r.cnt}")

q4 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?kind (COUNT(?s) AS ?cnt) WHERE {
        ?s rdf:type ?kind .
        FILTER(?kind != <http://www.w3.org/2002/07/owl#Thing>)
    } GROUP BY ?kind
""")
print("4. 各类节点分布:")
for r in q4:
    print(f"   {str(r.kind).split('/')[-1]}: {r.cnt}")

# 风险传导传递性推理
q5 = g.query("""
    PREFIX ont: <http://beneh.ga/ontology/>
    SELECT ?a ?c WHERE { ?a ont:dependsOn ?c . } LIMIT 10
""")
print(f"5. dependsOn (传递性): {len(q5)} 条")
