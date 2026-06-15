# GenericAgent 集成 OpenSquilla SquillaRouter 方案

> 分析日期: 2026-06-12  
> 源项目: OpenSquilla v0.3.1 — SquillaRouter (OnnxBGE + V4 Phase3 + CascadeRouter)  
> 目标项目: GenericAgent (D:\\00synchronize\\GenericAgent)

---

## 1. 为什么集成 SquillaRouter？

GenericAgent 当前使用 `mykey.py` 中定义的单一模型（如 `deepseek-v4-flash`）进行所有对话轮次。但这存在几个问题：

- **简单问题浪费资源**：问答/翻译用最强模型，成本高速度慢
- **复杂问题可能不足**：需要深度推理时，轻量模型能力不够
- **无动态切换**：对话中途从简单变复杂（或反之），模型不能自适应

OpenSquilla 的 **SquillaRouter** 解决这些问题的思路：

```
每轮用户输入 → BGE编码(语义) → 特征提取(390维) → LightGBM分类 → 
  c0/c1/c2/c3 路由决策 → 选择对应模型 → 级联降级/升级
```

---

## 2. SquillaRouter 核心架构

### 2.1 路由层级 (Tiers)

来自 `router_tiers.py`：

```
Tier      | 典型模型              | 适用场景
----------|----------------------|--------------------------------
c0 (T0)   | 极轻量模型            | 简单问答、翻译、格式化
c1 (T1)   | 中等模型(deepseek-chat)| 常规对话、信息提取
c2 (T2)   | 强模型+推理           | 复杂推理、代码生成
c3 (T3)   | 最强模型+深度思考      | 数学、科学、高难度分析
```

### 2.2 核心模块

```
squilla_router/
  controller.py       # 后处理: thinking模式/T0-T3, prompt策略P0-P2
  v4_phase3.py        # V4 Phase3 适配器: 加载bundle, 调用推理管线
  models/v4.2_phase3_inference/
    runtime_src/src/router/
      predictor.py    # SquillaRouter + CascadeRouter (主入口)
      bge_onnx.py     # ONNX INT8 BGE 编码器
      v4_features.py  # 390维特征提取 + BGE×3段
      trajectory.py   # 轨迹分类器 (8种对话走向)
      inference/
        core.py       # 推理核心: 特征→LightGBM→MLP→融合
        features.py   # 特征捆绑构建
        heads.py      # 多头推理
        ensemble.py   # 概率融合
        artifacts.py  # 推理工件
        types.py      # 数据类型
```

### 2.3 推理流程 (7层处理)

来自 `predictor.py`：

```
Layer 1: Feature Extraction (390-dim + BGE 1536-dim)
Layer 2: Main model inference (LightGBM → 4-class probs)
Layer 3: Auxiliary model (optional LightGBM for calibration)
Layer 4: MLP calibration (ONNX MLP)
Layer 5: Probability fusion (weighted average)
Layer 6: Post-processing (margin upgrade, flag overrides)
Layer 7: Sticky tier (KV-cache aware,避免频繁切换)
```

---

## 3. 集成方案

### 3.1 需要新增的文件

在 GenericAgent 项目中新增以下文件：

```
squilla_router/
  __init__.py           # 包入口, 暴露 SquillaRouterEngine
  bge_onnx.py           # 从 OpenSquilla 移植 (ONNX INT8 BGE)
  features.py           # 从 OpenSquilla 移植 (特征提取)
  predictor.py          # 从 OpenSquilla 移植 (路由预测)
  controller.py         # 从 OpenSquilla 移植 (后处理)
  router_tiers.py       # 从 OpenSquilla 移植 (层级定义)
  trajectory.py         # 从 OpenSquilla 移植 (轨迹追踪)
  artefacts.py          # 推理工件
  types.py              # 数据类型
  config.py             # 路由配置 (模型映射表)
  cascade_router.py     # 级联路由器 (集成到agent_loop的入口)
```

