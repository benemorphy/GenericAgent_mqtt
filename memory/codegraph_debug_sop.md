---
skill: codegraph_debug
domain: code-analysis
version: "1.0"
tags: [codegraph, debug, call-chain, call-tree, methodology]
cc_quick: "CodeGraph调用链Debug五步法 — grep→调用树思维转换"
cc_keywords: ["CodeGraph", "debug", "调用链", "调用树", "callers", "callees", "impact"]
---

# CodeGraph 调用链 Debug 五步法

## 0. 核心思维转换

```
旧习惯（不要）                   新习惯（要做）
─────────────────────────       ─────────────────────────
看到报错 → code_run(grep)       看到报错 → codegraph_search(符号)
追踪调用 → file_read + 手动追    追踪调用 → callers(上游) + callees(下游)
评估影响 → 脑补推理              评估影响 → impact(影响分析)
```

**核心原则**: 不读源码先查图。CodeGraph 已经索引了 319 文件 / 6238 节点 / 11498 边，**查图比读代码快 10 倍**。

---

## 1. 五步法总览

| 步骤 | 工具 | 解决的问题 | 耗时 |
|------|------|-----------|------|
| STEP 1: 错误定位 | `codegraph_search` | 报错符号/关键词在哪个文件、哪一行 | 1 次调用 |
| STEP 2: 上游追踪 | `codegraph_callers` | 谁调用了这个函数？（调用链 - 向上追溯） | 1 次调用 |
| STEP 3: 下游展开 | `codegraph_callees` | 这个函数调用了什么？（调用树 - 向下展开） | 1 次调用 |
| STEP 4: 影响分析 | `codegraph_impact` | 改了这里会影响什么？ | 1 次调用 |
| STEP 5: 文件直达 | `codegraph_files` | 改完后的结构检查 | 1 次调用 |

**总调用次数: 5 次 = 5 秒，获得完整的调用图全景。**

---

## 2. 详细操作指南

### STEP 1: 错误定位 — codegraph_search

当遇到报错时，提取报错信息中的**关键符号（函数名/变量名/类名）**，直接搜索：

```python
codegraph_call("codegraph_search", {"query": "报错函数名"})
```

**示例**: 搜索 `format_error`
```
结果: format_error
  文件: ga_utils.py:13
  类型: function
```

### STEP 2: 上游追踪 — codegraph_callers

找到符号后，查**谁调用了它** —— 生成调用链（向上追溯）

```python
codegraph_call("codegraph_callers", {"symbol": "函数名"})
```

**示例**: `callers(main)`
```
调用者: __main__.py (入口)
         launcher_mqtt.py
         conductor.py
```

### STEP 3: 下游展开 — codegraph_callees

查**这个函数调用了什么** —— 生成调用树（向下展开）

```python
codegraph_call("codegraph_callees", {"symbol": "函数名"})
```

**示例**: `callees(某函数)`
```
被调用:
   sub_func_a (line 42)
   sub_func_b (line 78)
   helper util (line 120)
```

### STEP 4: 影响分析 — codegraph_impact

当需要修改代码时，先评估**影响范围**

```python
codegraph_call("codegraph_impact", {"symbol": "待修改函数/文件名"})
```

**示例**: `impact(agentmain)`
```
受影响: 16 节点 / 8 条边
   - conductor.py:31 (import agentmain)
   - genericagent_acp_bridge.py (import agentmain)
   - qtapp.py (import agentmain)
   ...
```

### STEP 5: 结构确认 — codegraph_files

改完后，检查文件结构：

```python
codegraph_call("codegraph_files")
```

---

## 3. 实际 Debug 案例对比

### 场景: 某个 Python import 报错 `ModuleNotFoundError`

**旧方法（grep 流）**:
```
第1步: code_run("grep -r 'agentmain' *.py")          # 搜索引用
第2步: file_read("agentmain.py")                      # 读源码找 import
第3步: code_run("grep -r 'main()' *.py")              # 找调用点
第4步: 手动拼凑...                                      # 脑补调用关系
结果: 4-5轮工具调用，30秒+
```

**新方法（CodeGraph 流）**:
```
第1步: codegraph_search(query="agentmain")             # 找到符号位置
第2步: codegraph_callers(symbol="main")                 # 谁调了main
第3步: codegraph_impact(symbol="agentmain")             # 改agentmain影响谁
结果: 3次工具调用，3秒
```

### 输出对比

| 维度 | grep 流 | CodeGraph 流 |
|------|---------|-------------|
| 调用链完整性 | 需手动拼凑（易遗漏） | 自动生成（11498边全覆盖） |
| 跨文件关系 | 逐文件 grep 串接 | 全项目图遍历 |
| 影响范围 | 靠经验推测 | 精确到行号 |
| 耗时 | 30s-2min | 3-5秒 |

---

## 4. 工具调用速查表

| 你需要 | 调用 |
|--------|------|
| 搜索报错符号 | `codegraph_call("codegraph_search", {"query": "符号名/关键词"})` |
| 查谁调了我 | `codegraph_call("codegraph_callers", {"symbol": "函数名"})` |
| 查我调了谁 | `codegraph_call("codegraph_callees", {"symbol": "函数名"})` |
| 改这影响谁 | `codegraph_call("codegraph_impact", {"symbol": "文件名/符号名"})` |
| 项目总览 | `codegraph_call("codegraph_status")` |
| 文件列表 | `codegraph_call("codegraph_files")` |

---

## 5. 已知坑

1. **callees 可能返回空**: 如果函数调用的是动态导入或 C 扩展，CodeGraph 无法追踪。此时回退到 `file_read` + 正则搜索。
2. **索引需要同步**: 代码变更后运行 `codegraph sync` 更新索引，否则查到的是旧调用关系。
3. **符号名要精确**: `callers("main")` 可能匹配多个文件中的 `main`，用 `codegraph_search` 先确认精确符号。
4. **跨文件 import**: CodeGraph 能追踪 `from X import Y`，但对 `importlib.import_module()` 动态导入无能为力。

---

## 6. 预期效果

采用本 SOP 后，debug 流程应为:

```
报错 → codegraph_search(报错符号) → caller(看调用链路)
     → callee(看内部调用) → impact(看修改影响)
     → 定位到具体行 → file_read 确认 → 修复
```

**关键指标**: 80% 的 debug 场景应在 3 次 codegraph 调用内定位到根因，不再需要手动 grep 拼凑。
