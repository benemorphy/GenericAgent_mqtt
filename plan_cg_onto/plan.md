# CG-OWL Bridge 实施计划

## Step 1: MCP Serve 启动
- [x] codegraph init -i 索引 (211 files, 4709 nodes, 8930 edges)
- [ ] codegraph serve --mcp (Node.js runtime, 需在独立终端手动启动)

## Step 2: 本体增强
- [x] _build_final_ontology.py 全部6种 edge kinds
- [x] OWL 推理器 (RDFLib transitive property)
- [x] 输出: ontology_full.ttl (1906 triples)

## Step 3: 自动同步管线
- [x] scripts/cg_ontology_sync.py 构建脚本
- [x] 增量更新 OWL 三元组

## Step 4: SPARQL 验证
- [x] scripts/sparql_verify.py 验证脚本
- [x] 5 类查询通过: imports/calls/module count/node distribution/dependsOn

## Step 5: MCP 集成
- [x] 文档说明 MCP 启动方式
- [ ] codegraph serve --mcp (需手动启动)

## Step 6: 文档更新 ✅
- [x] SOP 已推送到 Sophub (id: 6a25d003bb8b27ff96341454)
- [x] 项目文档已更新
