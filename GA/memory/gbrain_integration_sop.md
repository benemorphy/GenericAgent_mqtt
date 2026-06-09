# GA 集成 gbrain SOP

## 概述

gbrain (garrytan/gbrain) 是一个基于 bun/TypeScript 的本地知识大脑，提供知识检索、链式推理与知识图谱能力。GA Agent 通过 MCP 层 + Skill 层双层架构集成 gbrain。

## 架构

```
GA Agent
   |
   v
tools/skills/gbrain_skill.py  ← 4个 @TOOL.register() 技能
   |
   v
tools/mcp/gbrain_mcp.py       ← 10个 MCP 封装函数 (subprocess调用gbrain CLI)
   |
   v
gbrain CLI (bun run src/cli.ts)  ← 需预先 clone 到 GBRAIN_REPO
   |
   v
DeepSeek API (DEEPSEEK_API_KEY)  ← 通过 keychain 注入
```

## 前提条件

1. **bun 已安装**: 默认路径 `C:\Users\user\AppData\Roaming\npm\bun.CMD`，可覆盖 `BUN_PATH` 环境变量
2. **gbrain 仓库已 clone**: 默认路径 `D:/open_claw_agent/gbrain`，可覆盖 `GBRAIN_REPO` 变量
3. **DeepSeek API Key**: 需在 keychain 中配置 `deepseek_api_key`

## MCP 层 (tools/mcp/gbrain_mcp.py)

### 暴露的 10 个工具函数

| 函数 | 说明 | CLI 命令 |
|---|---|---|
| `gbrain_query(question, sources)` | 向 gbrain 提问，返回搜索结果 | `bun run src/cli.ts query <q> --json` |
| `gbrain_search(query, limit=10)` | 搜索知识库 | `bun run src/cli.ts search <q> --json --limit N` |
| `gbrain_think(prompt)` | 深度链式推理 | `bun run src/cli.ts think <prompt> --json` |
| `gbrain_graph_query(slug, depth=2)` | 知识图谱遍历 | `bun run src/cli.ts graph-query <slug> --depth N --json` |
| `gbrain_get_page(slug)` | 获取页面内容 | `bun run src/cli.ts get <slug>` |
| `gbrain_put_page(slug, content, type)` | 创建/更新页面 | `bun run src/cli.ts put <slug> --type <type> --content <file>` |
| `gbrain_list_pages()` | 列出所有页面 | `bun run src/cli.ts list` |
| `gbrain_list_skills()` | 列出所有技能 | `bun run src/cli.ts list-skills` |
| `gbrain_init()` | 初始化大脑 | `bun run src/cli.ts init --json` |
| `gbrain_status()` | 查看状态 | `bun run src/cli.ts status --json` |

### 核心依赖

- `from memory.keychain import keys` → `keys.deepseek_api_key.use()` 获取 API Key
- 环境变量注入：`DEEPSEEK_API_KEY` 传入 gbrain CLI 子进程

### 输出解析器

内置 3 个解析器处理 gbrain CLI 的非 JSON 输出：
- `_parse_search_query_output()` — 解析 `[score] slug -- title` 格式
- `_parse_get_output()` — 解析 YAML frontmatter + content
- `_parse_list_output()` — 解析 TSV 表格

## Skill 层 (tools/skills/gbrain_skill.py)

### 向 Agent 注册的 4 个工具

| 工具名 | 封装的 MCP 函数 | 用途 |
|---|---|---|
| `gbrain_query_agent(query)` | `gbrain_query()` | 向知识库提问，返回合成答案（含引用） |
| `gbrain_search_agent(query, limit=5)` | `gbrain_search()` | 关键词搜索，返回结果列表 |
| `gbrain_think_agent(prompt)` | `gbrain_think()` | 深度链式推理分析 |
| `gbrain_graph_agent(slug, depth=2)` | `gbrain_graph_query()` | 查询知识图谱实体关系 |

### 注册方式

```python
from tools.agent.registry import TOOL

@TOOL.register()
def gbrain_query_agent(query: str) -> str:
    """文档字符串即 Agent 看到的工具描述"""
    ...
```

## 调用流程

1. Agent 决策 → 调用注册的工具名（如 `gbrain_query_agent`）
2. Skill 层 → 参数校验 + 异常包装 → 调用 MCP 层函数
3. MCP 层 → 构建 CLI 命令 → subprocess.run → 解析输出
4. 结果返回 Agent 供继续推理

## 常见问题

- **gbrain 仓库不存在**: 检查 `GBRAIN_REPO` 路径配置
- **CLI 返回非零退出码**: 检查 bun 安装和 gbrain 依赖
- **API Key 无效**: 重新配置 keychain 中的 `deepseek_api_key`
- **think 超时**: 默认 120s 超时，复杂推理可适当增加

## 相关文件

- `tools/mcp/gbrain_mcp.py` — MCP 层实现
- `tools/skills/gbrain_skill.py` — Skill 层注册
- `memory/keychain.py` — API Key 管理
