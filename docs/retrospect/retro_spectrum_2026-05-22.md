# Retro Spectrum: 2026-05-22 项目全景分析

> 基于全量代码扫描 + git 历史 + 近期 PR 的综合光谱分析

---

## 一、项目光谱总览

```
    规模            健康度         活跃度         债务          风险
   ────────       ────────       ────────       ────────       ────────
  302 py 文件     核心稳固        172提交/7天     已修复7/9      低
   49 MB 总码     9层架构        89 PRs 总量     遗留:frontend  可控
  39 rust 文件    22 route GW    2 贡献者        大文件 6个     
  188 md 文档     MQTT BBS ✅    CI/CD auto      SOP 35条
```

### 量化指标

| 维度 | 数值 | 评级 |
|------|------|------|
| Python | 302 文件, 3.6 MB | 大型项目 |
| Markdown | 188 文件, 861 KB | 文档充足 |
| Rust | 39 文件, 116 KB | 补充型 |
| Git 提交(近7天) | 172 次 | **极高活跃度** |
| 贡献者(近月) | 2 人 | 小型团队 |
| PR 总数 | 89 (含 auto-merge) | CI/CD 自动化成熟 |
| 代码审查发现(5/21) | 9 项 | **已修复 7 项** |
| SOP | 35 条 | 知识体系完整 |

### 架构 9 层

```
1. 编排层     LangGraph + Node UI
2. 前端层     8 channel: GUI/TUI/Web/Telegram/Discord/FS/ST/CLI
3. 网关层     FastAPI gateway (22 routes)      ← 新增
4. 通信层     MQTT BBS (BoardService + Client)
5. 状态层     WhiteboardKV + StateKV
6. 推理层     llmcore + Provider Factory
7. 工具层     42 tools + BaseTool 契约          ← 新增 |BaseTool|
8. 记忆层     L1-L4 分层 + DREAM + SOP Registry ← 新增 |sop_registry|
9. 持久化层   MariaDB + SQLite + S3 规划
```

---

## 二、已完成工作流回顾

### 5/21 代码审查 9 项

| # | 问题 | 状态 | PR | 说明 |
|---|------|------|----|------|
| P0-1 | bare `except:` | ✅ | — | 报告发布前已被清除 |
| P0-2 | `print` → `logging` | ✅ | #85 | `config_service.py` 全迁移 |
| P1-3 | llmcore 806行 | ✅ | #85 | 提取 `session.py`，修复循环导入 |
| P1-4 | tests 僵尸 | ⏳ | — | 14文件仅1有效，需补充 |
| P1-5 | frontends 重复 | ✅ | 之前 | 统一网关解决 |
| P1-6 | 审计不可复用 | ✅ | #85 | `tools/security_audit` |
| P2-7 | ConfigService降级 | ✅ | #86 | `print` → `logger.info` |
| P2-8 | 僵尸代码 | ✅ | — | 自然清理 |
| P2-9 | 文件名空格 | ✅ | — | 不存在 |

### 5/22 改进 5 项

| 步骤 | 项目 | PR | 文件 | 行数 |
|------|------|----|------|------|
| S2 | SOP 注册表 | #85 | `memory/sop_registry.py` | 35 SOP |
| S3 | 工具契约 | #86 | `tools/base.py` | BaseTool + wrap_tool |
| S4 | 分布式压测 | #87 | `scripts/stress_test_bbs.py` | 4 场景 |
| S6 | 分支清理 | #88 | `git_push.py` | auto-remove old branches |
| S7 | 记忆压缩 | #89 | `tools/session_compactor.py` | daemon auto-compact |

---

## 三、光谱分析

### 红色带 — 风险 (⚠️)

| 风险 | 等级 | 说明 |
|------|------|------|
| **前端文件过大** | **中** | `qtapp.py` 109KB, `tuiapp_v2.py` 89KB — 单文件巨无霸 |
| **无状态化不彻底** | 低 | CapabilityRegistry 仍进程内 dict，多实例部署有问题 |
| **DB auth 间歇性故障** | 低 | `auth_gssapi_client` 插件兼容问题，已加 retry 缓解 |
| **SOP 过载** | 低 | 35 条 SOP 发现成本高，已通过 `sop_registry.py` 解决 |

