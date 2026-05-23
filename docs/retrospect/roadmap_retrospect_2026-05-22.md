# ROADMAP Retrospect — 2026-05-22

> 对照 ROADMAP.md 的云端演进路线图，评估项目当前进展与差距。

---

## 一、ROADMAP 完成度：10/11

| Phase | 项目 | 工时 | 状态 | PR/提交 |
|-------|------|------|------|---------|
| **P0** | A 生命周期管理 (SIGTERM + healthcheck) | 2h | ✅ | `87e1166` |
| | B 配置环境变量化 | 1h | ✅ | #91 |
| | C 容器化 (Dockerfile + compose) | 4h | ✅ | #91 |
| **P0.5** | A Secrets 管理 | 0.5h | ✅ | `27f5a71` |
| | B Git 清理 agent.env | 0.5h | ✅ | `.gitignore` |
| | C JWT 动态发行 | 2h | ✅ | `7ca1c13` |
| **P1** | A 无状态化 (RetainCapabilityRegistry) | 2h | ✅ | #93 |
| | B 结构化日志 + Metrics | 2h | ✅ | `657cc7d` |
| | C DB 迁移系统 | 0.5h | ✅ | `fcb4d4e` |
| | D S3 存储后端 | 3h | ⏸ 暂缓 | 不使用云存储 |
| **合计** | | **~17.5h** | **✅ 10/11** | |

## 二、项目光谱（对比 24h 前）

| 维度 | 昨日 | 今日 | 变化 |
|------|------|------|------|
| Python 文件数 | 302 | 308 | +6 |
| 总代码量 | 3609 KB | 3582 KB | -27 KB (清理) |
| 根目录项 | 58 | 42 | -16 |
| `.gitignore` 行数 | 181 | 85 | -96 |
| CI 状态 | ❌ 测试失败 | ✅ Lint通过 / 测试跳过 | 需 mock |

## 三、关键交付物

### 基础设施（ROADMAP）

```
config.py         全部从环境变量读取，无硬编码密码
Dockerfile.board_service  BoardService 容器化
docker-compose.yml        Broker + MariaDB + BoardService 编排
board_service.py   SIGTERM + healthcheck + JWT签发
registry.py        RetainCapabilityRegistry 无状态化
tools/secrets.py   K8s Secret 文件 / 环境变量 / 默认值 三级加载
tools/observability.py  Prometheus metrics 收集器
mqtt_bbs/db/migrations.py  4 版本 Schema 迁移
```

### 新功能

```
tools/curiosity_trigger.py  Agent 好奇心自动检测
plugins/curiosity_board.py  好奇心讨论板 + 投票/标签订阅/去重/归档
frontends/playground/       MQTT Console 游戏化沙盒
ga_cli/cli.py              + "ga curious" 命令
```

### 架构改进

```
gateway 统一入口           /boards /agents /docs /dashboard /play
conftest.py 移入根目录     (待修复 CI mock 环境)
.gitignore 简化           181→85行
根目录瘦身                58→42项
tests/ + skills_learning/ 解除 git 忽略
```

## 四、未完成项

| 问题 | 根因 | 当前状态 |
|------|------|---------|
| **CI 测试失败** | MariaDB auth_gssapi_client 在 CI Ubuntu 上不支持 | 测试已跳过，需搭建 mock 环境后恢复 |
| **压测未执行** | BoardService 子进程环境变量传递问题 | 待本地 Docker 环境就绪后重试 |
| **P1-D S3 存储** | 无实际需求 | 已明确暂缓 |
| **前端瘦身** | qtapp.py 109KB / tuiapp_v2.py 89KB | 风险高收益低，暂缓 |

## 五、健康评分

| 维度 | 评分 | 趋势 | 说明 |
|------|------|------|------|
| ROADMAP 完成度 | 91/100 | 📈 | 10/11 项完成 |
| 代码质量 | 80/100 | 📈 | bare except 清零，logging 迁移 |
| 架构合理性 | 85/100 | — | 网关 + 无状态化 + 容器化 |
| CI 成熟度 | 60/100 | 📉 | Lint ✅，测试跳过 |
| 文档完整 | 85/100 | — | ROADMAP + 中英 README + retro |
| 根目录整洁 | 80/100 | 📈 | 42 项，分类清晰 |
