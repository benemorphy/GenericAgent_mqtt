# 代码解耦改进：综合优先级排序

评估日期：2026-05-20
综合依据：docs/decoupling_risk_assessment.md（风险） + docs/decoupling_robustness_eval.md（鲁棒性收益）

## 优先级计算公式

```
优先级 = 鲁棒性收益得分 / 实施风险得分
        高收益 + 低风险 = 先做
        低收益 + 高风险 = 后做
```

## 最终排序

| 优先级 | # | 改进项 | 风险 | 鲁棒性收益 | 综合评分 |
|--------|---|--------|------|-----------|---------|
| **P1** | 5 | LLM Provider -> 工厂 ✅ | High | Most Significant | 高 |
| **P1** | 8 | mykey -> 配置服务 ✅ | High | Most Significant | 高 |
| **P2** | 9 | 全局记忆 -> 独立服务 | High | Moderate | 中 |
| **P4** | 13 | 日志系统 -> 统一 | High | Mixed/Caution | 最低（建议暂缓） |

## 执行批次

### 已完成

```
#1  Turn策略 -> Policy Hook     ga.py -> tools/hooks_default.py (3个policy hook函数+partial注册, 17行移出)
#4  系统提示注入 -> hook         ga.py -> tools/hooks_default.py (3个sph hook函数+partial注册, 22行移出)
#14 重试模式 -> 装饰器          llmcore.py -> tools/retry_utils.py (@retry_stream装饰器)
#3  工具函数 -> tools/utils      ga.py -> tools/ga_utils.py (6个工具函数: format_error/log_memory_access/expand_file_refs/scan_files/smart_format/consume_file)
#12 历史折叠 -> 工具库            ga.py -> tools/ga_utils.py (fold_earlier)
#7  历史压缩 -> 插件               llmcore.py -> tools/history_compressor.py (DefaultCompressor)
#10 WebDriver -> 惰性服务        ga.py -> tools/browser_service.py (BrowserService类 + 惰性初始化/优雅降级)
#2  Plan Mode -> 插件化           ga.py -> tools/plan_validator_default.py (验证器链+plan_limit_policy+utils, 3处策略完全提取)
#6  MQTT Worker -> 独立             agentmain.py -> mqtt_bbs/mqtt_agent_runner.py (MQTT wiring独立模块, 20行代码移出)
#11 斜杠命令 -> 插件              agentmain.py + frontends/ -> tools/slash_cmd_registry.py (注册式分发替换monkey-patch链)
#5  LLM Provider -> 工厂          llmcore.py -> tools/llm_providers/ (ProviderProtocol+ProviderRegistry+Claude/OpenAI SSE解析器, llmcore -189行, resolve_session→注册表)
#8  mykey -> 配置服务              mykey*.py -> tools/config_service.py + profiles/ (ConfigService单例+profile系统, 三阶段: 核心集成->消费者迁移->profile切换, 12文件变更)
```

---

### Batch 2: 核心隔离（ga.py剩余）

当前批次无待办项。#2 已完成，#10 已完成，无剩余。<br>
下一批请见 Batch 3。

#10 WebDriver -> 惰性服务 已完成后移出本批次。

---

### Batch 3: 独立子系统（llmcore.py + agentmain.py）

当前批次无待办项。#5 已完成。<br>
下一批请见 Batch 4。

---

### Batch 4: 高风险高收益

当前批次无待办项。#8 已完成。<br>
下一批请见 Batch 5。

---

### Batch 5: 可选（本期可选）

```
#9  全局记忆 -> 独立服务          高风险，中等收益
```

```
日志系统 -> 统一              高风险，收益不确定（print→logging语义差异可能降低可诊断性）
```

---

### Batch 6: 待分析

当前所有编号改进项已完成。如需进一步解耦，建议重新扫描代码库识别新的耦合点后更新本文档。

## 三份文档的关系

| 文档 | 回答的问题 |
|------|-----------|
| decoupling_analysis.md | 改什么？ |
| decoupling_risk_assessment.md | 怎么安全地改？ |
| decoupling_robustness_eval.md | 改了有什么好处？ |
| (本文件) | 先改哪个？顺序是什么？ |
