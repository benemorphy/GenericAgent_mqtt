# mykey → 配置服务：实现可行性分析报告

**分析日期**: 2026-05-21  
**依据文档**: `docs/decoupling_priority.md`(#8), `docs/decoupling_analysis.md`(§11), `docs/decoupling_risk_assessment.md`, `docs/decoupling_robustness_eval.md`

---

## 一、现状全景

### 1.1 当前架构（4文件 ~1154行）

```
mykey.py (476行)          ← 主配置模板，用户填入 API key + 模型配置
mykey_internet.py (480行)  ← 外网部署配置（DeepSeek V4 Flash）
mykey_inner.py (122行)     ← 内网部署配置（本地 llama-server :8080）
mykey_inner_vlm.py (76行)  ← 内网 VLM 部署配置（本地 VLM :8090）
                                └── switch_mykey.ps1 用文件复制切换
```

### 1.2 当前加载链路（耦合点）

```
[加载时]
llmcore.py:_load_mykeys()
  ├─ import mykey; importlib.reload(mykey)   ← 模块级 import，语法错误→全死
  └─ 或: json.load('mykey.json')             ← fallback

[运行时 hot-reload]
llmcore.py:reload_mykeys()
  ├─ stat mtime → importlib.reload(mykey)    ← 每次检查文件时间
  └─ globals().update(mykeys=mk)             ← 全局变量注入

[消费者]
├─ llmcore.py:resolve_session()     → reload_mykeys()[0].get(cfg_name)
├─ agentmain.py:load_llm_sessions() → reload_mykeys() → 遍历 mykeys items
├─ git_push.py                      → from mykey import github_token     ← 直接 import!
├─ vision_api.py                    → import mykey                       ← 直接 import!
├─ engine.py (skill_learn)          → import mykey; getattr(mykey, ...)  ← 直接 import!
├─ langfuse_tracing.py              → from llmcore import _load_mykeys   ← 内部函数泄漏
└─ onebot_config.py                 → from llmcore import mykeys
```

### 1.3 关键痛点

| 痛点 | 严重程度 | 说明 |
|------|---------|------|
| **配置即 Python 代码** | 致命 | mykey.py 语法错误→Agent 无法启动 |
| **直接 import 散布** | 致命 | 6 处直接 `import mykey`，牵一发动全身 |
| **配置切换靠文件复制** | 中 | switch_mykey.ps1 用 `Copy-Item` 覆盖 mykey.py |
| **密钥与配置混存** | 中 | API key + 模型 endpoint + 平台 token 全在一个文件 |
| **无验证层** | 中 | Malformed 配置→运行时崩溃（无 schema 校验） |
| **无 fallback 机制** | 致命 | 配置缺失→ValueError/AttributeError→不可恢复 |

---

## 二、目标设计

### 2.1 配置服务接口（建议）

```python
# tools/config_service.py

class ConfigService:
    """统一配置服务 — 替代 mykey.py 的直接模块导入
    
    - 单例模式，全局一个实例
    - 支持 profile 切换（inner/internet/inner_vlm）
    - 支持运行时热加载 + 事件通知
    - 支持 fallback 默认值 + 类型校验
    """

    @classmethod
    def init(cls, profile: str = 'internet') -> bool:
        """初始化配置服务，加载指定 profile"""

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """安全读取配置项，不存在则返回 default"""

    @classmethod
    def get_model_config(cls, name: str) -> dict | None:
        """获取 LLM 模型配置（供 ProviderRegistry 使用）"""

    @classmethod
    def reload(cls) -> bool:
        """重新加载配置（保留现有引用的向后兼容）"""

    @classmethod
    def watch(cls, callback: Callable) -> None:
        """注册配置变更回调"""
```

### 2.2 Profile 配置源（向后兼容）

```
profiles/
  internet.py      ← 当前 mykey_internet.py 迁移而来
  inner.py         ← 当前 mykey_inner.py 迁移而来
  inner_vlm.py     ← 当前 mykey_inner_vlm.py 迁移而来
  
# 仍保留 mykey.py 作为自定义配置入口（非 profile 模式）
```

---

## 三、可行性评估

### 3.1 依赖关系 ✅ 前置条件已满足

| 前置依赖 | 状态 | 说明 |
|---------|------|------|
| #5 LLM Provider → 工厂 | **已完成** | `tools/llm_providers/` 中的 ProviderRegistry 已就绪 |
| ProviderRegistry.create(cfg_name, cfg) | **可用** | 只需 `cfg` 来源从 mykey 改为 ConfigService |

### 3.2 实现工作量评估

| 模块 | 改动类型 | 预估行数 | 风险 |
|------|---------|---------|------|
| **新建** `tools/config_service.py` | 新增 | ~200 行 | 低（新文件，不影响现有） |
| **改造** `llmcore.py:_load_mykeys/reload_mykeys` | 重构 | ~30 行 | 高（核心路径） |
| **改造** `llmcore.py:resolve_session` | 替换 | ~3 行 | 中（cfg 来源切换） |
| **改造** `agentmain.py:load_llm_sessions` | 替换 | ~5 行 | 中（入口点） |
| **改造** `scripts/git_push.py` | 替换 import | ~3 行 | 低 |
| **改造** `memory/vision_api.py` | 替换 import | ~3 行 | 低 |
| **改造** `tools/skill_learn.../engine.py` | 替换 import | ~3 行 | 低 |
| **改造** `plugins/langfuse_tracing.py` | 替换 import | ~3 行 | 低 |
| **改造** `temp/onebot_qq/src/onebot_config.py` | 替换 import | ~3 行 | 低 |
| **改造/废弃** `switch_mykey.ps1` | 新增 API | ~20 行 | 低（有新接口后可选） |
| **配置迁移** mykey_internet.py → profiles/ | 复制+重命名 | ~0 行 | 低 |
| **总计** | | **~270 行** | |

### 3.3 3 阶段实施路径

```
Phase 1 — 核心服务（安全隔离层）
  ├─ 创建 tools/config_service.py（单例 + get/reload/watch API）
  ├─ 改造 llmcore.py 的 _load_mykeys/reload_mykeys（内部改用 ConfigService）
  └─ 改造 resolve_session（cfg 来源切换）
  → 验证: Agent 正常启动、热加载正常、Provider 创建正常

Phase 2 — 消费者迁移（消除直接 import）
  ├─ git_push.py: from mykey import X → ConfigService.get('X')
  ├─ vision_api.py: import mykey → ConfigService.get(...)
  ├─ skill_learn engine.py: getattr(mykey, ...) → ConfigService.get(...)
  ├─ langfuse_tracing.py: _load_mykeys → ConfigService.get(...)
  └─ onebot_config.py: from llmcore import mykeys → ConfigService.get(...)
  → 验证: git push 正常、OCR 正常、技能学习正常

Phase 3 — Profile 系统（替代 switch_mykey.ps1）
  ├─ 创建 profiles/ 目录，迁移 mykey_internet/inner/inner_vlm 为 profile 文件
  ├─ ConfigService.init(profile='internet') 接口
  └─ 废弃 switch_mykey.ps1（或改为调用 ConfigService API）
  → 验证: 通过代码切换配置，无需文件复制
```

### 3.4 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| **llmcore.py 改造导致启动失败** | 中 | 致命 | Phase 1 保留旧 `reload_mykeys()` 作为 fallback + 并行测试 |
| **直接 import 遗漏** | 高 | 中 | 用 `grep -r "import mykey"` 做最终审计 |
| **热加载语义变化** | 中 | 中 | 保持 mtime 检查 + `__getattr__` PEP 562 兜底 |
| **密钥泄露** | 低 | 致命 | ConfigService 不记录明文日志、不 dump 配置内容 |
| **profile 切换时 session 重建** | 中 | 中 | agentmain.py 中 `load_llm_sessions()` 已支持 changed 检测 |

---

## 四、与已完成的 #5（Provider 工厂）的集成分析

当前 `resolve_session()` 位于 `llmcore.py:784`：

```python
def resolve_session(cfg_name):
    from tools.llm_providers import ProviderRegistry
    cfg = reload_mykeys()[0].get(cfg_name)    # ← 这里直接调用 mykey 加载
    if not cfg: raise ValueError(...)
    return ProviderRegistry.create(cfg_name, cfg)
```

**改造后**：

```python
def resolve_session(cfg_name):
    from tools.config_service import ConfigService
    cfg = ConfigService.get_model_config(cfg_name)  # ← 通过配置服务
    if not cfg: raise ValueError(...)
    return ProviderRegistry.create(cfg_name, cfg)
```

集成点仅 1 行代码，**零架构摩擦**。ProviderRegistry 已经设计为接收 `(cfg_name, cfg)` dict，ConfigService 只需提供同样的 dict 格式即可。

---

## 五、结论：可行，建议排入下一个执行批次

### 关键判断矩阵

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术可行性** | 5/5 | 架构变动小（~270 行），核心是抽象层而非重写 |
| **前置依赖** | 5/5 | #5 Provider 工厂已就绪，可直接使用 |
| **风险可控性** | 4/5 | Phase 1 可保留完整向后兼容，支持逐步迁移 |
| **收益/努力比** | 5/5 | 消除 6 处直接耦合 + 实现 profile 管理 + 故障隔离 |
| **回滚难度** | 3/5 | 高风险在 llmcore.py，但 Phase 1 可保留旧接口做 fallback |

### 建议执行顺序

```
立即开始 → Phase 1（核心服务, 1-2 天）
           ↓
           Phase 2（消费者迁移, 0.5 天）
           ↓
           Phase 3（Profile 系统, 0.5 天）
```

**总预估工作量**: 2-3 天  
**总代码变更**: ~270 行新增 + ~50 行改造（分布在 8 个文件）  
**最大单点风险**: `llmcore.py` 中 `_load_mykeys()` → `ConfigService.get()` 的切换

---

### 风险最终评价

根据 `docs/decoupling_risk_assessment.md` 的原评级（高风险），**实际可控性高于预期**，原因：

1. #5 Provider 工厂的完成显著降低了 llmcore.py 的耦合度
2. ConfigService 可以包装现有 `reload_mykeys()` 逻辑，而非替换它
3. 大部分消费者（git_push.py、vision_api.py 等）是非关键路径，改出问题不影响 Agent 核心循环
4. Phase 1 可以保留 `reload_mykeys()` 作为内部实现，外部只暴露 `ConfigService` 接口

**综合结论**: **强烈建议实施**，优先排入下一个执行批次（在 Batch 5 高风险改造中排第一）。