### 3.2 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `agent_loop.py` | 在 `agent_runner_loop` 的 turn 循环中插入路由决策 |
| `mykey.py` | 增加多模型配置 (c0-c3 各层模型) |
| `ga.py` | 可选: 增加 `--router` 命令行参数 |

### 3.3 核心集成点 — agent_loop.py

现有流程 (agent_loop.py L42-107):
```
agent_runner_loop(client, system_prompt, user_input, handler, tools_schema):
    messages = [system, user]
    while turn < max_turns:
        response = client.chat(messages, tools)   # 固定模型
        ...处理工具调用...
        messages = [user, next_prompt, tool_results]
```

集成后流程:
```
agent_runner_loop(client, system_prompt, user_input, handler, tools_schema, router=None):
    messages = [system, user]
    router_ctx = RouterContext()        # 追踪路由决策历史
    while turn < max_turns:
        if router:
            decision = router.decide(messages, router_ctx)
            client.switch_model(decision.selected_model)
            # 启用/禁用 thinking mode
            if decision.thinking_mode == "T3":
                client.enable_thinking(True)
        response = client.chat(messages, tools)
        router_ctx.update(response)     # 记录本轮结果
        ...处理工具调用...
        messages = [user, next_prompt, tool_results]
```

---

## 4. 代码实现

### 4.1 config.py — 路由配置 + 模型映射

```python
"""SquillaRouter 配置: 模型映射表"""

# Tier → 模型配置映射
# 在 mykey.py 中为每个 tier 配置对应的模型
TIER_MODEL_MAP = {
    "c0": {
        "provider": "native_oai",
        "model": "deepseek-chat",         # 或 gpt-4o-mini
        "max_tokens": 4096,
        "reasoning": False,
    },
    "c1": {
        "provider": "native_oai",
        "model": "deepseek-chat",
        "max_tokens": 8192,
        "reasoning": False,
    },
    "c2": {
        "provider": "native_oai",
        "model": "deepseek-v4-flash",     # GenericAgent 当前模型
        "max_tokens": 16384,
        "reasoning": False,
    },
    "c3": {
        "provider": "native_oai",
        "model": "deepseek-reasoner",     # 或 claude-opus
        "max_tokens": 32768,
        "reasoning": True,                # 启用思维链
    },
}

# BGE 模型路径 (ONNX INT8)
BGE_MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "models/v4.2_phase3_inference/bge_onnx"
)

# LightGBM 模型路径
LGBM_MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "models/v4.2_phase3_inference"
)
```

### 4.2 cascade_router.py — 级联路由器 (核心集成入口)

```python
"""CascadeRouter: 每轮路由决策引擎。

在 agent_loop 的每个 turn 前调用，根据对话上下文
选择最优模型 tier，并支持级联降级/升级。
"""

import os, json
from dataclasses import dataclass, field
from typing import Optional
from .router_tiers import TIER_ORDER, normalize_text_tier
from .predictor import SquillaRouter, CascadeRouter

@dataclass
class RouterContext:
    """路由决策上下文（对话历史追踪）"""
    current_tier: str = "c1"              # 当前 tier
    route_history: list = field(default_factory=list)  # 决策历史
    turn_count: int = 0
    last_assistant_text: Optional[str] = None
    last_usage: Optional[dict] = None

class SquillaRouterEngine:
    """路由引擎 — 对 agent_loop 的唯一入口"""
    
    def __init__(self, bundle_dir: str, config: dict = None):
        self.config = config or {}
        self._router = None
        self._init_router(bundle_dir)
        self.context = RouterContext()
    
    def _init_router(self, bundle_dir: str):
        """初始化 V4 Phase3 路由模型"""
        from .v4_phase3 import V4Phase3Strategy
        self._strategy = V4Phase3Strategy(bundle_dir)
        self._strategy.load()
        self._router = CascadeRouter(self._strategy)
    
    def decide(self, user_text: str, 
               history_texts: list[str] = None,
               prev_assistant: str = None,
               prev_usage: dict = None) -> dict:
        """每轮调用: 输入当前对话上下文, 返回路由决策"""
        result = self._router.predict(
            current_user_text=user_text,
            history_user_texts=history_texts or [],
            prev_assistant_text=prev_assistant,
            prev_assistant_usage=prev_usage,
        )
        
        # 更新上下文
        self.context.current_tier = result.selected_model
        self.context.route_history.append({
            "turn": self.context.turn_count,
            "tier": result.selected_model,
            "thinking": result.thinking_mode,
        })
        self.context.turn_count += 1
        
        return {
            "tier": result.selected_model,
            "thinking_mode": result.thinking_mode,
            "prompt_policy": result.prompt_policy,
            "probabilities": result.probabilities,
        }
    
    def update_context(self, assistant_text: str, usage: dict = None):
        """在 LLM 响应后更新上下文"""
        self.context.last_assistant_text = assistant_text
        self.context.last_usage = usage
```

