---
skill: context_compression
domain: agent-core
version: "1.0"
tags: [compression, context, token, optimization]
cc_quick: "上下文压缩管线 — DynamicTrigger→LevelSummary→SemanticTrim→CompressTag"
cc_keywords: ["压缩", "上下文", "token优化", "摘要"]
---

# 上下文压缩 SOP

## 管线架构

```
messages → Stage1(DynamicTrigger) → Stage2(LevelSummary) → Stage3(SemanticTrim) → Stage4(CompressTag) → 输出
```

## Stage1: DynamicTrigger
- 阈值触发（取代固定5轮间隔）
- token估测 > 8K 或 turn > 30 或 上次压缩后新增 > 20轮 时触发

## Stage2: LevelSummary（层级摘要）
- L0: 全量原文（不压缩）
- L1: 最近10轮保留 + 旧轮摘要化为 `[Summary: ...]`
- L2: 全部摘要化（极端情况）
- 按token水位自动降级

## Stage3: SemanticTrim
- 保留工具调用结果中的关键数据（数字、路径、决策）
- 裁剪冗余的中间推理步骤

## Stage4: CompressTag
- 压缩后插入标记消息 `[Context compressed: N turns → 1 summary, ~X% reduction]`
- Agent可感知上下文被压缩过

## 接口
所有compressor继承 CompressorBase，通过 CompressionPipeline 串联。
