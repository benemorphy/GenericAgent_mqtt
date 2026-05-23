# Rust 开发环境配置 (Windows 本地)

> 生成: 2026-05-22 | 用途: BoardService高吞吐模块 / MQTT引擎 / 查询处理
> Agent已记录此配置备查

---

## 工具链

| 项 | 值 |
|:---|:----|
| Rust版本 | **1.95.0** (59807616e 2026-04-14) |
| 默认工具链 | **stable-x86_64-pc-windows-gnu** (GNU, 不需要Visual Studio) |
| 备用工具链 | stable-x86_64-pc-windows-msvc |
| Cargo版本 | 1.95.0 (f2d3ce0bd 2026-03-21) |
| 安装方式 | rustup-init.exe (官方) |
| 安装日期 | 2026-05-22 |

## 路径

| 组件 | 路径 |
|:-----|:------|
| rustup | `%USERPROFILE%\.cargo\bin\rustup.exe` |
| Cargo bin PATH | `%USERPROFILE%\.cargo\bin` (已自动加入系统PATH) |
| 工具链sysroot | `%USERPROFILE%\.rustup\toolchains\stable-x86_64-pc-windows-gnu` |

## 验证项目

```bash
{GA_ROOT}/rust_hello/  # 已验证编译+运行通过
```

## GA集成候选 (未来Rust实现)

| 模块 | 当前(Python) | Rust候选原因 |
|:-----|:------------|:-------------|
| BoardService 核心消息处理 | `mqtt_bbs/board_service.py` | 高吞吐MQTT消息处理 |
| 查询引擎 | `board_client.py` 中的query | 全文搜索/复杂查询 |
| 身份认证/JWT | 无专门模块 | 签名/验证性能 |
| 持久化层 | `mqtt_bbs/persistence.py` | DB连接池/批量写入 |
| MQTT客户端 | paho-mqtt | 可替换为rumqttc |

## 注意事项

1. GNU vs MSVC: 当前GNU, 无需VS。如需MSVC原生性能可装VS Build Tools后切换
2. 交叉编译: 需 `rustup target add x86_64-unknown-linux-gnu`
3. 构建产出: `rust*/target/` 应加入 `.gitignore`
