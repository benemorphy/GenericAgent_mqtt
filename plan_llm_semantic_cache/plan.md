<!-- EXECUTION PROTOCOL
1. file_read(plan.md)，找到第一个 [ ]
2. 执行该步骤
3. file_patch 标记 [ ] -> [Yes]+简要结果
4. 回到步骤1继续
5. 完成所有步骤后回复 __GOAL_COMPLETE__
-->

# LLM 语义缓存实施计划 (方案A+B融合)

**目标**: 本地 LRU 缓存命中率从 0% -> ~25%
**根因**: 当前 key = sha256(messages全文), 每轮hash不同 -> 100% MISS
**方案**: 语义相似度匹配(embedding) + 意图签名提取

## Step 1: 创建 tools/semantic_cache.py

[Yes] 1.1 创建 SemanticCache 类 (V1.0)
    - 方案A(char n-gram embedding + numpy) + 方案B(intent签名) 融合
    - 自动检测 sentence-transformers, 降级到 numpy char-gram
    - 阈值: sentence-transformers=0.88, char-gram=0.70
    - 意图提取正则: 替换路径/行号/代码/数字/时间戳等为@前缀占位符
    - 文件: tools/semantic_cache.py (12KB, 427行)

## Step 2: 集成到 session.py (/ llmcore.py)

[Yes] 2.1 在 session.py 导入 SemanticCache
    - `from tools.semantic_cache import get_semantic_cache`
    - 全局实例: `_SEMANTIC_CACHE = get_semantic_cache()`
    - 防御: 异常时不阻断主流程 (try/except + log.warning)

[Yes] 2.2 修改 _raw_ask, 在精确hash lookup之前加语义查找
    - 在精确 CACHE MISS 前插入 SEM CACHE lookup
    - 使用 `_SEMANTIC_CACHE.lookup(msgs, system, model)`
    - 命中时 yield cached_chunks 并 return
    - 异常安全: try/except/fallback

[Yes] 2.3 在 raw_ask 响应后, 调用 `_SEMANTIC_CACHE.store(...)`
    - 在实际API调用成功后存 (collected 非空时)
    - 异常安全: try/except/log.warning

## Step 3: 更新 cache_monitor.py

[Yes] 3.1 新增语义缓存统计面板
    - PAT_SEM_HIT 正则模式
    - sem_hit 计数器 + get_stats / render 显示
    - 与精确LRU并排显示

## Step 4: 验证测试

[Yes] 4.1 单元测试通过
    - _extract_intent: @fp @n @c @u @d @url @pct @ip @f 占位符正确
    - 相似请求命中 (sim>0.70)
    - 不同意图拒绝 (sim<0.70)
    - LRU淘汰正确 (max_entries)

[~] 4.2 集成测试 (Python模块缓存影响, GA重启后生效)
    - session.py导入正确 (_SEMANTIC_CACHE全局实例)
    - _raw_ask中语义lookup/store逻辑完整
    - 异常安全 (try/except/log.warning)

## Step 5: 基准测试

[~] 5.1-5.3 依赖GA实际运行
    - 模拟测试75%~100%命中率 (同类请求)
    - 重启GA后cache_monitor自动追踪sem:前缀
    - 预期: 相似请求命中率~25%

## 风险控制
- embedding 调用失败 -> 降级到精确hash (不阻断主流程)
- 阈值太低(误匹配) -> 默认0.92, 可根据日志调整
- mempalace_bridge.get_embedding 不存在 -> 记录警告, 跳过语义缓存