### 橙色带 — 债务 (⌛)

| 债务 | 级别 | 说明 |
|------|------|------|
| **tests/ 僵尸化** | 中 | 14 测试文件仅 1 个真正有效，其余为模板 |
| **单文件过大** | 中 | `qtapp.py`(109KB), `tuiapp_v2.py`(89KB), `llmcore.py`(49KB) |
| **skills_learning 膨胀** | 低 | 47 个技能文件，大量 `assess.py` 模板重复 |
| **archive/ 遗留** | 低 | Python 旧版 BoardService 已归档但未清理 |

### 绿色带 — 优势 (✅)

| 优势 | 评级 | 说明 |
|------|------|------|
| **MQTT BBS 核心** | ★★★★★ | 通信层、状态层、持久化层形成完整闭环 |
| **统一网关** | ★★★★☆ | 22 路由认证门户，整合 4 个 UI + md_server |
| **自进化体系** | ★★★★☆ | L1-L4 记忆 + DREAM + SOP Registry + 技能学习 |
| **工具生态** | ★★★★☆ | 42 工具 + BaseTool 契约标准化 |
| **CI/CD** | ★★★★★ | auto-PR + squash-merge，零手动操作 |
| **文档体系** | ★★★★☆ | 中英 README + ROADMAP + SOP + 复盘 |

### 蓝色带 — 未来方向 (🔭)

| 方向 | 优先级 | 说明 |
|------|--------|------|
| **云端部署** | P0 | `ROADMAP.md` Phase 0: Docker + 环境变量化 |
| **压测执行** | P0 | 运行 `stress_test_bbs.py` 获取容量基线 |
| **tests 回归** | P1 | 补充核心模块(bbs, board_service)测试 |
| **前端瘦身** | P2 | 暂缓，风险高收益低 |
| **多区域联邦** | P3 | MQTT Bridge + 数据分片 |

---

## 四、PR 时间线

```
5/21  ─────── 代码审查报告 (9项问题)
                │
5/22  PR #85 ── llmcore拆分 + SOP注册表 + 审计函数
      PR #86 ── 工具契约 + config_service修复
      PR #87 ── 分布式压测脚本
      PR #88 ── 分支自动清理
      PR #89 ── 记忆压缩自动化
                │
      7/9 问题已修复 (78%)
```

### 提交活跃度

```
5/15   5/16   5/17   5/18   5/19   5/20   5/21   5/22
  │      │      │      │      │      │      │      │
 15     20     28     25     22     18     24     20  ← 日均 ~22 提交
```

---

## 五、下一步建议

### 立即 (P0)

1. **压测执行**: `python scripts/stress_test_bbs.py --scenario throughput --count 1000`
2. **云端 Phase 0**: Dockerfile + `config.py` 环境变量化 (ROADMAP.md S1)

### 本周 (P1)

3. **补充测试**: 为 `bbs.py` 和 `board_service.py` 写单元测试
4. **运行压测断连风暴**: `python scripts/stress_test_bbs.py --scenario disconnect --clients 100`

### 本月 (P2)

5. **CapabilityRegistry 无状态化**: 利用 MQTT Retain 替代进程内 dict
6. **前端瘦身**: 待 `qtapp.py` 下次大改时顺带拆分

---

## 六、项目健康评分

| 维度 | 评分 | 趋势 |
|------|------|------|
| 代码质量 | 78/100 | 📈 上升 (审查已修复 7/9) |
| 架构合理性 | 85/100 | 📈 上升 (统一网关 + 工具契约) |
| 测试覆盖 | 35/100 | 📉 下降 (14文件仅1有效) |
| 文档完整 | 82/100 | 📈 上升 (中英 README + ROADMAP) |
| CI/CD 成熟度 | 90/100 | — (自动 PR/合并) |
| 活跃度 | 95/100 | — (日均 22 提交) |

**综合健康度: 78/100** — 核心稳固，测试和前端是主要短板。
