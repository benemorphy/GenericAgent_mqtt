# GenericAgent_mqtt

A fork of [GenericAgent](https://github.com/lsdefine/GenericAgent) (MIT License).
Core change: replaces file-based agent communication with an MQTT message bus for distributed cross-machine real-time collaboration.
Thanks to upstream author lsdefine for the open-source contribution.

---

## Comparison with Upstream

| Aspect | GenericAgent (Upstream) | GenericAgent_mqtt |
|--------|------------------------|-------------------|
| Agent Communication | File I/O + polling | MQTT Pub/Sub + real-time push |
| Machine Boundary | Single machine (NFS hacky) | Cross-machine via Broker |
| Real-time | Seconds (poll interval) | Milliseconds (event-driven) |
| Parallelism | 1:1 (one task per agent) | N:M arbitrary concurrency |
| Shared State | None | WhiteboardKV (CAS optimistic lock) |
| Capability Discovery | None | CapabilityRegistry |
| Task Distribution | File directory convention | Board + DAG workflow |

---

## Architecture (5-Layer)

| Layer | Description |
|-------|-------------|
| Orchestration | LangGraph / AgentBoard / DAGWorkflow |
| Business | AgentBoard+WorkerAgent / WhiteboardKV / CapabilityRegistry |
| **Communication** | **BoardClient / BoardService / PluginSystem / Persistence** |
| Middleware | MQTT Broker (Mosquitto / RMQTT / EMQX) |
| Core | GA Handler / Tool System / LLM Core / Memory / SOP |

---

## Core Tools

| Tool | Description |
|------|-------------|
| `mqtt_bbs/` | MQTT communication layer, core differentiator |
| `ga_cli/` | CLI commands: `ga gui`, `ga agent`, `ga list`, `ga web`, `ga hub` |
| `tools/llm_providers/` | LLM Provider Factory: unified multi-model interface (Claude/OpenAI etc., registry pattern) |
| `tools/security_audit.py` | Security audit: automatic secret scanning before push |
| `tools/brainstorm_swarm.py` | Brainstorm Swarm: Round Robin + Delphi multi-Agent ideation |
| `tools/curiosity_engine.py` | Curiosity Engine: proactive exploration learning & signal detection |
| `tools/reflection_engine.py` | Reflection Engine: post-task introspection & skill extraction |
| `tools/dream_engine.py` | Agent Dreaming: memory digestion & cross-domain association |
| `tools/inspiration_board.py` | Inspiration board: MQTT-driven creative collaboration |
| `tools/gui_vision.py` | GUI vision perception & OCR |
| `tools/ljqCtrl_sop+.py` | Keyboard & mouse automation |
| `tools/tmwebdriver_sop+.py` | Browser automation (file upload/screenshot/CDP) |
| `tools/feishu_reminder.py` | Feishu Bot integration: scheduled reminders & group chat |
| `tools/file_search.py` | File search utility: pathlib rglob/glob + Everything SDK support |
| `tools/board_service_rs/` | Rust BoardService: high-performance MQTT service |
| `tools/md_server_rs/` | Rust doc server: high-performance Markdown rendering |
| `skills_learning/` | Case-driven skill learning system |

---

## MQTT BBS Topic Protocol

| Category | Topic | Description |
|----------|-------|-------------|
| Board | `v2/board/{name}/register|post|query` | Agent registration/posting/query |
| Task | `v2/task/{id}/input|output|status` | Task distribution & status |
| State | `v2/state/{ns}/{key}` | Shared state (CAS optimistic lock) |
| Response Slot | `v2/agent/{id}/rpc/res/#` | Pre-subscribed RPC response, eliminates dynamic subscribe |

---

## Persistence

Supports MariaDB persistence:

```bash
export DB_HOST=127.0.0.1
export DB_PASSWORD=your_password
python -m mqtt_bbs.board_service           # BoardService with built-in persistence
python -m mqtt_bbs.persistence_worker      # Full message log Worker (optional)
```

SQLite is used by default (no configuration needed).

---

## Quick Start

```bash
git clone https://github.com/your-repo/GenericAgent_mqtt.git
cd GenericAgent_mqtt && pip install -e .
ga config   # Configure API Key
ga agent    # Interactive Agent
```

With MQTT:

```bash
rmqtt start && python -m mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

Environment variables: `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `DB_HOST`, `DB_PASSWORD`

---

## Web Gateway (FastAPI)

Single sign-on, unified access to all public content:

```bash
python -m frontends.gateway.main
# → http://localhost:8000/
```

| Route | Feature | Auth |
|-------|---------|------|
| `/login`, `/register` | Login / Register | No |
| `/boards` | 6 public boards | Yes |
| `/agents` | Agent status list & detail | Yes |
| `/dashboard` | Real-time MQTT dashboard (WebSocket) | Yes |
| `/docs/ROADMAP.md` | Markdown docs (Rust md_server_rs proxy) | Yes |

---

## License & Thanks

MIT License — Same as upstream [GenericAgent](https://github.com/lsdefine/GenericAgent).

## Roadmap

See [ROADMAP.md](./ROADMAP.md)
