---
skill: codegraph_ontology_bridge
domain: code-analysis
version: "1.0"
tags: [codegraph, ontology, owl, code-analysis, integration]
cc_quick: "CodeGraph + OWL Ontology 双向映射 — 代码图与语义推理融合"
---

# CodeGraph + OWL Ontology Bridge SOP

将 CodeGraph 的代码级图分析与 OWL 本体推理双向映射，使 Agent 能同时理解代码结构和领域语义。

## Prerequisites

```bash
# CodeGraph installed
npm install -g @codegraph/cli    # or: cargo install codegraph-cli

# Python packages
pip install rdflib requests
```

## Step 1: Initialize CodeGraph Index

```python
import subprocess, json

# In project root
result = subprocess.run(["codegraph", "init", "-i", "."], 
    capture_output=True, text=True, timeout=60)
print(result.stdout)

# Verify index
result = subprocess.run(["codegraph", "status", "."],
    capture_output=True, text=True)
print(result.stdout)
```

Expected output:
```
Indexed N files
NN nodes, NN edges
```

## Step 2: Build OWL Ontology from CodeGraph Data

```python
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL
import subprocess, json

NS = Namespace("http://your-domain/ontology/")
g = Graph()
g.bind("ont", NS)

# 1. Define classes
g.add((NS.CodeComponent, RDF.type, OWL.Class))
g.add((NS.Function, RDF.type, OWL.Class))
g.add((NS.Module, RDF.type, OWL.Class))

# 2. Define properties
g.add((NS.imports, RDF.type, OWL.ObjectProperty))
g.add((NS.calls, RDF.type, OWL.ObjectProperty))
g.add((NS.dependsOn, RDF.type, OWL.ObjectProperty))

# 3. Import CodeGraph data
# Query functions
funcs = subprocess.run(["codegraph", "query", "--kind", "function", "."],
    capture_output=True, text=True)
for line in funcs.stdout.splitlines():
    if line.strip():
        # Create OWL individual
        g.add((NS[line.strip()], RDF.type, NS.Function))

# Query imports/calls
# ... use codegraph callers/callees to build edges

# Save
g.serialize("ontology/combined.ttl", format="turtle")
print(f"Ontology saved: {len(g)} triples")
```

## Step 3: Run OWL Reasoning

```python
from rdflib import Graph

g = Graph()
g.parse("ontology/combined.ttl", format="turtle")

# Define reasoning rules
# Rule: if A imports B and B imports C, then A dependsOn C
g.add((NS.dependsOn, RDF.type, OWL.TransitiveProperty))

# Run reasoner (using RDFLib's built-in inference)
from rdflib.plugins.sparql import prepareQuery
q = prepareQuery("""
    PREFIX ont: <http://your-domain/ontology/>
    SELECT ?a ?c WHERE {
        ?a ont:imports ?b .
        ?b ont:imports ?c .
    }
""")

# Infer transitive dependencies
for row in g.query(q):
    g.add((row.a, NS.dependsOn, row.c))

g.serialize("ontology/inferred.ttl", format="turtle")
print(f"Inferred: {len(g)} triples")
```

## Step 4: CodeGraph MCP + OWL Query

```bash
# Start CodeGraph MCP server
codegraph serve --mcp --path .
```

Then from GA:
```python
# Use CodeGraph tools via MCP
from codegraph_mcp import CodeGraphClient
cg = CodeGraphClient()

# Query code structure
callers = cg.get_callers("calculate_risk")
print(f"Callers: {callers}")

# Query ontology
from rdflib import Graph
g = Graph()
g.parse("ontology/inferred.ttl")
q = """
    PREFIX ont: <http://your-domain/ontology/>
    SELECT ?comp ?dep WHERE {
        ?comp ont:dependsOn ?dep .
    }
"""
for row in g.query(q):
    print(f"{row.comp} depends on {row.dep}")
```

## Step 5: Impact Analysis with Ontology

When code changes, trace impact through both graphs:

```python
import subprocess, json

# Step 5a: CodeGraph impact analysis
result = subprocess.run(
    ["codegraph", "impact", "--since", "HEAD~1", "--format", "json", "."],
    capture_output=True, text=True
)
affected = json.loads(result.stdout)
print(f"Code affected: {len(affected)} files")

# Step 5b: Map to ontology
from rdflib import Graph, URIRef
g = Graph()
g.parse("ontology/inferred.ttl")

for file in affected:
    comp = URIRef(f"http://your-domain/ontology/{file}")
    # Query what depends on this
    q = f"""
        PREFIX ont: <http://your-domain/ontology/>
        SELECT ?dependent WHERE {{
            ?dependent ont:dependsOn <{comp}> .
        }}
    """
    for row in g.query(q):
        print(f"Change to {file} affects: {row.dependent}")
```

## Universal Application

This SOP is **domain-agnostic**. Apply it to:

| Scenario | CodeGraph Role | Ontology Role |
|----------|---------------|---------------|
| Supply chain | Import graph → supply chain topology | Company/relation model → risk inference |
| microservice architecture | Call graph → service dependencies | Service/API model → impact analysis |
| Code review | Symbol search → affected functions | Bug/pattern ontology → automated review |
| Migration planning | Dependency graph → migration order | Compatibility model → breaking change detection |

## Verification Checklist

- [ ] CodeGraph index built (verify with `codegraph status`)
- [ ] OWL ontology has all classes defined
- [ ] Import/call graph → OWL properties mapped
- [ ] Reasoner runs without errors
- [ ] MCP server responds to queries
- [ ] Impact analysis produces actionable results

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `codegraph: command not found` | Install via `npm i -g @codegraph/cli` |
| RDFLib reasoner too slow | Limit triples or use SPARQL queries instead |
| MCP connection refused | Ensure `codegraph serve --mcp` is running |
