# GenericAgent_mqtt

A fork of [GenericAgent](https://github.com/lsdefine/GenericAgent) (MIT License).
Core change: replaces file-based agent communication with an MQTT message bus for distributed cross-machine real-time collaboration.

---

## Project Structure (3 Parts)

```
GenericAgent_mqtt/
├── Part 1: Agent Core         ← What you interact with daily
├── Part 2: MQTT Infrastructure  ← Services to run on a VPS
└── Part 3: GA_tools             ← Standalone viewer/converter tools
```

---

## Part 1: Agent Core

The agent system inherited from GenericAgent, enhanced with MQTT communication.

| Component | Description |
|-----------|-------------|
| `agentmain.py` / `ga.py` | Main entry: `ga agent`, `ga gui`, `ga web` |
| `ga_cli/` | CLI command set |
| `llmcore.py` | LLM Core: multi-Provider factory, Mixin sessions, tool calling |
| `frontends/` | Frontends: Feishu Bot / Telegram / Web Gateway |
| `memory/` | Memory system: SOPs, skills, working memory |
| `agents/` | WorkerAgent implementations |
| `skills_learning/` | Case-driven skill learning |
| `tools/` | Agent toolset (see below) |

### Agent Tools (tools/)

| Tool | Description |
|------|-------------|
| `dream_engine.py` | Agent Dreaming: memory digestion & cross-domain association |
| `reflection_engine.py` | Post-task introspection & skill extraction |
| `brainstorm_swarm.py` | Brainstorm Swarm: multi-Agent ideation |
| `curiosity_board_client.py` + hooks system | Curiosity Engine: proactive exploration |
| `inspiration_board.py` | MQTT-driven creative collaboration |
| `gui_vision.py` | GUI vision perception & OCR |
| `feishu_reminder.py` | Feishu Bot integration |
| `file_search.py` | File search (Everything SDK) |
| `security_audit.py` | Pre-push security audit |
| `llm_providers/` | Unified LLM Provider interface |
| `simphtml_rs/` | Rust HTML simplification engine |

---

## Part 2: MQTT Infrastructure (VPS Deployment)

Standalone communication layer services, designed for VPS deployment.

| Component | Description | Deployment |
|-----------|-------------|------------|
| `mqtt_bbs/` | BoardService + BBSClient + Persistence + Scheduler | `python -m mqtt_bbs.board_service` |
| `tools/board_service_rs/` | Rust high-performance BoardService | Standalone binary |
| `tools/mqtt_bbs_rs/` | Rust MQTT BBS components | Standalone binary |
| `tools/rmqtt_webui.py` | MQTT Broker Web dashboard | `python tools/rmqtt_webui.py` |
| `tools/rmqtt_webui_rs/` | Rust Web dashboard | Standalone binary |
| `tools/rmqtt_auth_rs/` | Rust MQTT auth extension | Standalone binary |
| `tools/gen_jwt.py` | JWT token generation | Utility script |
| `tools/secrets.py` | Secrets management | Utility script |
| `docker/` / `Dockerfile.*` | Docker deployment | `docker-compose up` |
| `k8s/` | Kubernetes deployment | `kubectl apply -f k8s/` |

### MQTT BBS Topic Protocol

| Category | Topic | Description |
|----------|-------|-------------|
| Board | `v2/board/{name}/register|post|query` | Agent registration/posting/query |
| Task | `v2/task/{id}/input|output|status` | Task distribution & status |
| State | `v2/state/{ns}/{key}` | Shared state (CAS optimistic lock) |
| Response Slot | `v2/agent/{id}/rpc/res/#` | Pre-subscribed RPC response |

### Quick Deploy

```bash
# 1. Start MQTT Broker
rmqtt start

# 2. Start BoardService (Python)
python -m mqtt_bbs.board_service

# 3. Or use Rust version (high performance)
cd GA_tools && ./md_server_rs/target/release/board_service_rs
```

---

## Part 3: GA_tools (Standalone Tools)

Independent viewer/conversion tools, usable separately from the agent.

| Tool | Description |
|------|-------------|
| `md_to_ppt_pipeline.py` | Markdown to PPT conversion pipeline |
| `echart_ppt_pipeline.py` | ECharts HTML preview to pyecharts to PPT |
| `html_slides.py` | HTML slide generation |
| `md_server_rs/` | Rust Markdown document server |
| `patch_echarts.py` | Chart.js to ECharts replacement |
| `benchmark.py` | Performance benchmarks |
| `file_sync_agent.py` | File sync tool |

---

## Comparison with Upstream

| Aspect | GenericAgent (Upstream) | GenericAgent_mqtt |
|--------|------------------------|-------------------|
| Agent Communication | File I/O + polling | MQTT Pub/Sub + real-time push |
| Machine Boundary | Single machine | Cross-machine via Broker |
| Real-time | Seconds | Milliseconds |
| Parallelism | 1:1 | N:M arbitrary concurrency |
| Shared State | None | WhiteboardKV (CAS optimistic lock) |
| Capability Discovery | None | CapabilityRegistry |
| Task Distribution | File directory convention | Board + DAG workflow |

---

## Quick Start

```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt && pip install -e .
# Configure via env var (preferred) or mykey.py
export DEEPSEEK_API_KEY=sk-xxx
ga agent    # Interactive Agent
```

With MQTT:

```bash
rmqtt start && python -m mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

---

## License

MIT License — Same as upstream [GenericAgent](https://github.com/lsdefine/GenericAgent).
