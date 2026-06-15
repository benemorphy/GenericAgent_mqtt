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
| `curiosity_board_client.py` | Curiosity Engine: proactive exploration (client) |
| `curiosity_hooks.py` | Curiosity Engine hook integration |
| `curiosity_trigger.py` | Curiosity Engine trigger strategies |
| `inspiration_board.py` | MQTT-driven creative collaboration |
| `gui_vision.py` | GUI vision perception & OCR |
| `feishu_reminder.py` | Feishu Bot integration |
| `file_search.py` | File search (Everything SDK) |
| `security_audit.py` | Pre-push security audit |
| `agent_runner.py` | Standalone agent runner: `python agent_runner.py name cap1,cap2` |
| `config_service.py` | Unified config loading & hot-reload |
| `constraint_dashboard.py` | Constraint state awareness dashboard |
| `failure_tracker.py` | Failure-driven learning tracker |
| `hitl_approval.py` | Human-in-the-loop approval manager |
| `observability.py` | Structured logging + Prometheus metrics |
| `pii_masker.py` | PII masking middleware for LLM calls |
| `session_compactor.py` | Background L4 session compaction |
| `skill_review.py` | Spaced repetition skill review |
| `step_detector.py` | Real-time step detection for tool execution |
| `turn_policy.py` | Pluggable turn strategy chain |
| `llm_providers/` | Unified LLM Provider interface |
| `simphtml_rs/` | Rust HTML simplification engine |
| `metaso_search.py` | Metaso search: web search & knowledge acquisition |
| `browser_service.py` | Browser automation service |
| `todo_manager.py` | Todo management |
| `diagnosis_agent.py` | Diagnosis agent: system problem investigation |

---

## Part 2: MQTT Infrastructure (VPS Deployment)

Standalone communication layer services, designed for VPS deployment.

| Component | Description | Deployment |
|-----------|-------------|------------|
| `Mqtt_bbs/` | BoardService + BBSClient + Persistence + Scheduler | `python -m Mqtt_bbs.board_service` |
| `tools/rmqtt_webui.py` | MQTT Broker Web dashboard | `python tools/rmqtt_webui.py` |
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

# 2. Start BoardService
python -m Mqtt_bbs.board_service
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
rmqtt start && python -m Mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

---

## License

MIT License — Same as upstream [GenericAgent](https://github.com/lsdefine/GenericAgent).