### 4.3 agent_loop.py 集成修改

在 `agent_runner_loop` 中 (L42-L107)，插入路由决策：

```python
def agent_runner_loop(client, system_prompt, user_input, handler, tools_schema,
                      max_turns=40, verbose=True, initial_user_content=None, 
                      yield_info=False, router_engine=None):
    """原有函数签名增加 router_engine 参数"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user_content or user_input}
    ]
    turn = 0; handler.max_turns = max_turns
    _hook('agent_before', locals())
    
    while turn < handler.max_turns:
        turn += 1
        
        # ===== 路由决策: 每轮选择最佳模型 =====
        if router_engine:
            # 提取当前用户输入和上下文
            current_user = messages[-1].get('content', '') if messages else ''
            history = [m.get('content','') for m in messages[:-1] if m.get('role')=='user']
            prev_asst = router_engine.context.last_assistant_text
            
            decision = router_engine.decide(
                user_text=str(current_user)[:2000],
                history_texts=[str(h)[:500] for h in history[-3:]],
                prev_assistant=str(prev_asst)[:2000] if prev_asst else None,
            )
            
            # 切换模型
            tier = decision['tier']
            model_cfg = TIER_MODEL_MAP.get(tier, TIER_MODEL_MAP['c1'])
            client.switch_model(model_cfg['model'])
            
            # 设置推理模式
            if decision['thinking_mode'] in ('T2', 'T3'):
                client.enable_reasoning(True)
            else:
                client.enable_reasoning(False)
        
        turnstr = f'LLM Running (Turn {turn}) ...'
        if router_engine:
            turnstr += f' [Tier: {decision["tier"]}]'
        ...
        
        # LLM 调用 (原有)
        response_gen = client.chat(messages=messages, tools=tools_schema)
        ...
        
        # ===== 路由反馈: 记录响应 =====
        if router_engine and response:
            router_engine.update_context(
                assistant_text=response.content if hasattr(response, 'content') else '',
                usage=getattr(response, 'usage', None)
            )
```

### 4.4 mykey.py 多模型配置

在 `mykey.py` 中增加多级模型配置：

```python
# ── SquillaRouter 多级模型配置 ──
router_model_config = {
    "c0": {
        "name": "deepseek-chat",
        "apikey": _api_key,
        "apibase": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_mode": "chat_completions",
        "max_tokens": 4096,
        "context_win": 64000,
    },
    "c1": {
        "name": "deepseek-chat",
        "apikey": _api_key,
        "apibase": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_mode": "chat_completions",
        "max_tokens": 8192,
        "context_win": 128000,
    },
    "c2": {
        "name": "deepseek-v4-flash",        # 当前在用
        "apikey": _api_key,
        "apibase": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash",
        "api_mode": "chat_completions",
        "max_tokens": 16384,
        "context_win": 300000,
    },
    "c3": {
        "name": "deepseek-reasoner",         # 深度推理模型
        "apikey": _api_key,
        "apibase": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "api_mode": "chat_completions",
        "max_tokens": 32768,
        "context_win": 300000,
    },
}
```

