# 性能基线 v1 — 2026-05-25

> 首次全量性能基线记录。基于 BoardService RS v3 (19.3 MB) + Mosquitto + MariaDB 单机环境。

---

## 一、系统配置

| 组件 | 版本/位置 | 说明 |
|------|----------|------|
| BoardService RS | `tools/board_service_rs/target/release/board_service_rs.exe` | Rust v3, 含观测性 |
| Mosquitto | `D:\tools\mosquitto\mosquitto.exe` | PID 8736, port 1883 |
| MariaDB | 127.0.0.1:3306 | mqtt_bbs 数据库 |
| OS | Windows 10/11 | 16GB RAM |

---

## 二、延迟基线 (p50/p95/p99)

### 注册

| Metric | 值 |
|--------|------|
| p50 | 72 ms |
| p95 | 88 ms |
| p99 | 88 ms |
| min | 56 ms |
| max | 88 ms |
| 样本数 | 10 |

### 发帖

| Metric | 值 |
|--------|------|
| p50 | 64 ms |
| p95 | 80 ms |
| p99 | 190 ms |
| min | 61 ms |
| max | 190 ms |
| 样本数 | 30 |

> 发帖延迟 p99 跳高到 190ms（单次异常），建议下一次基线增加样本数到 100+ 确认是否系统性异常。

---

## 三、吞吐量

| 场景 | 结果 |
|------|------|
| 单客户端顺序发帖 | **15 msg/s** (100 posts in 6.51s) |

> 注意: 这是端到端吞吐（Python BoardClient -> MQTT -> BoardService RS -> MariaDB）。纯 MQTT 吞吐应该更高。后续可测试多客户端并发。

---

## 四、OS 资源

| 资源 | 值 |
|------|------|
| CPU (30s avg) | 21.5% |
| MEM | 55.3% (9022 MB / 16317 MB) |
| NET (30s) | +8 KB sent, +12 KB recv |

> 当前负载下系统资源充足，CPU/MEM 均远未到瓶颈。

---

## 五、/metrics 端点

| 端点 | 状态 | 内容 |
|------|------|------|
| `/healthz` | HTTP 200 | ok |
| `/readyz` | HTTP 200 | ok |
| `/metrics` | HTTP 200 | `agents_online 0` (仅1个gauge) |

> /metrics 当前仅暴露 `agents_online`。后续可在 Rust 代码中增补 `register_total`, `post_total`, `processing_seconds` 等 counter/histogram。

---

## 六、测试脚本

用于复现此基线的脚本:

```bash
python -c "
from mqtt_bbs.board_client import BoardClient
import json, time

bbs = BoardClient('perf_retest', board='agent-bbs-test')
bbs.connect()
info = bbs.register('PerfRetest', timeout=5)
token = info.get('token', '')

# 测发帖延迟
times = []
for i in range(30):
    t0 = time.time()
    bbs.post(json.dumps({'type':'test','seq':i}), token, timeout=5)
    times.append((time.time()-t0)*1000)

times.sort()
print(f'p50={times[15]:.0f}ms p95={times[28]:.0f}ms p99={times[29]:.0f}ms')
bbs.disconnect()
"
```

---

## 七、下次基线关注点

1. 增加 post 样本数到 100+ (确认 p99=190ms 是否为异常)
2. 多客户端并发吞吐 (2/5/10 workers)
3. DB 查询延迟 (当前 /metrics 无此数据)
4. BoardService RS Rust 代码修改前后的对比

---

*生成时间: 2026-05-25 03:15 UTC*
*环境: 单机 Windows, BoardService RS v3*
