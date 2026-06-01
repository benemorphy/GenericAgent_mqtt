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
- **tools/**: 工具定义、工具函数、安全、日志
- **agents/**: 多 Agent 编排（langgraph）
- **frontends/**: 用户界面（Streamlit, TUI, Tauri 桌面端, Telegram, QQ, 微信, 飞书）
- **Mqtt_bbs_server/**: MQTT BBS 看板服务（分布式 Agent 协调）
- **reflect/**: 反射循环模块 — 自主执行模式，含 MQTT 脉冲/编年史
  - `goal_mode.py` — Goal Mode: 持续自驱执行直到预算耗尽
  - `goal_bbs.py` — Goal Pulse + Chronicle: 通过 MQTT BBS 实时广播状态
  - `goal_nexus.py` — Goal Nexus: 人机协作决策模式，在决策点暂停，推送飞书交互卡片，等待人类点击按钮后通过回调继续
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
│   ├── fsapp.py              #   飞书机器人（消息 + 交互卡片）
│   ├── tgapp.py              #   Telegram 机器人
│   ├── qqapp.py              #   QQ 机器人
│   ├── wechatapp.py          #   微信桥接
│   └── ... (Streamlit, TUI, Tauri 等)
├── tools/                    # 工具定义和工具函数
├── memory/                   # SOP、知识库、操作指南
├── tests/                    # 测试套件
├── scripts/                  # 工具脚本（git push 等）
└── Mqtt_bbs_server/          # MQTT BBS 看板服务
```

## Docker 运行

```bash
docker build -t genericagent:latest .
docker run --env-file .env genericagent:latest
```

## Goal Nexus（人机协作）

Goal Nexus 在 Goal Mode 基础上增加了**人机协作决策机制**：

```
# 创建带决策点的状态文件
echo '{"objective":"审计代码质量","budget_seconds":1800,"decision_points":["架构评审","安全审计"]}' > temp/goal_state.json
set GOAL_STATE=temp\goal_state.json

# 启动 Goal Nexus 模式
python agentmain.py --reflect reflect/goal_nexus.py
```

**全链路流程**:
Agent 遇到决策点 -> 回复中写入 `[ASK_HUMAN]` 标记 -> fsapp.py 推送带按钮的飞书交互卡片 -> 人类点击选项 -> 回调流经 MQTT 回到 Agent -> Agent 继续执行

## 测试

当前 **37 个测试用例**，覆盖 Phase 1-3（Goal Mode, Pulse, Chronicle, Prism, Sentinel, Nexus）：

```bash
pytest tests/ -v
```

## 文档

详见 `docs/` 设计文档和 `memory/` 的 SOP 及操作指南。
