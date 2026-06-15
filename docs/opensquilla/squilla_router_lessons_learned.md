# SquillaRouter 集成经验教训

> 源自: GenericAgent 集成 OpenSquilla SquillaRouter 实战  
> 日期: 2026-06-12

---

## 1. file_patch 多行替换会静默删行

在 BaseSession.__init__ 中添加 self._tier 属性时，旧文本块覆盖不完整导致 self.user_agent 行被静默删除。AttributeError 被 except:pass 吞掉，排查了数轮才发现。

**教训**: file_patch 的旧文本块必须完整覆盖目标区间的每一行。少一行→匹配失败，多行间隔→中间行被删。

## 2. except:pass 吞掉所有错误

agentmain.py 的 `load_llm_sessions()` 中:
```python
try:
    resolve_client(k)
except:
    pass
```
NativeOAISession 缺属性的 AttributeError 被静默吞掉，用户只看到 "Please set mykey.py!"。

**教训**: 排查空 session 问题时应先临时去掉 except:pass 暴露真实错误。见 Rule 17。

## 3. 包装类需要暴露代理属性

NativeToolClient 包装 Session，但 `.model` 和 `.switch_model()` 未暴露。路由集成需要：
- `@property model` → `self.backend.model`
- `switch_model()` → `self.backend.switch_model()`

## 4. 跨项目移植的 import 依赖涟漪

复制 OpenSquilla 源码到 GenericAgent 时，多处存在 `from opensquilla.xxx` 引用。逐个修复了 3 个文件 5 处 import。

**教训**: 复制后应先 `grep 'from opensquilla' -r` 一次性修复所有引用。

## 5. 模型文件路径约定需同步

OpenSquilla 模型目录名 `v4.2_phase3_inference`，GenericAgent 用 `v4_bundle`。`default_bundle_dir()` 必须同步修改。

## 6. MixinSession 配置隐式依赖

`llm_nos: ['deepseek-v4-flash']` 要求 session 的 `backend.name` 匹配字符串。不匹配时 StopIteration 被吞。

**教训**: `llm_nos` 应当使用整数索引 [0] 而非字符串名称。

## 7. CodeGraph 调试效率

用 CodeGraph DB 查调用链和类定义，比逐行读文件快 10 倍。
