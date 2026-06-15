# Rust 工具链环境配置 (L3 存档)

最后更新: 2026-05-26

## 工具链概况
- 默认工具链: `stable-x86_64-pc-windows-msvc`
- rustc: 1.95.0 (59807616e 2026-04-14)
- cargo: 1.95.0 (f2d3ce0bd 2026-03-21)
- 链接器: MSVC link.exe (VS Build Tools 2022 VC++ 14.4x)

## VS Build Tools 2022 安装
- 安装路径: `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools`
- 组件: VC++ 2022 工具集 (x86/x64) + Windows 10 SDK (10.0.20348)
- 环境: cargo build 自动调用 vcvars64.bat 设置环境变量
- 工作负载ID: Microsoft.VisualStudio.Workload.VCTools
- 组件ID: Microsoft.VisualStudio.Component.VC.Tools.x86.x64
- SDK组件ID: Microsoft.VisualStudio.Component.Windows10SDK.20348

## Rust 项目清单 (tools/ 目录)

| 项目 | 版本 | 端口 | 描述 | 关键依赖 | 编译目标 |
|------|------|------|------|----------|----------|
| board_service_rs | 0.1.0 | - | MQTT BBS 持久化服务 (MariaDB) | rumqttc 0.25, sqlx 0.8(mysql), tokio 1 | debug |
| mqtt_bbs_rs | 0.1.0 | - | BBS 客户端库 (依赖库) | rumqttc 0.25, sqlx 0.8 | - |
| rmqtt_auth_rs | 0.1.0 | - | RMQTT HTTP Auth 服务 | ureq 2, jsonwebtoken 9 | - |
| rmqtt_webui_rs | 0.1.0 | 8900 | Broker 监控面板 | rumqttc 0.24, ureq 2, tokio 1 | debug |
| simphtml_rs | 0.1.0 | 8901 | HTML 简化提取 | scraper 0.20, regex 1 | release |

## 编译产物路径
- `tools/*/target/debug/*.exe` — debug 版
- `tools/*/target/release/*.exe` — release 版

## 常见问题
1. **MinGW GNU 工具链不可用** — ld 2.28 不支持 --high-entropy-va 链接标志, GCC 6.3 过老
2. **缺少 Windows SDK** — VS Build Tools 安装时需选 Windows10SDK.20348 组件, 否则 link.exe 找不到 kernel32.lib
3. **修改源码后需重新编译** — 使用 `cargo build` 在项目目录下执行, 自动调用 MSVC 环境
