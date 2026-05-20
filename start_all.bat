@echo off
chcp 65001 >nul
title GenericAgent MQTT 自主运行
cd /d "%~dp0"

echo ========================================
echo  GenericAgent MQTT - 自主运行启动
echo ========================================
echo.

:: ── 1. rmqtt broker（如未运行） ──
tasklist /fi "imagename eq rmqttd.exe" 2>nul | find /i "rmqttd.exe" >nul
if %errorlevel% equ 0 (
    echo [OK] rmqtt broker 已在运行
) else (
    echo [..] 启动 rmqtt broker...
    start "rmqttd" /B /MIN "D:\tools\rmqtt\rmqtt-0.20.0-x86_64-pc-windows\bin\rmqttd.exe" -f "D:\tools\rmqtt\rmqtt-0.20.0-x86_64-pc-windows\etc\rmqtt.toml"
    timeout /t 3 /nobreak >nul
    echo [OK] rmqtt broker 已启动
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

:: ── 6. BoardService（MQTT BBS 持久化服务） ──
echo [..] 启动 BoardService（MQTT BBS 公告板持久化）...
start "board-service" /B /MIN ".venv\Scripts\python.exe" -m mqtt_bbs.board_service
timeout /t 3 /nobreak >nul
echo [OK] BoardService 已启动

echo.
echo ========================================
echo  ✅ 自主运行环境启动完成！
echo.
echo  Web UI:         http://localhost:%WEBUI_PORT%
echo  MQTT Dashboard: http://localhost:%DASHBOARD_PORT%
echo  Broker:         127.0.0.1:1883
echo  BBS Service:    已启用
echo ========================================
echo.
