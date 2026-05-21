# Brainstorm: 项目的净化与洗涤

> 生成: 2026-05-21 | 方法: 3角色多视角脑暴 + 代码实测审计
> 前置: code_and_rumination.md (反刍哲学) → 本篇(反刍的实践:清理)

---

## 角色 A：源流守护者 (Source Gardener)

**视角**: 代码仓库如同花园，需要定期修剪枯枝、清除杂草、腾出生长空间。

### 现场审计报告

| 污垢类型 | 量级 | 严重程度 |
|:---------|:-----|:---------|
| `__pycache__` 缓存 | **11629 个 .pyc 文件** | 高 — 磁盘浪费 + git 泄露风险 |
| `temp/` 临时文件 | **2.4MB** (含2428KB model_responses/) | 中 — 长期积累不清理 |
| 根目录膨胀 | 29个顶级目录/文件 | 中 — 新开发者无从下手 |
| `skills_learning/` 被完全忽略 | 519KB 技能数据不被 git 追踪 | 高 — 反刍产物丢失风险 |
| `tests/` 被忽略 | 已有测试文件需 `-f` 强制添加 | 高 — CI 混淆 |
| `.gitignore` | 60+ 行，大量负规则 | 高 — 维护负担 |

### 修剪方案

#### 1. 缓存清理（无风险，立即执行）

```bash
# 清理所有 __pycache__
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
# 清理 temp/ 中过期文件 (保留最近3天的模型响应)
find temp/ -name "*.py" -type f -delete  # 临时脚本
# 清理 model_responses/ (超过7天的)
```

**11629 个 .pyc** 的主要来源是 `skills_learning/` 和 `tests/` 下的技能评估案例——每个技能 rev 都产生自己的 `__pycache__`。一个全局清理脚本应该加入 `scheduled_task`。

#### 2. 根目录瘦身

当前 29 项 → 建议合并为：

```
genericagent/          ← 核心代码(agentmain, ga, ga_cli)
  tools/               ← 工具模块
  frontends/           ← 前端
  mqtt_bbs/            ← MQTT 服务
config/                ← 配置(mykey, pyproject)
docs/                  ← 文档
  architecture/        ← 架构设计
  deep_research/       ← 深度研究
assets/                ← 静态资源
memory/                ← 记忆系统 (已结构)
scripts/               ← 工具脚本
temp/                  ← 运行时缓存 (.gitignore)
tests/                 ← 测试 (.gitignore)
```

根目录散布的 `agents/`, `plugins/`, `profiles/`, `reflect/`, `rules/`, `specs/`, `sche_tasks/`, `bbs_files/`, `config/`, `logs/`, `CLEAR=1/` 需要评估是否可合并。

> ⚠️ `CLEAR=1/` — 这看起来是某个配置错误产生的目录，应确认后删除。

---

## 角色 B：记忆清理师 (Memory Janitor)

**视角**: 记忆系统积累的信息如同神经突触——不用则废，常看则新。需要定期修剪冗余，强化通路。

### 记忆系统中的污垢

#### 1. `.gitignore` 规则膨胀

当前 `memory/*` + 无数 `!memory/xxx` 白名单模式：

```
memory/*
!memory/memory_management_sop.md
!memory/web_setup_sop.md
!memory/autonomous_operation_sop.md
!memory/autonomous_operation_sop/
!memory/autonomous_operation_sop/**
!memory/scheduled_task_sop.md
!memory/L4_raw_sessions/
!memory/L4_raw_sessions/*
!memory/L4_raw_sessions/compress_session.py
!memory/ljqCtrl.py
!memory/ljqCtrl_sop.md
!memory/procmem_scanner.py
!memory/procmem_scanner_sop.md
... (20+ 规则)
```

**问题**: 每添加一个 SOP 都需要改 `.gitignore` + 负规则使 git 性能下降。

**方案**: 改为 `memory/` 整体不忽略，仅忽略敏感/生成文件：
```
memory/
  !memory/L4_raw_sessions/
  !memory/*.db
  !memory/*.zip
```
这样可以追踪所有 SOP 文件而无需白名单。

#### 2. `skills_learning/` 被完全忽略

519KB 的技能案例数据（如 `all_cases.json`）不被 git 追踪。这意味着：
- 跨设备同步时技能丢失
- 间隔重复算法的复习追踪文件也丢失
- 技能学习的"反刍产物"得不到版本控制

