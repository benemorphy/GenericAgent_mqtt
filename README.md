# GenericAgent (GA)

基于 MQTT 通信的多 Agent 基础设施，含 BBS 看板服务、飞书机器人集成、自主运行能力，以及 **人机协作决策模式（Goal Nexus）**。

## 快速开始

```bash
pip install -r requirements.txt

# 配置环境变量（复制并填写）
cp .env.example .env

# 运行 agent
python agentmain.py --task "你的任务描述"
```

## 核心架构

- **agentmain.py**: 主入口（CLI + agent 循环）
- **ga.py**: GeneraticAgentHandler — 核心 Agent 逻辑
- **llmcore.py**: LLM Provider 抽象层（Claude, OpenAI, DeepSeek）
- **tools/**: 工具定义、MCP 封装、工具函数、安全、日志
- **agents/**: 多 Agent 编排（langgraph）
- **frontends/**: 用户界面桥接层（FastAPI Web UI 8001, 飞书, Telegram, QQ, 微信）
- **Mqtt_bbs_server/**: MQTT BBS 看板服务（分布式 Agent 协调）
- **reflect/**: 反射循环模块 — 自主执行模式，含 MQTT 脉冲/编年史
  - `goal_mode.py` — Goal Mode: 持续自驱执行直到预算耗尽
  - `goal_bbs.py` — Goal Pulse + Chronicle: 通过 MQTT BBS 实时广播状态
  - `goal_nexus.py` — Goal Nexus: 人机协作决策模式
  - `goal_prism.py` — Goal Prism: 复杂决策的多视角分析
  - `goal_sentinel.py` — Goal Sentinel: 监控守卫循环
- **memory/**: SOP 文档和知识库

## 配置

复制 `.env.example` 为 `.env` 并配置：

| 变量 | 说明 | 必填 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 | 是（或 LLM_API_KEY）|
| `MQTT_HOST` | MQTT Broker 地址 | 是（默认 127.0.0.1）|
| `JWT_SECRET` | 64 位随机密钥用于认证 | 是（生产环境）|
| `GITHUB_TOKEN` | GitHub 个人访问令牌 | Git 操作 |

## 项目结构

```
├── agentmain.py              # 主入口（CLI / reflect / MQTT）
├── ga.py                     # GeneraticAgent — 核心 Agent 循环
├── llmcore.py                # LLM Provider 抽象层
├── reflect/                  # 反射循环模块
│   ├── goal_mode.py          #   Goal Mode: 持续自驱执行
│   ├── goal_nexus.py         #   Goal Nexus: 人机协作（飞书卡片）
│   ├── goal_prism.py         #   Goal Prism: 多视角分析
│   ├── goal_sentinel.py      #   Goal Sentinel: 监控守卫
│   ├── goal_bbs.py           #   Goal Pulse + Chronicle (MQTT BBS)
│   ├── autonomous.py         #   自主运行模式
│   └── scheduler.py          #   定时任务执行器
├── frontends/                # 用户界面桥接层
│   ├── web_ui/               #   FastAPI Web 管理面板 (port 8001)
│   │   └── main.py           #   入口: `-m frontends.web_ui.main`
│   ├── fsapp.py              #   飞书机器人（消息 + 交互卡片）
│   ├── tgapp.py              #   Telegram 机器人
│   ├── qqapp.py              #   QQ 机器人
│   └── stapp.py              #   Streamlit 界面
├── tools/                    # 工具定义和 MCP 封装
│   ├── mcp/                  #   MCP 工具封装
│   │   ├── gbrain_mcp.py     #   gbrain 本地知识库检索 (CLI 封装)
│   │   ├── codegraph_mcp.py  #   CodeGraph 代码分析
│   │   └── browser_service.py#   浏览器自动化
│   ├── skills/               #   技能注册
│   ├── utils/                #   工具函数
│   └── ...                   #   其他模块
├── memory/                   # SOP、知识库、操作指南
├── tests/                    # 测试套件
├── scripts/                  # 工具脚本（git push 等）
└── Mqtt_bbs_server/          # MQTT BBS 看板服务
    └── start_all.ps1         # 全服务启动脚本
```

## 第三方知识集成

### gbrain — 本地知识脑

GA 通过 `tools/mcp/gbrain_mcp.py` 集成 [gbrain](https://github.com/garrytan/gbrain) 本地知识库引擎，支持：

- **知识导入**：Markdown 目录批量导入，自动向量化嵌入
- **混合检索**：`gbrain_query` / `gbrain_search` — 语义 + 关键词混合搜索
- **推理问答**：`gbrain_think` — 基于知识库的链式推理
- **知识管理**：`gbrain_get_page` / `gbrain_list_pages` / `gbrain_status`

知识库位置：`C:\Users\<user>\.gbrain\brain.pglite` (PGLite 嵌入式数据库)

### miniload_kg — 小微金融贷款风控知识库

位于 `D:\open_claw_agent\miniload_kg\`，覆盖两个知识维度：

| 维度 | 内容 | 文档数 |
|------|------|--------|
| 风控理论 | 风险分类、评分卡、IPC技术、供应链金融、监管政策 | 9 |
| 项目实践 | 方付通项目：模型实践、欺诈检测、IPC风控、行业财务、复核审批SOP、审计标准、图像审核智能体、利率模型 | 12 |

已导入 gbrain，可通过 `gbrain_query("/查询内容/")` 直接检索。

## Docker 运行

```bash
docker build -t genericagent:latest .
docker run --env-file .env genericagent:latest
```

## Goal Nexus（人机协作）

Goal Nexus 在 Goal Mode 基础上增加了**人机协作决策机制**：

```bash
# 创建带决策点的状态文件
echo '{"objective":"审计代码质量","budget_seconds":1800,"decision_points":["架构评审","安全审计"]}' > temp/goal_state.json
set GOAL_STATE=temp\goal_state.json

# 启动 Goal Nexus 模式
python agentmain.py --reflect reflect/goal_nexus.py
```

**全链路流程**:
Agent 遇到决策点 -> 回复中写入 `[ASK_HUMAN]` 标记 -> fsapp.py 推送带按钮的飞书交互卡片 -> 人类点击选项 -> 回调流经 MQTT 回到 Agent -> Agent 继续执行

## 测试

```bash
pytest tests/ -v
```

## 文档

详见 `docs/` 设计文档和 `memory/` 的 SOP 及操作指南。
