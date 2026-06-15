# Goal Mode 移植可行性分析

> 基于对 `D:\00synchronize\GenericAgent`（源项目）和 `D:\open_claw_agent\Beneh`（本项目）的代码审计
> 来源：Docs: goal_mode_analysis.md

## 结论：可行，工作量约 1-2 小时

已经在 B 项目（Beneh）中有大量基础设施，核心缺失仅 1 处。

---

## 现状差异表

| 组件 | 源项目（GenericAgent） | 本项目（Beneh） | 缺失程度 |
|------|----------------------|----------------|---------|
| `reflect/goal_mode.py` | 97 行，完整 | 97 行，略有差异 | **小改** |
| `memory/goal_mode_sop.md` | 50 行 | 49 行，有差异 | **小改** |
| `agentmain.py --reflect` 参数 | 有（L192-193） | 无 | **核心缺失** |
| `agentmain.py` reflect 循环 | 38 行（L239-276） | 无 | **核心缺失** |
| `reflect/scheduler.py` | 无 | 有（131 行定时任务） | B 项目独有优势 |
| `reflect/autonomous.py` | 无 | 有（6 行自动触发） | B 项目独有优势 |
| `memory/goal_hive_sop.md` | 有 | 无 | **新增** |
| `memory/goal_hive_master_duty.md` | 有（107 行） | 无 | **新增** |

---

## 缺失 1（致命）：agentmain.py 无 --reflect 参数

### 现状

当前 Beneh 的 `agentmain.py` only 支持 3 种模式：

```
agentmain.py                          → 交互 / MQTT 模式
agentmain.py --task <name>            → Subagent 文件模式
```

没有 `--reflect` 参数。

### 需要添加的内容

```python
# 在 argparse 中添加（约 L189 附近）
parser.add_argument('--reflect', metavar='SCRIPT', help='反射模式：加载监控脚本，check()触发时发任务')

# 解析未知参数（用于传参给 reflect 脚本）
_args_unknown = [a for a in sys.argv[1:] if a.startswith('--') and a.lstrip('-') not in vars(args)]
_reflect_args = dict(zip([k.lstrip('-') for k in _args_unknown[::2]], _args_unknown[1::2]))

# 在 __main__ 末尾、MQTT 模式之前或作为独立分支，添加 reflect 循环（约 38 行）
if args.reflect:
    agent.peer_hint = False
    agent.force_non_stream = True
    import importlib.util
    spec = importlib.util.spec_from_file_location('reflect_script', args.reflect)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if hasattr(mod, 'init'): mod.init(_reflect_args)
    _mt = os.path.getmtime(args.reflect)
    while True:
        if os.path.getmtime(args.reflect) != _mt:
            spec.loader.exec_module(mod); _mt = os.path.getmtime(args.reflect)
            if hasattr(mod, 'init'): mod.init(_reflect_args)
        time.sleep(getattr(mod, 'INTERVAL', 5))
        try: task = mod.check()
        except Exception: continue
        if task and task == '/exit': break
        if task is None: continue
        dq = agent.put_task(task, source='reflect')
        while 'done' not in (item := dq.get(timeout=1200)): pass
        result = item['done']
        if (on_done := getattr(mod, 'on_done', None)):
            on_done(result)
        if getattr(mod, 'ONCE', False): break
```

**位置策略**：建议在 MQTT 模式分支之前，作为独立第 4 种运行模式。因为 reflect 模式与 MQTT Worker 模式互斥。

---

## 缺失 2（次要）：goal_mode.py 差异

源项目的 goal_mode.py 有 2 处 Beneh 可以吸收的改进：

| 差异点 | 源项目 | 本项目 | 建议 |
|--------|--------|--------|------|
| `done_prompt` 字段 | `BUDGET_LIMIT_PROMPT` 模板引用 `{done_prompt}` | 没有 | 添加（用于 Hive Master 收口指令） |
| prompt 指令 | 6 条规则，含"扩大视野"换角度 | 5 条规则，更简练 | 保留本项目版本（更实用） |

---

## 缺失 3（新增文件）：goal_hive_sop.md + master_duty.md

这两个文件是 Goal Hive 多 Worker 协作的配套 SOP，直接从源项目复制+调整路径即可。

- `goal_hive_sop.md`（52 行）：Hive 模式启动、第一帖规范、Worker 拉起
- `goal_hive_master_duty.md`（107 行）：Master 编排哲学（x/u/y/J 控制模型）

---

## 实施步骤

```
Step 1: agentmain.py 添加 --reflect 参数 + reflect 循环
        ├── argparse 添加 --reflect
        ├── 添加 _reflect_args 解析
        └── 添加 reflect 主循环分支（38 行）
        
Step 2: 同步 goal_mode.py（可选）
        ├── 添加 done_prompt 支持
        └── 其余保持本项目版本

Step 3: 复制 goal_hive_sop.md
        └── 调整路径引用为 Beneh 项目路径

Step 4: 复制 goal_hive_master_duty.md (107 行)
        ├── 调整路径引用
        └── 适配 MQTT BBS 协议

Step 5: 更新 L1 索引
        └── 添加新 SOP 到 global_mem_insight.txt

Step 6: 测试
        ├── 启动 goal_mode 单实例
        └── 启动 goal_hive 多 worker
```

---

## 风险与注意事项

1. **agentmain.py 结构差异**：Beneh 的 `__main__` 末端直接进入 MQTT 模式（`start_mqtt_agent`），reflect 分支必须在它之前或作为独立 if/elif 分支，避免冲突
2. **force_non_stream**：源项目在 reflect 模式下设置 `force_non_stream=True`，Beneh 的 stream 实现需确认兼容
3. **代码过热加载**：reflect 循环每轮 `exec_module` 热重载，需确认不影响 agent 的运行时状态
4. **GA 路径差异**：源项目 reflect 脚本相对路径基于 `script_dir`，Beneh 的 `GA/reflect/` 路径相同，无需调整
