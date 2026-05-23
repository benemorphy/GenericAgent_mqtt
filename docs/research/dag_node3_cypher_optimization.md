# DAG 节点3: Cypher环查询优化

## 核心优化策略

| 策略 | 实施 | 效果 |
|:-----|:-----|:-----|
| 限定深度 | [:*1..10] | 避免指数爆炸 |
| 提前终止 | RETURN true | 发现即停止 |
| 锚定节点 | 最小度节点开始MATCH | 减少搜索空间 |
| GDS库 | 原生SCC算法 | 亿级节点可用 |

## 本项目适用

```cypher
MATCH (a:Order {if_hidden_net:true})
WHERE (a)-[:REFUND*2..5]->(a)
RETURN a.order_id, length(path) AS hops
LIMIT 100
```

## 与GNN对比

| 方式 | 场景 | 复杂度 |
|:-----|:------|:-------|
| Cypher环查 | 已知结构小规模 | O(k^n)剪枝 |
| GNN评分 | 未知模式大规模 | O(V+E) |
| GDS SCC | 全局离线 | O(V+E) |
