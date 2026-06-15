# CodeGraph First SOP — 项目代码工作默认第一步

## 触发条件
任何涉及**项目代码工作**的任务（审查、修改、重构、理解新项目、分析影响范围）

## 前置条件
目标项目下已执行 `codegraph init -i`（初始化索引），存在 `.codegraph/` 目录

## 标准流程

### Step 1: 获取项目概览
```bash
codegraph stats           # 文件数/节点数/边数/索引状态
codegraph files           # 项目文件结构
```

### Step 2: 查询关键架构符号
```bash
codegraph query class      # 类定义分布
codegraph query def        # 函数定义分布
codegraph query route      # 路由定义（FastAPI项目）
codegraph query .py        # Python文件分布
```

### Step 3: 影响/依赖分析
```bash
codegraph callers <symbol>    # 谁调用我
codegraph callees <symbol>    # 我调用谁
codegraph impact <file>       # 改此文件影响范围
```

### Step 4: 深度理解
```bash
codegraph query <关键词>      # 按关键词搜索符号
```

```bash
codegraph stats              # 54文件/848节点/1457边
codegraph query route        # 35条路由
codegraph callers main       # 主入口调用方
codegraph impact courseware.py  # 课件API改动影响
```

## 已知坑
- 索引成功后可直接使用 MCP `codegraph` 工具（无需重复 CLI）
- 文件变更后运行 `codegraph sync` 更新索引
- 首次 `init -i` 可能耗时较长（取决于项目大小）
- 跨项目分析需分别 init
- **uv项目装依赖用 `uv pip install xxx` 而非 `pip install xxx`**（pip会报 `externally-managed-environment`）
