# LLM Provider → 工厂 可行性评估报告

评估日期：2026-05-21
评估范围：llmcore.py (994行) → tools/llm_providers/

## 当前架构快照

llmcore.py: 994 行，内含：

| 类别 | 内容 | 可移出行数估算 |
|------|------|:------------:|
| Provider Session 类 | NativeClaudeSession(L592), NativeOAISession(L636), LLMSession(L703) | ~150 |
| Tool Client 类 | ToolClient(L703), NativeToolClient(L931) | ~130 |
| 多Provider路由器 | MixinSession(L859, 含fallback+spring-back逻辑) | ~60 |
| Provider专属函数 | _parse_claude_sse/json, _parse_openai_sse/json, _msgs_claude2oai, _apply_claude_thinking | ~250 |
| 共享基础层 | BaseSession, _raw_api_post, _fix_messages, reload_mykeys, resolve_session, resolve_client | 留在llmcore |
| **总计可移出** | | **~550行 (55%)** |

## 已有基础

resolve_session() 已经是一个 mini 工厂：

```python
def resolve_session(cfg_name):
    if 'native' in cfg_name:
        return NativeClaudeSession if 'claude' else NativeOAISession
    if 'claude' in cfg_name: return ClaudeSession
    return LLMSession if 'oai' in cfg_name else None
```

mykey.py 的配置命名约定（native_claude_v2, claude_v2, openai_oai）已经隐含 Provider 类型标识。

## 风险分析

| 风险维度 | 评级 | 具体原因 |
|----------|:----:|---------|
| 修改量 | 最高 | 550行迁移，跨越6个文件 |
| SSE解析 | 高 | 流式解析与线程安全紧密耦合于 _raw_api_post |
| 消息转换 | 高 | _msgs_claude2oai/openai_tools_to_claude 的格式转换错误直接导致 API 400 |
| MixinSession | 中高 | fallback逻辑依赖 Native/非Native 分组判断 |
| 认证流 | 中 | NativeClaudeSession 的特殊请求头等 |

## 鲁棒性收益

| 场景 | 当前 | 工厂化后 |
|------|------|---------|
| OpenAI API断连 | Agent完全不可用 | 自动fallback到Claude / 可配置降级 |
| 新增Gemini Provider | 改llmcore.py | 写一个 gemini.py 实现接口即可 |
| Claude API超时 | MixinSession硬编码fallback链 | 工厂管理的Provider池 |

## 实施路径（4 阶段）

### Phase 1: ProviderProtocol + ProviderRegistry（零风险）
- 定义抽象接口 ProviderProtocol
- 实现 ProviderRegistry 注册表
- 将现有 resolve_session 包装为注册表调用
- **测试：resolve_session 行为零差异**

### Phase 2: 提取 Claude Native（中等风险）
- 将 NativeClaudeSession + Claude专属SSE解析移到 claude.py
- 在 claude.py 中实现 ClaudeProvider 类，注册到 Registry
- **测试：native_claude_v2 会话行为完全一致**

### Phase 3: 提取 Open AI 和 LLMSession（中等风险）
- 移动到 openai.py 和 generic.py
- **测试：全部 resolve_session 路径行为一致**

### Phase 4: 替换 resolve_session 核心（低风险）
- resolve_session 内部改为 ProviderRegistry.create
- 移除硬编码分支

## 可行性评分：7/10

| 维度 | 评分 | 说明 |
|------|:---:|------|
| 技术可行性 | 8/10 | 已有 resolve_session 雏形 |
| 隔离度 | 6/10 | SSE解析与 _raw_api_post 的协程/线程耦合 |
| 回滚难度 | 5/10 | 55%代码迁移 |
| 增量价值 | 9/10 | 新增 Provider 零修改核心文件 |
| **综合** | **7/10** | 值得做，必须分阶段、每阶段独立测试 |
