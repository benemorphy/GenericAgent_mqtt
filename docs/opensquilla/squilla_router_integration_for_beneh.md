# Beneh 集成 SquillaRouter 方案

> 分析日期: 2026-06-12  
> 源项目: OpenSquilla v0.3.1 SquillaRouter + D:\00synchronize\GenericAgent (已验证)  
> 目标项目: Beneh/GA/ (D:\open_claw_agent\Beneh\GA)

---

## 1. 背景

Beneh/GA 是 GenericAgent 的复刻版，当前`agent_loop.py`/`llmcore.py`/`agentmain.py`均为**原始未修改版本**。  
SquillaRouter 已在 `D:\00synchronize\GenericAgent` 集成验证成功（`temp/router_log.jsonl` 有 9 条路由决策记录）。

## 2. 移植内容

从已验证的 GenericAgent 复制以下改动到 Beneh/GA：

### 2.1 新增：squilla_router/ 包 (37 文件, 91KB)

```
GA/squilla_router/
├── __init__.py                  # 包导出
├── config.py                    # Tier模型映射 (c0-c3)
├── cascade_router.py            # 级联路由引擎入口 + 埋点日志
├── router_tiers.py              # Tier标识符适配层
├── v4_phase3.py                 # V4 Phase3适配器
├── controller.py                # 推理模式/提示策略
├── runtime_src/                 # 完整推理管线源码 (15文件)
│   ├── predictor.py             # LightGBM+MLP融合预测
│   ├── bge_onnx.py              # ONNX BGE编码器
│   ├── v4_features.py           # 390维特征提取
│   ├── trajectory.py            # 轨迹追踪
│   └── inference/               # 推理核心
└── models/v4_bundle/            # 模型文件 (75MB, 20文件)
    ├── bge_onnx/                # BGE ONNX模型
    ├── features/                # 特征提取配置
    ├── mlp/                     # MLP模型
    ├── lgbm_main.bin            # LightGBM主模型
    └── lgbm_aux.bin             # LightGBM辅助模型
```

### 2.2 修改：agent_loop.py (3处)

| 位置 | 改动 | 效果 |
|------|------|------|
| 文件开头 | 添加 `_init_router()` 函数 + `_ROUTER`/`_ROUTER_ENABLED` 全局变量 | 按需初始化路由引擎 |
| agent_runner_loop 入口 | 调用 `_init_router()` | 每轮开始时准备路由 |
| 每次 LLM 调用前 | 插入 `route_decision()` 决策块 + `switch_model()` | 自动选模型、切换、输出埋点 |

### 2.3 修改：llmcore.py (2处)

| 位置 | 改动 | 效果 |
|------|------|------|
| BaseSession.__init__ | 添加 `self._tier` + `self.user_agent` (防止误删) | 记录当前路由层级 |
| BaseSession 类 | 添加 `switch_model()`/`switch_tier()` 方法 | 热切换模型 |
| NativeToolClient 类 | 添加 `model` 属性 + `switch_model()`/`switch_tier()` 代理 | 代理到 backend |

### 2.4 修改：agentmain.py (2处)

| 位置 | 改动 | 效果 |
|------|------|------|
| load_llm_sessions | MixinSession 失败后清理失效条目 | 避免空 session 列表 |
| load_llm_sessions | 空session保护 (`if not self.llmclients: self.llmclient = None`) | 避免除零错误 |

## 3. 移植操作

### Phase 1: 复制 squilla_router 包

```bash
# 从已验证的 GenericAgent 复制
xcopy /E D:\00synchronize\GenericAgent\squilla_router D:\open_claw_agent\Beneh\GA\squilla_router\
```

### Phase 2: 修改 agent_loop.py

将 `D:\00synchronize\GenericAgent\agent_loop.py` 的路由集成部分移植

### Phase 3: 修改 llmcore.py

添加 `switch_model()`/`switch_tier()` 方法到 `BaseSession`，  
添加 `model`/`switch_model()`/`switch_tier()` 到 `NativeToolClient`

### Phase 4: 修改 agentmain.py

添加 MixinSession 失败清理 + 空 session 保护

## 4. 预期效果

| 输入长度 | 路由层级 | 模型 |
|---------|---------|------|
| <=50字 | c0 | deepseek-chat |
| 50-400字 | c1 | deepseek-chat |
| 400-800字 | c2 | deepseek-v4-flash |
| >800字 | c3 | deepseek-reasoner |

## 5. 埋点

- 终端实时: `[Router] old_model -> new_model (tier=..., traj=..., ...ms)`
- 持久化: `GA/temp/router_log.jsonl`

## 6. 注意

- 确保 Beneh/GA/ 的 mykey.py 中的 mixin_config 已注释或 fix `llm_nos` 为整数索引
- 模型文件复制需要约 75MB 磁盘空间
- 需要安装依赖: `pip install onnxruntime lightgbm scikit-learn tokenizers structlog`
