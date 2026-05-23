# 项目代码复盘：诊断与改进建议

**分析日期**: 2026-05-21
**分析范围**: llmcore.py, agentmain.py, ga.py, agent_loop.py, tools/md_server.py,
              tools/config_service.py, scripts/git_push.py, tools/hooks_default.py,
              tests/, frontends/, tools/

## 优先级 P0：立即影响稳定性

### 1. bare `except:` 比率过高

| 文件 | except总数 | bare except | 比例 |
|------|-----------|-------------|------|
| llmcore.py | 19 | 9 | 47% |
| agentmain.py | 7 | 3 | 42% |
| ga.py | 8 | 3 | 37% |
| scripts/git_push.py | 5 | 2 | 40% |

**后果**: `except:` 会捕获 `KeyboardInterrupt`、`SystemExit`，且无法区分错误类型，
生产故障时所有信号被吞。

**建议**: 批量改为 `except Exception:`，关键路径加 `except (KeyError, ValueError) as e:` 精确捕获。

### 2. print 日志 === 故障黑箱

8 个核心文件全量使用 `print()`，**零 `logging` 调用**。

| 文件 | print 调用 |
|------|-----------|
| scripts/git_push.py | 42 |
| tools/md_server.py | 11 |
| llmcore.py | 10 |
| tools/config_service.py | 2 |

**后果**: 故障时无法分级查看、按模块过滤、带时间戳追踪时序、日志轮转。

**建议**: 引入 `logging.getLogger(__name__)`，分 3 批迁移。

## 优先级 P1：架构可维护性

### 3. llmcore.py 体积与行宽

- 806 行，60 函数，11 类
- 47 行超 120 字符（最长 232 字符）
- 核心循环、SSE 解析、消息格式化、会话管理仍在一个文件

### 4. tests/ 僵尸化

12 个 `tests/` 文件中仅 1 个有真实测试用例（`test_turn_policies.py: 5 cases`），
其余 11 个是压测脚本。`conftest.py` 仅 2 行空壳。

### 5. frontends/ 重复模式

22 个文件，4 个超 1000 行（fsapp 1018, tgapp 982, qtapp 2478, tuiapp_v2 2250）。
每个前端独立初始化 agent、解析配置、处理消息格式。

### 6. 安全审计逻辑不可复用

`scripts/git_push.py`（258 行）内嵌审计函数但不可被其他入口调用。
`--skip-audit` 直接跳过所有检查。

## 优先级 P2：技术债

### 7. ConfigService 降级通知缺失

profile 不存在时降级到 mykey.py 但不通知监听器（`changed=False`）。

### 8. 僵尸代码

`_render_index` 已不用但保留（200 行）。`_build_nav` 内的 `_rel_path` 闭包不可复用。

### 9. 文件名校验缺失

`docs/` 目录曾出现前导空格文件名 ` brainstorm_cdaln_synthesis.md`。

## 执行优先级

| 优先级 | 改进项 | 预估工作量 | 收益 |
|--------|--------|-----------|------|
| P0 | bare `except:` → `except Exception:` | 1 天 | 避免生产故障信号被吞 |
| P0 | 引入 `logging` 替代 `print` | 2 天 | 故障可诊断性从0到1 |
| P1 | 为核心函数写单元测试 | 2 天 | 每次改动的安全网 |
| P1 | frontends 公共逻辑抽取 | 3 天 | 减少6个前端重复代码 |
| P1 | 抽出 `tools/security_audit.py` | 0.5 天 | 所有入口共用审计 |
| P2 | 移除僵尸代码 | 0.5 天 | 减少迷惑性死代码 |
| P2 | 加文件名 lint 检查 | 0.5 天 | 防止含空格文件入仓 |