---

## 5. 先决条件 (依赖安装)

使用 `uv pip install` 安装 SquillaRouter 所需依赖：

```bash
# ONNX 运行时
uv pip install onnxruntime>=1.15

# LightGBM
uv pip install lightgbm>=4.0

# BGE 编码
uv pip install tokenizers>=0.15

# 科学计算
uv pip install numpy>=1.24 scikit-learn>=1.3

# 可选: 句子转换器 (如不使用 ONNX BGE)
uv pip install sentence-transformers>=2.2
```

---

## 6. V4 Phase3 模型文件

OpenSquilla 中 `squilla_router/models/v4.2_phase3_inference/` 包含:

```
models/v4.2_phase3_inference/
  bge_onnx/                   # ONNX INT8 BGE 模型
    config.json
    tokenizer.json
    model.onnx
  features/                    # 特征器
  mlp/                         # MLP 校准
    scaler.pkl
    model.onnx
  runtime_src/                 # Python 运行时源码
  router.runtime.yaml          # 运行时配置
  main_lightgbm.txt            # 主 LightGBM 模型
  aux_lightgbm.txt             # 辅助 LightGBM 模型
```

这些模型文件需要从 OpenSquilla 复制到 GenericAgent 中。

---

## 7. 集成步骤 (分阶段实施)

### Phase 1: 基础结构 (1-2小时)
1. 创建 `squilla_router/` 包目录
2. 复制运行时源码 (predictor, bge_onnx, v4_features, trajectory, controller, types)
3. 复制模型文件 (bge_onnx, lightgbm, mlp)
4. 创建 `config.py` 和 `cascade_router.py`

### Phase 2: agent_loop 集成 (1小时)
1. 修改 `agent_runner_loop` 增加 `router_engine` 参数
2. 在 turn 循环开始前插入路由决策
3. 在 turn 循环结束后更新路由上下文
4. 在 llmcore.py 中增加 `switch_model()` 方法

### Phase 3: 模型层适配 (1-2小时)
1. 修改 `llmcore.py` 的 Session 类:
   - 增加 `switch_model(name)` 方法
   - 增加 `enable_reasoning(flag)` 方法
   - 确保不同 tier 的 model 用同一 API key 和 base

### Phase 4: 验证与调优 (2小时)
1. 测试简单对话 (应落到 c0/c1)
2. 测试复杂推理 (应升到 c2/c3)
3. 查看路由日志，调优阈值
4. A/B 对比: 有路由 vs 无路由的 token 节省

---

## 8. 路由决策可视化 (调试工具)

```python
def router_debug_view(decision: dict) -> str:
    """调试用: 显示路由决策详情"""
    probs = decision.get('probabilities', {})
    return f'''
[SquillaRouter Decision]
  Tier: {decision['tier']}
  Thinking: {decision['thinking_mode']}
  Prompt Policy: {decision['prompt_policy']}
  Probabilities:
    c0: {probs.get('c0', 0):.3f}
    c1: {probs.get('c1', 0):.3f}
    c2: {probs.get('c2', 0):.3f}
    c3: {probs.get('c3', 0):.3f}
'''
```

---

## 9. 预期效果

| 指标 | 当前(无路由) | 集成后(有路由) |
|------|------------|--------------|
| 简单问答速度 | 一般 | 快 2-3x (走 c0/c1 轻量模型) |
| 复杂推理质量 | 固定模型 | 可自动升级到 c3 推理模型 |
| token 成本 | 全量 | 预计节省 40-60% |
| 对话体验 | 无感 | 首次调用有 ~100ms 路由延迟 |

---

> 本文档基于 OpenSquilla v0.3.1 SquillaRouter 源码分析生成  
> 分析工具: CodeGraph (30685 nodes, 75343 edges)  
> 版本: 2026-06-12
