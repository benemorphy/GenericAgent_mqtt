---
skill: ontology_compress_strategy
domain: ontology + routing
version: "1.0"
tags: [ontology, compress, p0, strategy, integration]
cc_quick: "本体模型与上下文压缩(P0)交叉集成方案 — 3阶段实现，本体类型索引压缩粒度"
cc_keywords: ["本体", "P0压缩", "controller.py", "交叉策略"]
---

# 本体模型与上下文压缩(P0)交叉集成方案

## 背景
- 本体模型: `GA/ontology_models/A-supply-analysis_ontology.ttl` (Turtle格式, 141行)
  - 核心类: Function, Module, Route, Variable, Class
  - 关系: calls, contains, dependsOn, imports
- 上下文压缩: `GA/squilla_router/controller.py`
  - P0: 压缩（缩短思考）
  - P1: 正常
  - P2: 详细
  - 当前仅基于 difficulty + margin + flags 做决策

## 3阶段方案

### A阶段: 本体类型索引P0粒度
文件: `GA/squilla_router/controller.py`
新增 `_ONTOLOGY_COMPRESS_MAP`:
```
function → P0    # 函数级→一句话概括
variable → P0    # 变量级→省略
module   → P1    # 模块级→保留接口细节
route    → P1    # 路由级→保留路径参数
class    → P2    # 类级→保留完整结构
project  → P2    # 项目级→不压缩
```

同时增加 `_COMPRESS_BLOCK_ONT_DEPTH = 2`，调用链深度 > 2 时强制不压缩。

### B阶段: P0 hint注入本体元信息
文件: `GA/squilla_router/controller.py`
当前: `"Answer directly, keep thinking short."`
增强: `"Topic scope: {scope} ({dep_count} related entities). Keep thinking short."`

### C阶段: 本体查询接口
新文件: `GA/tools/ontology_query.py`
提供 `get_ont_type(topic)` 和 `get_ont_depth(topic)` 接口，
给 router 提供当前 topic 的本体类型和依赖深度。

## 文件位置
- 本方案: `memory/ontology_compress_strategy.md`
- 待改文件: `GA/squilla_router/controller.py`
- 新增文件: `GA/tools/ontology_query.py`
