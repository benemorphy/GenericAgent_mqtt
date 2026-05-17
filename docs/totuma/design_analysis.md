# totuma.cn 算法可视化网站 — 完整设计分析

> 分析日期: 2026-05-16
> 技术栈: Nuxt.js (Vue) + AntV G6 v4.8.10 + SVG

---

## 一、技术架构

```
Nuxt.js (SSR Vue)
  ├── AntV G6 v4.8.10 — 图可视化引擎 (SVG渲染)
  ├── Prism.js — 代码语法高亮
  ├── Element UI — UI组件库
  └── 自定义状态机引擎 — 算法步骤管理
```

## 二、站点结构 (25+算法页)

### 线性表
  `/en/algorithms/list/sequence` — 顺序表
  `/en/algorithms/list/link-head-node` — 单链表(有头) [主要分析页]

### 栈与队列
  `/en/algorithms/stack-queue/stack-sequence`
  `/en/algorithms/stack-queue/queue-link-head-node`

### 树/图/查找/排序
  `/en/algorithms/tree/binary-search-tree-link` — BST
  `/en/algorithms/graph/struct-link_bfs` — BFS
  `/en/algorithms/sort/insert` — 插入排序
  `/en/algorithms/search/linear` — 顺序查找

## 三、核心设计模式

### 3.1 G6图可视化引擎 (AntV v4.8.10)
- 自定义节点: 矩形+文字组合表示节点
- 自定义边: 带箭头的有向边
- 状态管理: `graph.setItemState(item, 'active', true)`
- SVG渲染而非Canvas

### 3.2 节点状态语义配色
| 状态 | 色值 | 含义 |
|:-----|:----:|:-----|
| 默认 | `#f0f0f0` 灰 | 未操作 |
| 访问中 | `#1890ff` 蓝 | 当前节点 |
| 已完成 | `#52c41a` 绿 | 处理完成 |
| 待删除 | `#f5222d` 红 | 将要移除 |
| 新增 | `#fa8c16` 橙 | 刚插入 |

### 3.3 三面板布局
```
[导航侧栏]  [可视化画布(G6 SVG)]
            [代码查看器(多语言Tab)]
[控制栏: Play/Step/速度/变量]
```

## 四、设计原则
1. **代码与可视化双向绑定**: 每行代码对应一个可视化步骤
2. **状态序列预生成**: 算法分解为离散状态快照
3. **SVG渲染**: 支持高清屏和精确样式控制
4. **语义化配色**: 颜色传达算法执行阶段
5. **一致性框架**: 25+页面复用相同布局
