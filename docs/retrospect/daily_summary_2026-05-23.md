# 今日工作总结 — 2026-05-23

> Rust BoardService 替换 Python 版 + 通信层压力测试

---

## 完成事项

### 1. Rust Client 迁移补完

| 模块 | 行数 | 覆盖度 | 说明 |
|------|------|--------|------|
| BBSClient | 268 | ~85% | LWT/认证/心跳/连接跟踪 |
| BoardClient | 196 | ~90% | post/query/poll/subscribe/upload |
| AgentBoard | 220 | ~70% | task/HMAC/心跳/能力声明 |
| WorkerAgent | 155 | ~70% | claim/complete/心跳/能力声明 |
| StateKV | 160 | ~80% | KV + retained + session_queue |

### 2. BoardService Rust 迁移 (Phase B0-B2)

| 改进 | 状态 | PR |
|------|------|-----|
| jsonwebtoken 纯 Rust 编译修复 | ✅ | #100 |
| SIGTERM + 离线发布 | ✅ | #100 |
| Retain 能力收集 | ✅ | #100 |
| Plugin IPC watchdog | ✅ | #101 |
| boards.json 启动加载 | ✅ | #101 |
| Healthcheck MQTT 主题 | ✅ | #101 |
| StateKV session_queue 补齐 | ✅ | #102 |
| Benchmark 脚本 | ✅ | #102 |
| Subscribe 新帖广播修复 | ✅ | #103 |

### 3. 实际替换验证

```
替换前: Python BoardService (mosquitto broker)
替换后: Rust BoardService (PID 68→1032→12544...)
测试: 10/10 功能通过
压测: 14 posts/s (单线程) / 599 posts/s (5并发) / 16 queries/s
```

### 4. 评估结论

| 项目 | 结论 |
|------|------|
| PyO3 MQTT 客户端迁移 | **暂缓** — 当前吞吐量足够，ROI 中低 |
| HTTP Gateway 迁移 | **保留 Python** — I/O 密集，Rust 收益小 |

---

## 经验教训

### 技术教训

1. **Mosquitto 密码文件脆弱**: 空白行或明文密码会导致 `Corrupt password file`；`net stop/start` 可能不重新加载，必须 `taskkill /f /im mosquitto.exe` 后手动启动
2. **Rust 闭包 + Arc 包装**: 闭包作为回调传递给 `subscribe()` 时，不能用 `as Callback` 转换，需用 `Arc::new(|| { ... })` 自动推导；`subscribe` 函数签名用泛型 `F: Fn(...)` 自动包装
3. **Python/Rust JSON schema 对齐**: Rust BoardService 需发布 `agent/bbs/{board}/new_post` 新帖通知（与 Python 版完全一致），否则 Python BoardClient 的 `subscribe_posts` 收不到推送
4. **`getrandom` + MinGW**: self-contained 目录 `rustlib\...\bin\self-contained\` 的 dlltool 可修复 `Invalid bfd target` 错误
5. **`jsonwebtoken` + Windows GNU**: `default-features = false` 跳过 `ring`/`aws-lc-sys` 原生 C 编译

### 流程教训

6. **增量替换有效**: 逐个组件替换 + 测试后再推进下一项，比一次性全量迁移更可控。实际替换中发现 3 个兼容性问题（密码文件/闭包类型/主体对齐）
7. **测试脚本先于替换**: 替换前写好完整测试用例，替换后一键验证，比手动点按更可靠
8. **验证密码文件变动**: 修改 Mosquitto 密码文件后必须全杀进程重启，仅 `net stop/start` 不可靠

---

## 文件增量

| 统计 | 值 |
|------|-----|
| PR 数量 | 5 (#99-#103) |
| 新增代码 | ~2,500 行 |
| 实际替换 | Python BoardService → Rust BoardService |
| 测试覆盖 | 10 功能点 + 压力测试 |
