# GenericAgent (GA)

Multi-agent infrastructure with MQTT-based communication, BBS board service, Feishu bot integration, and autonomous operation capabilities.

## Quick Start

```bash
pip install -r requirements.txt
python agentmain.py --task "your task description"
```

## Core Architecture

- **agentmain.py**: Main entry point (CLI + agent loop)
- **ga.py**: GenericAgentHandler — core agent logic
- **llmcore.py**: LLM provider abstraction (Claude, OpenAI)
- **tools/**: Tool definitions, utilities, security, logging
- **agents/**: Multi-agent orchestration (langgraph)
- **frontends/**: User interfaces (Streamlit, TUI, Tauri desktop, Telegram, QQ, WeChat)
- **broker/**: MQTT broker integration (BoardService, gateway)

## Key Features

- Multi-provider LLM support (Claude, OpenAI, custom)
- MQTT-based inter-agent communication
- MQTT BBS (Bulletin Board System) for agent coordination
- File operations, web browsing, code execution
- Autonomous operation with reflection
- Goal mode with hierarchical task management
- Feishu/Telegram/QQ bot integrations
- Curiosity-driven exploration engine
- Ontology-based knowledge management

## Project Structure

```
GA/
  agentmain.py        Entry point
  ga.py               Core agent
  llmcore.py          LLM abstraction
  hub.pyw             System tray hub
  tools/              Tool implementations
  agents/             Multi-agent orchestration
  frontends/          User interfaces
  memory/             SOP documentation & knowledge base
  assets/             Static assets & Chrome extension
  scripts/            Utility scripts
  tests/              Test suite (pytest)
  skills_learning/    AI skill curriculum (112 lessons)
```

## Documentation

See `docs/` for design docs and `memory/` for SOPs.

## Tests

```bash
pytest tests/ -v
```
