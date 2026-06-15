# Search Skills SOP - 搜索技能通用指南

> 来源: Metaso + skills.sh (find-skills, firecrawl-search) + best practices

## 可用的搜索工具

| 工具 | 方式 | 适用场景 |
|------|------|---------|
| **MemPalace 语义搜索** | `from memory.mempalace_bridge import semantic_search; semantic_search(query, n_results=5)` | **本地记忆语义搜索优先** — 语义向量模糊匹配记忆文件（2526抽屉/6房间），无需关键词精确匹配 |
| **Metaso API** | `metaso_search(keyword, size=5)` | 技术文档/知识搜索，中文优先 |
| **Local (es.exe)** | `from tools.file_search import es_search; es_search(pattern, max_results=10)` | 本地文件全盘搜索，~54ms，依赖 Everything 服务 |
| **Bing 浏览器** | `web_execute_js` 打开 bing.com 搜索 | 备用搜索，无API密钥时 |
| **skills.sh** | `requests.get(skills.sh)` | 查找可安装的 agent skill |
| **Firecrawl** | `firecrawl-search` | Web 内容深度抓取和搜索 |

## 搜索策略（按优先级排序）

1. **MemPalace 语义搜索优先** — 先查本地记忆语义搜索，能模糊匹配已知事实
   - 参数: query, n_results=1-20
   - 返回: source, room, cosine score, content preview
   - 适用: 本地 SOP/知识检索，模糊查询已知事实

2. **Metaso API 次选** — 有API key时，用 `metaso_search` 搜索
   - 参数: keyword, scope=(webpage/news/academic), size=1-20
   - 返回: title, url, snippet, score
   - 适用: 技术问题、文档查找、知识检索

3. **skills.sh 搜索技能** — 查找可安装的 agent skill
   - `find-skills` skill: 帮助用户发现技能
   - 遍历 skills.sh 页面链接，关键词匹配

4. **Bing 浏览器兜底** — 启用 CDP 浏览器后
   - 打开 bing.com → 搜索关键词 → scan 结果
   - 适用于 Metaso 不返回结果时

## 搜索查询优化规则

- **中文优先**: 先中文关键词，无结果再换英文
- **site: 限定**: 用 `site:github.com` 等限定来源
- **重试策略**: 首次无结果 → 改写查询词 → 换搜索源
- **精简关键词**: 去除停用词，保留核心术语
- **多角度**: 同义替换 + 不同措辞

## 典型搜索流程

```
问题 → 提炼关键词 → MemPalace 语义搜索（本地）
  ├─ 有结果 → 打开文件核实 → 提取所需信息
  └─ 无结果 → 换 Metaso 搜索
              └─ 仍无 → Bing 浏览器兜底
```

## MemPalace 使用注意

- 语义搜索不依赖关键词精确匹配，适合模糊查询
- 桥接模块: `from memory.mempalace_bridge import semantic_search`
- Palace 状态: 2526 drawers, 6 rooms (l4_raw_sessions, general, inspirations, autonomous_operation_sop, learning_log, skill_search)
- 首次查询可能因加载 ONNX 模型稍慢（~2s），后续查询 < 500ms

## Metaso 使用注意

- API Key 从 keychain 读取: `keys.metaso_api_key.use()`
- 未配置 key 时需请求用户提供
- scope 参数: webpage(默认) / news / academic
- 返回结果最多20条，默认5条
- 搜索前先查 memory 中的 SOP，避免重复搜索已知内容