**方案**: 至少追踪技能元数据（review_tracker、failure_tracker），案例文件可忽略。

#### 3. temp/model_responses/ 积累

2428KB 的 LLM 响应缓存——这些是"反刍的中间产物"。短期有用，长期废弃。

**方案**: 保留最近 3 天，自动清理 >7 天的。

---

## 角色 C：安全与合规官 (Security & Compliance Officer)

**视角**: 净化不仅是整理，更是消除安全风险——密钥泄露、过度权限、信息暴露。

### 安全隐患

#### 1. `mykey.py` 在 git 追踪中

`mykey.py` 虽在 `.gitignore` 中，但它就在根目录下，且包含 `github_token`、可能的 API keys 等敏感信息。`file_patch` 可以读取它。

**风险**: 任何能执行代码的第三方都能读取密钥。

**方案**: 
- 将密钥移到 `config/secrets/` 目录（双层 `.gitignore`）
- `mykey.py` 只保留环境变量引用 `os.environ.get('GA_GITHUB_TOKEN')`
- 参考 `keychain.py` 的统一密钥管理

#### 2. `.gitignore` 中 `*token*` 和 `*password*` 和 `*secret*`

这些模式可能过于宽泛或不够精确：
- `*token*` 会匹配 `mykey_template.py` 中的 `github_token` 变量名（虽然文件本身不会被忽略，因为已经在 `mykey` 项目中... 实际上变量名不会触发 gitignore）
- 但文件名包含 `token` 的文件都会被忽略——这可能是误伤

**方案**: 审查忽略模式，确保精确覆盖敏感文件路径而非通配符。

#### 3. CI 中 GitHub Token 管理

`git_push.py` 从 `mykey.py` 读取 `github_token`——意味着 token 在宿主机上明文存储。

**方案**: 使用环境变量 + `.env` 文件（已在 `.gitignore` 中），避免在代码中硬编码 token 路径。

#### 4. `memory/L4_raw_sessions/`

10MB+ 的原始会话数据包含所有用户交互历史——高度敏感。

**方案**: 
- 确认其已在 `.gitignore` 中 (`memory/L4_raw_sessions/*`)
- 添加定期清理策略（只保留最近30天）
- 检查 `all_histories.txt`(878KB) 是否包含敏感信息

---

## 综合净化路线图

### 第一阶段：紧急清理（可立即执行，零风险）

```
1. 清理所有 __pycache__ (11629文件 → 0)
2. 清理 temp/ 过期脚本 (*.py)
3. 删除 temp/model_responses/ 中 >7天的
4. 确认 CLEAR=1/ 是误创建 → 删除
```

### 第二阶段：配置净化（需要审查）

```
5. 简化 .gitignore (60+行 → 20行)
   - memory/* → 改为白名单模式
   - skills_learning/ → 追踪元数据
   - 移除冗余 *token* 模式
6. 密钥迁移: mykey.py → config/secrets/ + 环境变量
7. tests/ 从 .gitignore 移除 → 显式忽略 __pycache__
```

### 第三阶段：架构净化（需要决策）

```
8. 根目录瘦身: 评估 agents/plugins/profiles/reflect/
   rules/specs/sche_tasks/bbs_files/logs/CLEAR=1 的去留
9. 建立 temp/ 自动清理机制 (scheduled_task)
10. __pycache__ 清理加入 CI lint 流程
```

### 第四阶段：持续净化（SOP化）

```
11. 编写 `cleanup_sop.md` — 明确清理策略和频率
12. model_responses/ 保留策略: 3天/30天两级
13. L4_raw_sessions 保留策略: 30天轮换
```

---

## 附录：反刍视角的净化

从 `code_and_rumination.md` 的反刍视角：

> **净化不是销毁，是固化的逆过程**。
> 
> 代码反刍将经验固化为 SOP（记忆→代码），
> 项目净化将死代码释放回内存（代码→记忆），
> 两者构成完整的代谢循环。

项目长期不净化的后果就是"代谢废物积累"——`__pycache__` 像神经网络中的无用突触，`temp/` 像细胞代谢废物，`.gitignore` 的负规则像冗余 DNA 片段。

**真正的净化是让系统可以忘记。**
