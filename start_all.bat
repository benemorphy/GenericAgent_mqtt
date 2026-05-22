@echo off
chcp 65001 >nul
title GenericAgent MQTT 自主运行
cd /d "%~dp0"

echo ========================================
echo  GenericAgent MQTT - 自主运行启动
echo ========================================
echo.

:: ── 1. Mosquitto MQTT broker（如未运行） ──
tasklist /fi "imagename eq mosquitto.exe" 2>nul | find /i "mosquitto.exe" >nul
if %errorlevel% equ 0 (
    echo [OK] Mosquitto broker 已在运行
) else (
    echo [..] 启动 Mosquitto broker...
    start "mosquitto" /B /MIN "D:\tools\mosquitto\mosquitto.exe" -c "D:\tools\mosquitto\mosquitto.conf"
    timeout /t 3 /nobreak >nul
    echo [OK] Mosquitto broker 已启动 (1883 + TLS 8883)
)

:: ── 2. MariaDB（如未运行） ──
:: MariaDB 通常作为服务运行，这里只是检查
net start | find /i "MariaDB" >nul
if %errorlevel% equ 0 (
    echo [OK] MariaDB 已在运行
) else (
    echo [!] MariaDB 未运行，尝试启动服务...
    net start MariaDB 2>nul
    if errorlevel 1 echo [!] 请确认 MariaDB 服务已安装
)

:: ── 3. Web UI（如未运行） ──
set WEBUI_PORT=8100
netstat -ano | findstr ":%WEBUI_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [OK] Web UI (port %WEBUI_PORT%) 已在运行
) else (
    echo [..] 启动 rmqtt Web UI...
    start "rmqtt-webui" /B /MIN ".venv\Scripts\python.exe" tools\start_webui.py
    timeout /t 4 /nobreak >nul
    echo [OK] Web UI 已启动 (http://localhost:%WEBUI_PORT%)
)

:: ── 4. MQTT Dashboard（如未运行） ──
set DASHBOARD_PORT=8501
netstat -ano | findstr ":%DASHBOARD_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [OK] MQTT Dashboard (port %DASHBOARD_PORT%) 已在运行
) else (
    echo [..] 启动 MQTT Dashboard...
    start "mqtt-dashboard" /B /MIN ".venv\Scripts\streamlit.exe" run frontends/dashboard_mqtt.py --server.port %DASHBOARD_PORT%
    timeout /t 5 /nobreak >nul
    echo [OK] MQTT Dashboard 已启动 (http://localhost:%DASHBOARD_PORT%)
)

:: ── 5. Worker Agents（通过 launcher_mqtt.py 启动5个） ──
echo [..] 启动 5 个 Worker Agent（scanner, analyzer, reporter, monitor, helper）...
start "mqtt-launcher" /B /MIN ".venv\Scripts\python.exe" frontends/launcher_mqtt.py --workers 5
timeout /t 5 /nobreak >nul
echo [OK] 5 个 Worker Agent 已启动

:: ── 6. BoardService（MQTT BBS 持久化服务 — Rust 版） ──
echo [..] 启动 BoardService RS（Rust MQTT 公告板持久化）...
set BOARD_RS_DIR=%~dp0tools\board_service_rs
set BOARD_RS_EXE=%BOARD_RS_DIR%\target\release\board_service_rs.exe
if not exist "%BOARD_RS_EXE%" set BOARD_RS_EXE=%BOARD_RS_DIR%\target\debug\board_service_rs.exe
if exist "%BOARD_RS_EXE%" (
    start "board-service-rs" /B /MIN "%BOARD_RS_EXE%" --db-url "mysql://root:mariadb@127.0.0.1/mqtt_bbs"
    timeout /t 3 /nobreak >nul
    echo [OK] BoardService RS 已启动
) else (
    echo [!] Rust BoardService 未编译，回退到 Python 版...
    start "board-service" /B /MIN ".venv\Scripts\python.exe" -m mqtt_bbs.board_service
    timeout /t 3 /nobreak >nul
    echo [OK] BoardService (Python fallback) 已启动
)

:: ── 7. MariaDB 持久化 Worker ──
echo [..] 启动 MariaDB 持久化 Worker（保存全部 MQTT 消息）...
start "bbs-persist" /B /MIN ".venv\Scripts\python.exe" -m mqtt_bbs.persistence_worker
timeout /t 2 /nobreak >nul
echo [OK] MariaDB 持久化 Worker 已启动

:: ── 8. 默认 WorkerAgent ──
echo [..] 启动默认 WorkerAgent（发布心跳/能力，可被Dashboard看到）...
start "default-worker" /B /MIN ".venv\Scripts\python.exe" -c "
import sys, time, threading
sys.path.insert(0, '.')
from mqtt_bbs.bbs import WorkerAgent
w = WorkerAgent('default_worker', capabilities=['scan','analyze','monitor','report','ops'])
@w.on_task
def h(msg):
    w.stream_out(f'Processing: {msg}')
    return {'status': 'done', 'task': msg.get('type')}
w.start()
try:
    while True:
        time.sleep(10)
except:
    w.stop()
"
timeout /t 2 /nobreak >nul
echo [OK] 默认 WorkerAgent 已启动

:: ── 9. MD Server（Markdown 文件浏览器，端口 8899） ──
set MD_PORT=8899
netstat -ano | findstr ":%MD_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [OK] MD Server (port %MD_PORT%) 已在运行
) else (
    echo [..] 启动 MD Server（Markdown 文件浏览器）...
    start "md-server" /B /MIN tools\md_server_rs\target\release\md_server_rs.exe --port %MD_PORT%
    timeout /t 3 /nobreak >nul
    echo [OK] MD Server 已启动 (http://localhost:%MD_PORT%)
)

:: ── 10. MQTT 监控面板（Rust，端口 8900） ──
set MQTT_MONITOR_PORT=8900
netstat -ano | findstr ":%MQTT_MONITOR_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo [OK] MQTT 监控面板 (port %MQTT_MONITOR_PORT%) 已在运行
) else (
    echo [..] 启动 MQTT 监控面板（Rust）...
    start "mqtt-monitor-rs" /B /MIN tools\rmqtt_webui_rs\target\release\rmqtt_webui_rs.exe
    timeout /t 3 /nobreak >nul
    echo [OK] MQTT 监控面板已启动 (http://localhost:%MQTT_MONITOR_PORT%)
)

echo.
echo ========================================
echo  ✅ 自主运行环境启动完成！
echo.
echo  Web UI:         http://localhost:%WEBUI_PORT%
echo  MQTT Dashboard: http://localhost:%DASHBOARD_PORT%
echo  MQTT Monitor:   http://localhost:%MQTT_MONITOR_PORT%
echo  MD Server:      http://localhost:%MD_PORT%
echo  Broker:         127.0.0.1:1883
echo  BBS Service:    已启用
echo ========================================
echo.
