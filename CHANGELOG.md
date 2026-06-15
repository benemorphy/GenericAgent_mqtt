# Changelog

## 0.3.0 (2026-06-01)

### Added
- Refactored board_service.py (940 lines) into 5 modules:
  - board_config.py: Configuration and constants
  - board_db.py: CapabilityRegistry and MariaDBWrapper
  - board_handlers.py: 12 MQTT message handlers
  - board_core.py: BoardService lifecycle and main()
  - board_service.py: Backward-compatible wrapper
- 7 new test files with 38 total test cases
- test_board_config.py: webhook_send and constants
- test_board_core.py: BoardService initialization
- test_board_service.py: CapabilityRegistry (6 tests), MariaDBWrapper (2 tests)
- test_goal_bbs.py: MQTT-mocked goal_bbs tests (4 tests)
- Coverage increased to 16% (Mqtt_bbs_server)
- .env.example: Added GATEWAY_HEALTHCHECK and DB_TIMEOUT

### Fixed
- CapabilityRegistry API: get_agents/get_agent instead of query/register
- MariaDBWrapper compatibility with SQLite interface

## 0.2.0 (2026-06-01)

### Added
- Code review Phase 2: 34 fixes across security, engineering, code quality
- Multi-stage Dockerfile with non-root user
- Docker Compose GA service with health checks
- Makefile for build automation (test/lint/clean/docker)
- Tauri CSP security policy
- docs/index.md documentation index
- README.md with configuration table and Docker guide
- py.typed marker for PEP 561 compliance
- Log rotation (RotatingFileHandler, 10MB x 5)
- Windows ANSI color support
- Thread daemon=True safety (stress test scripts)

### Fixed
- TMWebDriver.jump() XSS injection (json.dumps + URL scheme whitelist)
- CI Pipeline lint job (removed `continue-on-error: true`)
- pyproject.toml package discovery (added all 9 sub-packages)
- login.html Jinja2 syntax error (DOCTYPE before extends)
- bbs_browser login.html Jinja2 syntax
- Mqtt_bbs_server: 55 emoji in logs replaced with text
- Mqtt_bbs_client: 6 emoji in logs replaced with text
- JWT hardcoded fallback secret removed (fail-closed)
- DB credentials hardcoded in hitl_approval.py (now reads env vars)
- ffmpeg_utils.py hardcoded paths (now uses shutil.which)
- ontology_model.py hardcoded mosquitto path
- desktop_bridge.py wrong mykey.txt reference (should be mykey.py)
- chatapp_common.py broken imports (continue_cmd/btw_cmd)
- Gateway 2s latency (bbs.py timeout 2→0.5)
- agentmain.py: shebang error handling regression
- ruff auto-fix: 140 files, unused imports cleanup

### Changed
- requirements.txt: all deps pinned to exact versions
- docker-compose.yml: restructured with health checks
- pyproject.toml: expanded package discovery
- .gitignore: comprehensive ignores

## 0.1.0 (2026-05-??)

### Added
- Initial release
