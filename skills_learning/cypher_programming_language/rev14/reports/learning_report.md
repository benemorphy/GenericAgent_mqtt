# 技能学习报告: cypher_programming_language

| 属性 | 值 |
|------|-----|
| 版本 | rev14 |
| 评分 | 94/100 PASS |
| 案例数 | 29 条 |
| 模式总数 | 24 个 |
| 继承自 rev13 | 23 个 |
| 新增 | 1 个 |

## 知识模式

### 领域专有 (10个)
- [95%] Cypher 查询基础与图模式匹配
- [95%] 在MATCH子句中始终明确指定关系类型和方向，避免无关系条件的模式导致笛卡尔积，防止中间结果集爆炸。
- [90%] 数据建模与节点关系设计
- [90%] 为频繁查询的节点属性创建索引，以加速节点查找和匹配操作。
- [85%] 高级查询：聚合、路径遍历与子查询
- [85%] 仅使用图数据库中已定义的节点类型、关系类型和属性，不引入未在模式中声明的元素。
- [83%] Cypher查询语言核心语法与模式匹配（cypher_programming_l）
- [80%] 索引、约束与查询性能优化
- [75%] Cypher 与 Neo4j 集成：事务管理与程序化查询
- [75%] 根据数据集大小和工作负载复杂度选择简单直接的查询模式，避免过度复杂的嵌套子查询。

### 高级模式 (10个)
- [93%] 使用Cypher查询语言进行图模式匹配与关联分析
- [92%] 设计合理的节点标签与关系类型优化遍历性能
- [91%] 利用图索引提升Cypher查询性能
- [89%] 使用图算法进行路径分析、社区发现与推荐
- [88%] 采用APOC标准库扩展Neo4j功能
- [87%] 优化Cypher查询计划（PROFILE/EXPLAIN）
- [86%] 使用事务管理批量写入确保数据一致性
- [85%] 在生成Cypher语句时，严格遵循提供的模式过滤规则，不使用未在模式中列出的关系类型或属性。
- [80%] 优化查询模式，减少不必要的UNWIND、OPTIONAL MATCH和聚合操作，以降低计算开销。
- [70%] 使用参数化查询代替字符串拼接，以提高查询安全性和执行计划复用效率。

### 基础模式 (4个)
- [84%] 固定版本号避免意外升级
- [83%] 部署前验证配置文件正确性
- [79%] 使用环境变量/配置文件分离环境差异
- [75%] 资源限制防止单服务耗尽

## 参考案例 (29条)

- [openCypher query best practices](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/best-practices-content.html)
- [Things You Didn’t Know About Cypher Query Language](https://www.tigergraph.com/glossary/cypher-query-language/#%3A~%3Atext%3DIn%20addition%20to%20its%20GSQL%2Ccompared%20to%20traditional%20Cypher%20implementations.)
- [Dify与Neo4j集成实战：图数据库查询性能优化深度指南](https://www.cnblogs.com/ycfenxi/p/19866473)
- [Using Query Best Practices](https://neo4j.com/graphacademy/training-best-practices-40/03-best-practices40-using-query-best-practices/)
- [Deployment best practices](https://memgraph.com/docs/deployment/best-practices)
- [Graph Query Languages](https://graph.build/resources/graph-query-languages)
- [Question-to-Cypher Query Research: A Novel Model for Graph Database Interaction](https://www.mdpi.com/2076-3417/14/17/7881)
- [Notifications](https://github.com/langchain-ai/langchain/discussions/17716)
- [Enhancing Text2Cypher with Schema Filtering](https://arxiv.org/html/2505.05118v1)
- [GraphCypherQAChain how are schema and question instantiated under the hood · langchain-ai/langchain · Discussion #23663](https://github.com/langchain-ai/langchain/discussions/23663)