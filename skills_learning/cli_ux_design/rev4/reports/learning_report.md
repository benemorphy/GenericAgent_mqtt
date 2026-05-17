# 技能学习报告: cli_ux_design

| 属性 | 值 |
|------|-----|
| 版本 | rev4 |
| 评分 | 86/100 PASS |
| 案例数 | 10 条 |
| 模式总数 | 13 个 |
| 继承自 rev3 | 12 个 |
| 新增 | 1 个 |

## 知识模式

### 领域专有 (12个)
- [95%] Command-line interface (CLI) design principles (核心设计原则，如一致性、可发现性、渐进式披露)
- [92%] CLI argument parsing and help system (参数解析与帮助系统设计，如子命令、标志、自动补全、man页面)
- [90%] Error message design for CLI (错误信息设计，包括清晰性、可操作性、上下文提示)
- [90%] CLI 错误消息应输出到标准错误流（stderr），而非标准输出流（stdout），以便用户和脚本区分正常输出与错误信息。
- [90%] CLI 应提供一致的命令语法结构，例如统一使用短选项（如 -v）和长选项（如 --verbose），并支持 --help 或 -h 查看帮助。
- [88%] CLI output formatting and readability (输出格式化与可读性，如颜色、表格、进度条、对齐)
- [85%] CLI user experience testing and iteration (用户体验测试与迭代，如用户研究、A/B测试、可访问性)
- [85%] CLI 设计应遵循单一职责原则，每个命令或子命令聚焦于一个明确的功能，避免过度复杂或功能混杂。
- [85%] CLI 错误消息应清晰描述问题原因、影响及可能的修复步骤，避免模糊或技术性过强的表述，以降低用户学习曲线。
- [85%] CLI 设计应优先考虑可脚本化，确保所有交互操作均可通过命令行参数或标准输入完成，无需人工干预。
- [80%] CLI 工具应支持静默模式（如 --quiet）和详细模式（如 --verbose），以适应不同用户场景（脚本自动化 vs 交互调试）。
- [80%] CLI 应提供合理的默认值，减少用户必须指定的参数数量，同时允许高级用户通过配置文件或环境变量覆盖默认行为。

### 高级模式 (1个)
- [75%] CLI 输出应结构化且易于解析，例如支持 JSON 或表格格式输出，便于其他工具或脚本处理结果。

## 参考案例 (10条)

- [Codex (AI agent)](https://en.wikipedia.org/wiki/Codex_%28AI_agent%29)
- [List of CLI languages](https://en.wikipedia.org/wiki/List_of_CLI_languages)
- [Command-line interface](https://en.wikipedia.org/wiki/Command-line_interface)
- [C++/CLI](https://en.wikipedia.org/wiki/C%2B%2B/CLI)
- [Climate fiction](https://en.wikipedia.org/wiki/Climate_fiction)
- [ProFTPD](https://en.wikipedia.org/wiki/ProFTPD)
- [Single UNIX Specification](https://en.wikipedia.org/wiki/Single_UNIX_Specification)
- [Error message](https://en.wikipedia.org/wiki/Error_message)
- [Open Database Connectivity](https://en.wikipedia.org/wiki/Open_Database_Connectivity)
- [Graphical user interface](https://en.wikipedia.org/wiki/Graphical_user_interface)