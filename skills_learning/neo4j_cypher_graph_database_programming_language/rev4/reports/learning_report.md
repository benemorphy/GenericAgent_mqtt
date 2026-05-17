# 技能学习报告: neo4j_cypher_graph_database_programming_language

| 属性 | 值 |
|------|-----|
| 版本 | rev4 |
| 评分 | 100/100 PASS |
| 案例数 | 31 条 |
| 模式总数 | 15 个 |
| 继承自 rev3 | 13 个 |
| 新增 | 2 个 |

## 知识模式

### 领域专有 (11个)
- [95%] 基础语法与查询模式：掌握MATCH、RETURN、WHERE等核心子句，构建节点与关系的匹配模式
- [90%] 数据建模与模式设计：设计节点标签、关系类型和属性，优化图结构以支持高效查询
- [90%] 设计图模型时优先考虑查询模式：根据实际查询需求设计节点、关系和属性，而非先建模再适配查询。
- [90%] 为经常用于过滤、排序或聚合的属性创建索引，以加速查询执行。
- [88%] 在Cypher查询中优先使用参数化查询而非字面量，以利用查询计划缓存并防止注入。
- [85%] 高级查询与聚合：使用WITH、ORDER BY、聚合函数和子查询实现复杂数据分析和路径遍历
- [85%] 使用有意义的标签和关系类型名称，避免模糊或通用命名，以提升查询可读性和性能。
- [80%] 索引与性能优化：创建索引、使用PROFILE分析查询计划，优化Cypher执行效率
- [75%] 图算法与数据操作：应用最短路径、社区检测等图算法，以及CREATE、MERGE、DELETE等数据变更操作
- [70%] 使用丰富的数据模型（Rich Data Model）表达业务语义，增强图的表达能力和遍历效率。
- [65%] 在Cypher模式匹配中使用ASCII艺术风格表示节点和关系，确保模式清晰且与数据逻辑一致。

### 高级模式 (4个)
- [85%] 使用PROFILE或EXPLAIN分析查询执行计划，识别慢查询并优化模式匹配和过滤顺序。
- [80%] 在Spring Data Neo4j中，使用Repository模式封装Cypher查询，并通过AOP监控查询执行时间和频率以辅助优化。
- [78%] 将复杂查询拆分为模块化子查询，便于复用和维护，同时结合参数化查询和索引提升整体性能。
- [75%] 避免在Cypher中使用max()等聚合函数对无索引的大数据集操作，应预先创建索引或改用其他查询模式。

## 参考案例 (31条)

- giuseppe-trisciuoglio/developer-kit/spring-data-neo4j
- coding-agents-and-ides/people-strategy
- [Introduction](https://dev.to/mangesh28/neo4j-fundamentals-introduction-to-graph-databases-e78)
- [Cypher query language for Neo4j graph database](https://arghya.xyz/articles/neo4j-graph-database-2/)
- [Graph Database](https://siamcomputing.com/general/neo4j-graph-database/)
- [Neo4j Graph Data Modelling: Design efficient and flexible databases by optimizing the power of Neo4j Profile Icon](https://www.packtpub.com/product/neo4j-graph-data-modeling/9781784393441)
- [Neo4j Cypher 笔记](https://cloud.tencent.cn/developer/information/Neo4j%20Cypher%20-%E6%8C%89%E9%A1%BA%E5%BA%8F%E5%88%86%E5%88%AB%E8%8E%B7%E5%8F%96%E5%A4%9A%E4%B8%AA%E8%B7%AF%E5%BE%84%E4%B8%8A%E7%9A%84%E8%8A%82%E7%82%B9)
- [SQErzo](https://github.com/BBVA/sqerzo)
- [一种优化Cypher查询语言在图数据库中的执行性能的方法](https://cloud.tencent.com.cn/developer/information/%E5%9F%BA%E4%BA%8E%E6%80%A7%E8%83%BD-%E7%A4%BE%E4%BC%9A%E5%9B%BE%E7%9A%84Cypher%E6%9F%A5%E8%AF%A2%E4%BC%98%E5%8C%96)
- [Query tuning](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/query-tuning/)