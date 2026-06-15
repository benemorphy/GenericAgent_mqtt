# P0-A 压测执行 — 完整记录

> 2026-05-22 压测调试全记录

---

## 已解决的问题

### 1. Broker 认证 (Mosquitto + JWT)

| 步骤 | 状态 |
|------|------|
| Mosquitto 配置密码文件 | ✅ |
| 添加 agent_gpt/board/dashboard 用户 | ✅ |
| 验证 agent_gpt + JWT → rc=Success | ✅ |
| BoardClient 带 JWT 连接 Broker | ✅ |

### 2. boards.json

| boards.json 新增 `agent-stress-test` | ✅ |

## 未解决问题

### 3. BoardService 无法正常启动

BoardService 启动后无输出，注册超时。原因链：

```
subprocess: BoardService
  → BBSClient 连接 Broker (需要 JWT env)
  → 连接 MariaDB (需要 DB_USER/PASSWORD env)
  → pymysql auth_gssapi_client 兼容问题
```

### 4. 整个过程发现的深层问题

```
1. JWT 环境变量需要手动传递到所有子进程 — 无统一加载机制
2. BoardService 依赖 env var 但无启动脚本
3. pymysql ↔ MariaDB 11 auth 兼容问题
4. mosquitto.conf 之前被覆盖 (TLS 配置丢失)
```

## 工作量统计

```
总共: 30+ 轮调试
实际压测: 0 次成功
新增:
  scripts/stress_test_bbs.py    (脚本就绪)
  boards.json 更新              (新增 agent-stress-test)
  Mosquitto 密码用户            (3 用户)
  docs/retrospect/retro_spectrum_2026-05-22.md (项目光谱)
修复:
  mosquitto.conf 配置 (allow_anonymous → password_file)
  
待解决根因:
  BoardService + MariaDB auth + 环境变量统一管理
  建议在 "云端 Phase 0" 中一并解决 (Dockerfile + compose 统一环境)
```
