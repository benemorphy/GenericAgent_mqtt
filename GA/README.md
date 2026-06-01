# GenericAgent (GA)

Multi-agent infrastructure with MQTT-based communication, BBS board service, Feishu bot integration, autonomous operation capabilities, and **human-in-the-loop decision mode** (Goal Nexus).

## Quick Start

```bash
pip install -r requirements.txt

# Configure environment (copy and fill in values)
cp .env.example .env

# Run the agent
python agentmain.py --task "your task description"
```

## Core Architecture

- **agentmain.py**: Main entry point (CLI + agent loop)
- **ga.py**: GenericAgentHandler — core agent logic
- **llmcore.py**: LLM provider abstraction (Claude, OpenAI, DeepSeek)
- **tools/**: Tool definitions, utilities, security, logging
- **agents/**: Multi-agent orchestration (langgraph)
- **frontends/**: User interfaces (Streamlit, TUI, Tauri desktop, Telegram, QQ, WeChat, Feishu)
- **Mqtt_bbs_server/**: MQTT BBS board service (distributed agent coordination)
- **reflect/**: Reflective loop modules — autonomous execution modes with MQTT pulse/chronicle
  - `goal_mode.py` — Goal Mode: sustained self-driven execution until budget exhausted
  - `goal_bbs.py` — Goal Pulse + Chronicle: real-time state broadcast over MQTT BBS
  - `goal_nexus.py` — Goal Nexus: human-in-the-loop decision mode, pauses at decision points, pushes interactive Feishu cards, waits for human response via card button callbacks
  - `goal_prism.py` — Goal Prism: multi-perspective analysis for complex decisions
  - `goal_sentinel.py` — Goal Sentinel: watch-loop that monitors and guards execution
- **memory/**: SOP documentation and knowledge base

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | Yes (or LLM_API_KEY) |
| `MQTT_HOST` | MQTT broker address | Yes (default: 127.0.0.1) |
| `JWT_SECRET` | 64-char random secret for auth | Yes (in production) |
| `GITHUB_TOKEN` | GitHub personal access token | For git operations |

## Project Structure

```
├── agentmain.py              # Main entry point (CLI / reflect / MQTT)
├── ga.py                     # GeneraticAgent — core agent loop
├── llmcore.py                # LLM provider abstraction
├── reflect/                  # Reflective loop modules
│   ├── goal_mode.py          #   Goal Mode: sustained self-driven execution
│   ├── goal_nexus.py         #   Goal Nexus: human-in-the-loop (Feishu cards)
│   ├── goal_prism.py         #   Goal Prism: multi-perspective analysis
│   ├── goal_sentinel.py      #   Goal Sentinel: watch-loop guard
│   ├── goal_bbs.py           #   Goal Pulse + Chronicle (MQTT BBS)
│   ├── autonomous.py         #   Autonomous operation mode
│   └── scheduler.py          #   Scheduled task runner
├── frontends/                # User interface bridges
│   ├── fsapp.py              #   Feishu bot (message + interactive card)
│   ├── tgapp.py              #   Telegram bot
│   ├── qqapp.py              #   QQ bot
│   ├── wechatapp.py          #   WeChat bridge
│   └── ... (Streamlit, TUI, Tauri, etc.)
├── tools/                    # Tool definitions & utilities
├── memory/                   # SOPs, knowledge base, operation guides
├── tests/                    # Test suite
├── scripts/                  # Utility scripts (git push, etc.)
└── Mqtt_bbs_server/          # MQTT BBS board service
```

## Running with Docker

```bash
docker build -t genericagent:latest .
docker run --env-file .env genericagent:latest
```

## Goal Nexus (Human-in-the-Loop)

Goal Nexus extends Goal Mode with **human-in-the-loop decision making**:

```
# Create a state file with decision points
echo '{"objective":"审计代码质量","budget_seconds":1800,"decision_points":["架构评审","安全审计"]}' > temp/goal_state.json
set GOAL_STATE=temp\goal_state.json

# Start Goal Nexus mode
python agentmain.py --reflect reflect/goal_nexus.py
```

**Flow**: Agent hits a decision point -> writes `[ASK_HUMAN]` marker in response -> fsaap.py pushes interactive Feishu card with buttons -> human clicks -> response flows back via MQTT -> agent resumes.

## Tests

Currently **37 tests** across Phase 1-3 (Goal Mode, Pulse, Chronicle, Prism, Sentinel, Nexus):

```bash
pytest tests/ -v
```

## Documentation

See `docs/` for design docs and `memory/` for SOPs and operational guides.
