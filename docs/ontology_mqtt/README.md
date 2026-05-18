# MQTT BBS × 本体论 — 语义协作层架构

> 将 Palantir 本体论架构映射到 MQTT BBS 智能体协作系统
>
> 参考文章：[6000字搞懂Palantir本体论](https://mp.weixin.qq.com/s/wSIuhivUqGjCPjp158IzRg)
> 技能库：`skills_learning/ontology/rev4` (16个知识模式)

---

## 1. 核心思想

**本体 = 给大模型的行动手册**

大模型像刚毕业的博士生，缺乏业务经验。"本体"相当于一本行动手册——企业的私有数据和业务规则。大模型必须遵循行动手册行事，从而从"初级助手"变成"靠谱牛马"。

### MQTT BBS 的本体映射

| Palantir 本体论 | MQTT BBS 映射 | 实现方式 |
|:---------------:|:-------------:|:--------:|
| **对象 (Object)** | 实体主题节点 | `ontology/entities/{type}/{id}` |
| **属性 (Property)** | 消息 Payload Schema | JSON Schema 校验消息字段 |
| **关系 (Relationship)** | 主题树结构 + 链接字段 | 主题层级反映概念继承；消息内 `ref` 表达关联 |
| **行动 (Action)** | 指令主题 | `ontology/actions/{action_type}/request` |
| **函数 (Function)** | API 网关主题 | 复杂操作通过 MQTT→HTTP Bridge 调用后端 API |
| **记忆 (Memory)** | 历史主题 | `ontology/memory/history/{entity_id}` 存储全生命周期 |
| **模拟 (Simulation)** | 沙箱主题前缀 | `ontology/sandbox/` 隔离模拟环境 |

## 2. 三层架构

```
+------------------------------------------+
|           应用层 (Application)             |
|  飞书Bot  |  Web UI  |  CLI  |  API       |
+------------------------------------------+
|         语义协作层 (Ontology BBS)          |
|  +---------+  +---------+  +---------+   |
|  |概念定义   |  |实体管理   |  |规则引擎  |   |
|  |(OWL/RDF) |  |(实例)    |  |(约束)   |   |
|  +----+----+  +----+----+  +----+----+   |
|       +----------+-----------+            |
|                MQTT Broker                 |
+------------------------------------------+
|          数据层 (Data Sources)              |
|  Agent  |  API  |  DB  |  ERP  |  CRM     |
+------------------------------------------+
```

## 3. 主题树设计

```
ontology/
+-- meta/                      # 元数据层
|   +-- concepts/              # 概念定义 (Schema)
|   |   +-- aircraft           # 飞机概念定义
|   |   +-- airport            # 机场概念定义
|   |   +-- flight             # 航班概念定义
|   +-- relations/             # 关系定义
|       +-- assigned_to        # 分配关系
|       +-- located_at         # 位置关系
|       +-- maintained_by      # 维护关系
|
+-- entities/                  # 实体实例层
|   +-- aircraft/
|   |   +-- A001               # 飞机A001实例
|   |       +-- status         # 当前状态
|   |       +-- properties     # 属性
|   |       +-- relations      # 关联实体
|   +-- airport/ ...
|   +-- flight/ ...
|
+-- actions/                   # 行动层
|   +-- command/               # 指令发布
|   |   +-- repair             # 维修指令
|   |   +-- reassign           # 重新分配
|   |   +-- delay              # 延误处理
|   +-- event/                 # 事件通知
|       +-- fault_reported     # 故障上报
|       +-- repair_completed   # 维修完成
|
+-- memory/                    # 记忆层
|   +-- history/               # 执行历史
|   +-- patterns/              # 学习模式
|
+-- sandbox/                   # 沙箱层（模拟环境）
    +-- simulation/            # 模拟方案
    +-- prediction/            # 预测结果
```

## 4. 语义路由机制

**从"主题匹配"到"语义路由"**

当前 MQTT：
```
topic: agent/task/create
Agent 订阅 -> 收到所有"创建任务"消息
```

本体论升级后：
```
topic: ontology/actions/task/create
payload: {
  "object": {"type": "aircraft", "id": "A001"},
  "action": {"type": "repair", "priority": "high"},
  "context": {
    "source": "fault_detection_system",
    "timestamp": "2026-05-18T15:30:00Z",
    "relations": [
      {"type": "located_at", "target": "PEK"},
      {"type": "assigned_to", "target": "mro_team_3"}
    ]
  }
}

routing: 根据 object.type + action.type 路由
- object.type=aircraft -> mro_agent
- action.type=repair    -> maintenance_scheduler
```

## 5. "0幻觉"机制

借鉴 Palantir 的实现：

```
+----------+    指令(方案)     +------------+
|  大模型   | ---------------> | Palantir   |
| (DeepSeek)|                  | (本体+规则)  |
|  "换飞机" |  <--------------- | 校验+执行   |
+----------+  校验结果         +------+------+
                                      |
                                      v
                               MQTT Broker
                            (ontology/actions/
                             command/reassign)
                                      |
                                      v
                              ERP/CRM 等源系统
```

**原则**：
1. 大模型只能**基于本体数据**给出方案（不能编造）
2. 大模型只能给出**指令**，由本体层校验并执行
3. 大模型**不参与具体执行**，大大降低幻觉风险

## 6. 已有基础

| 组件 | 状态 | 备注 |
|------|:----:|------|
| MQTT Broker (RMQTT) | :white_check_mark: | `D:\tools\rmqtt-0.20.0` |
| MQTT BBS 机制 | :large_orange_diamond: 已有 | `tools/bbs*.py` |
| 飞书Bot | :white_check_mark: 运行中 | `frontends/fsapp.py` |
| 本体论技能库 | :white_check_mark: rev4 (16模式) | `skills_learning/ontology/rev4` |
| OCR (RapidOCR) | :white_check_mark: | 可处理图像类事实 |
| LLM (DeepSeek) | :white_check_mark: | `native_oai_config` |

## 7. 参考案例：飞机故障

> 来自 Palantir 本体论文章

1. **事件**：A001 飞机出现机械故障，预计维修 2 小时
2. **本体查询**：AI 调取 A001 的对象信息（型号、机龄、航线）、关系网络（当前机场、机组、候选飞机）
3. **方案推演**：方案A-替换飞机 vs 方案B-延误航班
4. **模型预测**：调用预测模型评估投诉率、成本、连环延误概率
5. **决策执行**：AI 提交申请 -> Palantir 校验权限 -> 执行 -> 结果回写
6. **闭环**：记忆记录，下次类似场景可参考

---

*文档版本: v1.0 | 创建日期: 2026-05-18*
*来源: 微信文章 + skills_learning/ontology/rev4 + inspiration#7*
