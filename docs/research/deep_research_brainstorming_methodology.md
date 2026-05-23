# Deep Research: Brainstorming 方法论 — 从人类实践到Agent实现

> 来源: Google (Asana/Mural/Leadership IQ/Scribd/NIH/SixSigma/IDEO U)
> 方法论: Sophub DeepResearch SOP

---

## 1. 核心方法论对比

| 方法 | 核心机制 | 适用场景 | 关键实践 |
|:-----|:---------|:---------|:---------|
| **Round Robin** | 轮流发言,每人每次只贡献一个想法 | 团队中有主导人格时 | 3-5min/轮,沉默先行思考 |
| **Nominal Group (NGT)** | 静默写→轮流分享→澄清→投票 | 需要量化优先级 | 四个阶段严格分离 |
| **Delphi 法** | 匿名问卷→汇总→再问卷→收敛 | 专家共识,避免权威影响 | 多轮匿名,统计收敛 |
| **Brainwriting / 635** | 6人×3idea×5轮,传阅扩展 | 大量想法快速生成 | 轮次+人数固定 |
| **Devil's Advocate** | 设一个"反对者"角色专门质疑 | 避免群体思维(Groupthink) | 每次换人当 |

## 2. 避免群体思维 (Groupthink)

| 问题 | 现象 | 解法 |
|:-----|:-----|:-----|
| 权威压制 | 领头人先说→后面不敢反对 | 匿名提交、静默先行 |
| 和谐至上 | 怕破坏气氛不质疑 | 设Devil's Advocate |
| 早熟评估 | 边想边评价→扼杀创意 | 分离生成与评价阶段 |
| 信息漏斗 | 只有大声的人被听到 | Round Robin强制轮流 |

## 3. Round Robin 标准流程 (最适合Agent实现)

```
第1轮(静默):
  每个参与者独立写下1个想法,不交流

第2轮(轮流):
  按顺序每人分享1个→传给下一个人扩展

第3轮(迭代):
  每人看到别人的想法后,提出改进/反驳/补充

第4轮(投票):
  所有想法→澄清→打分→排序
```

## 4. 对当前 brain_swarm.py 的启发

| 当前实现 | 缺少 | 应仿照 |
|:---------|:------|:-------|
| Agent独立产出,不交流 | **轮流对话** | Round Robin |
| 无轮次概念 | **迭代修正** | Delphi匿名迭代 |
| 硬编码Cross Points | **真正的批判性反驳** | Devil's Advocate |
| 一轮结束 | **多轮收敛** | Delphi多轮 |

## 5. 改进方向

```
Agent Brainstorm 2.0 (基于Round Robin + Delphi):

第1轮: n个Agent独立产出(已实现)
第2轮: Agent2看到Agent1的产出→补充/反驳
第3轮: Agent3看到Agent1+2→综合
...
第N轮: 收敛投票
```

---

> 参考文献: Asana Round Robin Guide 2024 / NIH NGT+Delphi 2016 / Leadership IQ Brainstorming Science 2025 / IDEO U Rules