# CodeGraph SOP — 代码分析 + 索引维护标准流程

> 基于 20+ 模块反刍、11MB 索引查询、3 次胖函数拆分的实践

## 架构

```
数据: .codegraph/codegraph.db (SQLite, ~11MB)
守护: codegraph-server (MCP 模式, 文件监听自动同步)
查询: sqlite3 直接查 / tools.codegraph_db API
```

## 守护进程管理

```powershell
# 启动 (MCP 模式)
Start-Process -FilePath node_modules\@astudioplus\codegraph-mcp\bin\codegraph-server-win32-x64.exe `
  -ArgumentList "--workspace D:\open_claw_agent\Beneh --mcp" -NoNewWindow

# 确认状态
Get-Process -Name codegraph-server* | Select-Object Id, StartTime, @{N='Mem';E={$_.WorkingSet64/1MB}}

# 进程空闲 300s 后自动退出；代码变更时自动同步
```

## 索引查询实用 SQL (Phase 2 增强)

### P0: 死函数扫描
```sql
SELECT n.name, n.kind, n.file_path, n.start_line, n.end_line,
       (n.end_line - n.start_line + 1) as nlines
FROM nodes n
WHERE n.kind IN ('function', 'method')
  -- 排除回调/入口
  AND n.name NOT LIKE 'on_%' AND n.name NOT LIKE 'handle_%'
  AND n.name NOT IN ('main', 'start', 'stop')
  AND (n.end_line - n.start_line + 1) > 10
ORDER BY nlines DESC;
```

### P1: 胖函数排行榜
```sql
SELECT n.name, n.kind, n.file_path, n.start_line, n.end_line,
       (n.end_line - n.start_line + 1) as nlines
FROM nodes n
WHERE n.kind IN ('function', 'method')
  AND (n.end_line - n.start_line + 1) > 80
  AND n.file_path NOT LIKE '%_archive%'
ORDER BY nlines DESC;
```

### P2: 依赖拓扑
```sql
-- 文件节点数
SELECT path, node_count FROM files ORDER BY node_count DESC LIMIT 15;

-- 导入依赖
SELECT n.name, n.signature FROM edges e
JOIN nodes n ON n.id = e.target
WHERE e.source = 'file:{path}' AND e.kind = 'contains' AND n.kind = 'import';
```

## 反刍集成 (rumination_sop Phase 2b)

| 文件大小 | 是否文献式 | 使用方式 |
|:--------|:---------|:---------|
| <200 行 | 任意 | 手动扫 (读代码更快) |
| >200 行 | 是 (初始>90%) | CodeGraph 确认后跳过 |
| >200 行 | 否 | CodeGraph Phase 2b |

```
CodeGraph Phase 2b (0.2 秒 vs 手动 3 分钟):
  1. 查胖函数: end_line - start_line > 80
  2. 查扇入: edges source/target 反向引用
  3. 查依赖: import 节点数
```

## 维护建议

- 每轮反刍前确认守护进程在运行
- 大改代码后 touch 文件触发自动同步
- 每季度全量重建: 停进程 → 删 `codegraph.db` → 重启
