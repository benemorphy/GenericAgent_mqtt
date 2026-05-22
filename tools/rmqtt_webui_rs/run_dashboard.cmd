@echo off
cd /d D:\open_claw_agent\GenericAgent_mqtt\tools\rmqtt_webui_rs
set PATH=C:\Users\user\.cargo\bin;C:\Users\user\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;D:\tools\w64devkit\bin;C:\Windows\system32;C:\Windows
echo [1/2] ±‡“Î rmqtt_webui_rs ...
cargo build
echo.
echo [2/2] ∆Ù∂Ø Dashboard£®∞¥ Ctrl+C Õ£÷π£©...
set MQTT_USERNAME=dashboard_agent
set MQTT_PASSWORD=dashboard_agent
target\debug\rmqtt_webui_rs.exe
pause
