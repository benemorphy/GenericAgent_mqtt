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

:: ── 4. Worker Agent（如未运行） ──
tasklist /fi "username eq %username%" /v 2>nul | findstr /i "worker_agent" >nul
if %errorlevel% equ 0 (
    echo [OK] Worker Agent 已在运行
) else (
    echo [..] 启动 Worker Agent...
    start "worker-agent" /B /MIN ".venv\Scripts\python.exe" -m mqtt_bbs.examples.worker_agent
    timeout /t 3 /nobreak >nul
    echo [OK] Worker Agent 已启动
)

echo.
echo ========================================
echo  ✅ 自主运行环境启动完成！
echo.
echo  Web UI:  http://localhost:%WEBUI_PORT%
echo  Broker:  127.0.0.1:1883
echo ========================================
echo.
