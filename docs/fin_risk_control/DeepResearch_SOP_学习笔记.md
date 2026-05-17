# DeepResearch SOP — 学习笔记

> 来源：https://fudankw.cn/sophub/sops/69f207e974962f84e0625e0d
> 作者：@sophub 官方
> 学习时间：2026-05-16
> 浏览量：774 · 下载量：204

---

## 一句话总结

**多来源深度研究的DAG规划与并行执行框架** — 对标 MindSearch，解决需要整合网页+本地文件+记忆库等多源信息时的复杂问题。

---

## 核心架构

```
Main Agent (Planner)
├─ 职责：DAG构建、动态规划、收集子结论、决定下一步、综合输出
└─ 禁止：自己去读网页/文件原文——交给subagent，只看摘要结论

Sub Agent (Searcher，每节点一个)
├─ 职责：单一信息源检索 + 总结 → 写结论到output.txt
└─ 禁止：越界读其他节点的原始内容
```

### 关键原则：上下文隔离红线
subagent的context.json必须包含且仅包含：
1. `root_question` — 用户原始问题
2. `parent_conclusions` — 父节点已得结论（精简文字，非原文）
3. `sub_question` — 本节点原子子问题
4. `source` — 信息源描述（URL/文件路径/查询关键词）
5. `output_file` — 绝对路径

---

## 三阶段流程

### 阶段1：问题分解 → 初始DAG

Main agent 将用户问题拆解为原子子问题列表，判断依赖关系，写入 `./dr_{task}/dag.md`

**5种节点类型：**

| 类型 | 触发场景 | subagent工具 |
|:----:|---------|-------------|
| 🌐 WEB | 需要实时/在线信息 | web_scan + web_execute_js |
| 💻 LOCAL | 本地PDF/代码/数据文件 | pdftotext / file_read / code_run |
| 🧠 MEMORY | 记忆库/SOP/配置 | file_read global_mem/user_profile/sop |
| ⚙️ CODE | 需执行脚本获取结果 | code_run |
| 🔗 SYNTH | 汇总（Main agent自己做） | — |

**dag.md格式示例：**
```
# DR: {用户问题一句话}
ROOT: {原始问题}

## 节点列表
- [N1] WEB | 子问题：XX是什么 | 依赖：无
- [N2] LOCAL | 子问题：本地文件YY说了什么 | 依赖：无
- [N3] WEB | 子问题：基于N1结论，进一步查ZZ | 依赖：N1
- [N4] SYNTH | 汇总N1+N2+N3 | 依赖：N1,N2,N3

## 节点状态
N1: [ ] N2: [ ] N3: [ ] N4: [ ]
```

### 阶段2：执行循环

```
WHILE dag中有未完成节点:
  ready_nodes = 依赖全部满足且未执行的节点
  
  IF ready_nodes >= 2 且无资源冲突 → 并行Map模式
  ELSE → 顺序执行单节点
  
  收集结论 → 动态评估是否需要新增节点
```

**并行Map模式关键点：**
- 用 `subprocess.Popen` 并行启动（禁止 `run`）
- 每个节点独立目录 `temp/dr_{task}/{node.id}/`
- 用轮询检查 `output.txt` 是否稳定（大小不再变化）
- 只取结论段（末尾2000字）

### 阶段3：综合输出

- 读取所有节点 `output.txt`，按清洗规范处理
- 按DAG拓扑顺序综合
- 写入报告，告知用户路径

---

## 关键工具函数

### output.txt 清洗规范
```python
def extract_conclusion(content, max_chars=4000):
    # 多标记fallback找结论区域
    # 清洗LLM运行记录、工具调用、调试信息
    # 超过max_chars时在段落边界截断
```

### 报告过长处理
- 动态上限：不截断，只在总报告超80KB时才压缩
- 超80KB：次要节点压缩至3000字，核心节点保持全量

---

## 与MindSearch的对比

| 维度 | DeepResearch SOP | MindSearch |
|:----|:----------------:|:----------:|
| 架构 | Main+Sub Agent | 分层+并行 |
| DAG | 显式dag.md管理 | 隐式依赖 |
| 并行 | subprocess.Popen | 异步 |
| 上下文隔离 | context.json严格隔离 | 共享上下文 |
| 信息源 | WEB/LOCAL/MEMORY/CODE | 搜索为主 |

## 适用/禁用场景

| ✅ 适用 | ❌ 禁用 |
|--------|--------|
| 多来源信息整合 | 单一来源、1-2步可完成 |
| 网页+本地文件+记忆库交叉 | 直接能回答的问题 |
| 需要动态规划的研究任务 | 无需复杂分解的查询 |
