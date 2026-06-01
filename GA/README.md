# GenericAgent (GA)

Multi-agent infrastructure with MQTT-based communication, BBS board service, Feishu bot integration, and autonomous operation capabilities.

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
- **frontends/**: User interfaces (Streamlit, TUI, Tauri desktop, Telegram, QQ, WeChat)
- **Mqtt_bbs_server/**: MQTT BBS board service (distributed agent coordination)
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

```...existing content...
```

## Running with Docker

```bash
docker build -t genericagent:latest .
docker run --env-file .env genericagent:latest
```

## Tests

```bash
pytest tests/ -v
```

## Documentation

See `docs/` for design docs and `memory/` for SOPs and operational guides.
