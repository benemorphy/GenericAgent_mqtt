# EMQTT Design Principles — Knowledge Patterns for MQTT Client in Erlang

> Extracted from emqx/emqtt GitHub repository (Erlang MQTT 5.0 Client)
> Generated: 2026-05-16 via DeepSeek LLM analysis

## Architecture Patterns (5)
- [90%] OTP gen_server pattern for client state management
- [88%] Supervision tree with OTP supervisors for process lifecycle management
- [87%] Release packaging pattern with rel directory and bin script generation
- [85%] Compile-time feature toggling (BUILD_WITHOUT_QUIC) for optional transport support
- [82%] Transport layer abstraction supporting TCP, SSL/TLS, WebSocket, and QUIC

## Protocol Patterns (4)
- [95%] Multi-version MQTT protocol support (v5.0, v3.1.1, v3.1)
- [95%] QoS level support (0, 1, 2) for publish/subscribe operations
- [90%] Retained message support with boolean flag for publish operations
- [88%] Will message configuration for unexpected disconnection handling

## Transport Patterns (2)
- [92%] Mutually exclusive transport options: SSL, WebSocket, QUIC cannot be combined
- [90%] TLS version negotiation supporting tlsv1.0 through tlsv1.3

## Connection Management Patterns (3)
- [90%] Keepalive mechanism with configurable PINGREQ interval (default 300s)
- [85%] Automatic client ID generation with hostname and random hex suffix

## CLI Tool Design Patterns (3)
- [92%] CLI command pattern with subcommands (pub/sub) and hierarchical help
- [90%] Short and long option syntax with argument parsing
- [85%] Repeat publish pattern with configurable count and delay parameters

## Security Patterns (2)
- [90%] PEM-encoded certificate chain validation with CAfile, cert, and key files
- [85%] Username/password authentication pattern for broker authorization

## Error Handling Patterns (2)
- [82%] Error handling through socket error detection and reconnect logic
- [80%] Pending call error propagation on disconnect events

## MCP (Memory Consolidation)

### Relation to build_mqtt_client_with_erlang skill
These patterns complement the existing rev12 knowledge patterns by providing:
- Deeper architectural details (OTP gen_server, supervision tree)
- Transport layer specifics (QUIC, WebSocket support)
- CLI command pattern with subcommand design
- Packaging and release patterns

### Usage
Reference this file when:
- Building/improving MQTT client implementations in Erlang
- Designing CLI tools with pub/sub subcommands
- Implementing TLS/SSL certificate handling
- Setting up OTP supervision for connection management
