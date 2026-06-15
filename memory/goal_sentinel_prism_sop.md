# Goal Sentinel / Goal Prism SOP

> Phase 2: 存活监控与自恢复 + 多视角并行探索
> 基于 MQTT BBS Pulse 广播

---

## Goal Sentinel（目标哨兵）

### 核心能力
- 通过 MQTT 订阅 `agent/bbs/goal_pulse/post` 监听所有 goal agent 的脉冲
- 追踪每个 agent 的最后脉冲时间
- 超时未收到脉冲 → 标记为僵尸 → 可配置重启命令

### 启动

```bash
# 基本存活监控 (300s 超时)
python scripts/goal_sentinel.py

# 自定义超时
python scripts/goal_sentinel.py --timeout 120

# 后台守护运行
start /b python scripts/goal_sentinel.py --timeout 300
```

### 监控输出

```
[Sentinel] 启动: topic=agent/bbs/goal_pulse/post, timeout=300s
[Sentinel] 健康: [goal_froad-1040128_16720(5s), goal_froad-1040128_18376(12s)]
[Sentinel] ZOMBIE: goal_froad-1040128_16720 (last pulse 312s ago)
```

---

## Goal Prism（目标棱镜）

### 核心能力
- 同一目标从多个视角并行分析
- 每个视角有独立的 Board 和 worker agent
- 全部 worker 完成后自动聚合综合报告

### 配置 (`temp/prism_config.json`)

```json
{
  "objective": "审查项目安全性",
  "perspectives": [
    {"name": "代码安全", "board": "prism_code", "focus": "SQL注入/XSS/CSRF"},
    {"name": "依赖安全", "board": "prism_deps", "focus": "第三方库漏洞"},
    {"name": "配置安全", "board": "prism_config", "focus": "密钥/环境变量"}
  ],
  "budget_per_worker": 600,
  "max_workers": 3
}
```

### 启动

```bash
# 自动创建默认配置 (2个视角)
python agentmain.py --reflect reflect/goal_prism.py

# 自定义配置
set GOAL_PRISM_CONFIG=temp/my_prism.json
python agentmain.py --reflect reflect/goal_prism.py
```

### 产出

```
temp/
├── prism_config.json         # 配置文件
├── prism_workers/            # 各 worker 的 goal_state
│   ├── 代码安全.json
│   ├── 依赖安全.json
│   └── 配置安全.json
└── prism_report.md           # 综合报告
```

---

## 组合使用

```bash
# 终端1: 启动 Sentinel
start /b python scripts/goal_sentinel.py

# 终端2: 启动 Prism
start /b python agentmain.py --reflect reflect/goal_prism.py

# 终端3: 等 Prism 完成
python scripts/goal_wait.py --state temp/prism_workers/代码安全.json
```
