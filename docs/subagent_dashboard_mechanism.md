# Subagent Dashboard 工作机制

> 文件路径：`frontends/subagent_dashboard.py` (622行)

## 定位

基于 **Streamlit** 的 **Subagent 集群监控面板**，用于实时查看、控制和干预所有后台运行的 subagent。

---

## 一、整体架构（主循环）

```
main()
  ├── 侧边栏（控制面板）
  │   ├── 自动刷新开关 + 间隔滑块
  │   ├── 手动刷新按钮
  │   ├── Agent 启动面板（表单）
  │   └── 文件协议说明
  │
  └── 主区域（集群监控）
      ├── 集群概览（5 指标卡）
      └── Agent 卡片列表（每个 subagent 一张）
           └── 每 3s（可调）→ st.rerun() 全量重绘
```

---

## 二、核心数据结构

### 任务目录约定

每个 subagent 对应 `temp/{任务名}/` 目录，通过是否存在 **`input.txt`** 判定为有效 subagent。

### 目录内关键文件

| 文件 | 方向 | 用途 |
|------|------|------|
| `input.txt` | 输入 | subagent 的任务描述 |
| `output1.txt`, `output2.txt`... | 输出 | 每轮执行输出（按编号排序） |
| `stdout.log` | 日志 | 控制台标准输出 |
| `stderr.log` | 日志 | 错误日志（非空时标记 ⚠️） |
| `_stop` | 控制 | 存在即标记"已停止" |
| `_intervene` | 控制 | 写入后下轮被 subagent 读取为追加指令 |
| `_keyinfo` | 控制 | 注入工作记忆 |
| `reply.txt` | 控制 | 回复等待中的 subagent |

---

## 三、三大核心函数

### 1️⃣ `get_subagent_dirs()` — 扫描任务目录

```python
def get_subagent_dirs():
    """扫描 temp/ 下所有含 input.txt 的子目录"""
```

- 扫描 `temp/` 下所有子目录
- 过滤条件：子目录内存在 `input.txt`
- 按字母排序返回

### 2️⃣ `get_running_pids()` — 进程检测（四级降级）

```python
def get_running_pids():
    """获取所有 Python 进程的 {PID: command_line} 映射"""
```

**降级策略：**

| 优先级 | 方法 | 说明 |
|--------|------|------|
| 1 | `psutil` | 最准确，遍历 Python 进程获取完整命令行 |
| 2 | `wmic` | Windows 回退，解析 CSV 格式输出 |
| 3 | `tasklist` | 兜底，仅获取 PID 无命令行 |
| 4 | 空映射 | 后续由启发式兜底 |

**精确匹配条件：** 命令行同时包含「任务名」和 `agentmain`/`--task`。

**启发式兜底：** 检查 `output{n}.txt` 最近 180 秒有更新 → 认为进程存活。

### 3️⃣ `get_subagent_status()` — 状态判断

```python
def get_subagent_status(task_dir: Path, pid_map: dict):
    """返回 (status, pid, runtime, latest_output, all_outputs, stdout_log, stderr_log, input_text, enc_label)"""
```

**状态机逻辑：**

```
存在 _stop 文件？
  ├─ 是 → "stopped"
  └─ 否 → 检查进程存活
       ├─ 存活 → [ROUND END] 已出现且无 reply.txt？
       │   ├─ 是 → "waiting"（等待用户回复）
       │   └─ 否 → "running"（正在执行）
       └─ 不存活 → 有 output 输出？
           ├─ 是 → "done"（已完成）
           └─ 否 → "stopped"（未正常启动）
```

**辅助函数 `_detect_and_read()`：** 按 UTF-8 → GBK → cp936 → `replace` 逐级降级解码文件尾部。

**辅助函数 `_extract_model_name()`：** 从 `stdout.log` 首部正则提取 model/session 名称。

---

## 四、主界面布局

### 侧边栏（控制面板）

#### 1. 自动刷新控制
- `st.checkbox("🔄 自动刷新 (3s)", value=True)`
- `st.slider("刷新间隔(秒)", 1, 10, 3)`

#### 2. Agent 启动面板（`st.form`）

```python
task_name = st.text_input("Task Name")
task_prompt = st.text_area("Task Prompt")
llm_no = st.selectbox("模型选择", options=["默认 (0)", "模型1 (1)", ...])
```

点击「启动 Agent」后执行：

```python
subprocess.Popen([
    sys.executable, agentmain.py,
    "--task", task_name,
    "--input", task_prompt,
    "--llm_no", selected_no,
    "--bg"
], creationflags=CREATE_NO_WINDOW)
```

#### 3. 文件协议说明
列出所有干预文件名及其作用。

---

### 主区域

#### 集群概览

| 指标 | 说明 |
|------|------|
| 🧠 总数 | 总 agent 数 |
| ▶️ 运行中 | `status == "running"` |
| ⏸️ 等待回复 | `status == "waiting"` |
| ✅ 已完成 | `status == "done"` |
| ⏹️ 已停止 | `status == "stopped"` |

#### Agent 卡片

每张卡片结构如下：

```
┌──────────────────────────────────────────────────────────────┐
│  ▶️ agent_name    🟢运行中  🤖模型名  ⏱时长  🆔PID  [🛑停止] │  ← 始终可见
├──────────────────────────────────────────────────────────────┤
│  📋 详情（折叠）                                               │
│  ├── 📋 任务描述（折叠）                                      │
│  ├── 📄 最新输出（文本区，高120px）                           │
│  └── [📋日志] [📚全部输出] [✏️干预] 三个标签页                 │
│      ├── 📋 日志：stdout.log + stderr.log 尾部（各2000字）     │
│      │   + 🅾 刷新日志按钮 + 编码检测标签                     │
│      ├── 📚 全部输出：所有 output{n}.txt（最新一条默认展开）   │
│      └── ✏️ 干预：                                            │
│          ├── 📨 发送干预 → 写入 _intervene                     │
│          ├── 🧠 注入记忆 → 写入 _keyinfo                       │
│          └── 💬 发送回复 → 写入 reply.txt（仅waiting时可用）   │
└──────────────────────────────────────────────────────────────┘
```

**卡片样式规则：**
- 左侧边框颜色：`running`🟢 / `waiting`🟠 / `done`🔵 / `stopped`⚪ / `error`🔴
- `running` 状态带呼吸动画（`pulse-border` @keyframes）
- `stderr.log` 非空时显示 ⚠️ 角标，卡片添加红色边框

---

## 五、远程干预机制

| 干预方式 | 文件操作 | 生效时机 |
|---------|---------|---------|
| 🛑 **停止** | 写入 `_stop` 空文件 | subagent 下轮检测到即退出 |
| 📨 **发送干预指令** | 写入 `_intervene` 文本 | subagent 下轮 read 追加到提示 |
| 🧠 **注入工作记忆** | 写入 `_keyinfo` 文本 | subagent 下轮注入 |
| 💬 **发送回复** | 写入 `reply.txt` | 仅当状态为 `waiting` 时可用 |

---

## 六、自动刷新机制

```python
# main() 末尾
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
```

- 每次 `rerun()` 完全重绘页面（Streamlit 标准范式）
- 侧边栏提示：自动刷新时不要操作干预控件，避免冲突
- 暂停自动刷新后才能安全操作表单控件

---

## 七、技术要点

### 编码容错
- 所有文件读取使用 `_detect_and_read()` 逐级降级：`UTF-8 → GBK → cp936 → replace`
- 日志尾部默认读取 `stdout: 3000 bytes / stderr: 2000 bytes`

### 进程检测精确匹配
```python
# 匹配条件
str(task_dir.name) in cmdline and ('agentmain' in cmdline or '--task' in cmdline)
```

### 启动方式
```bash
streamlit run frontends/subagent_dashboard.py
```

### 代码根目录
```
CODE_ROOT = D:\open_claw_agent\GenericAgent
TEMP_DIR = CODE_ROOT / "temp"
```

---

## 八、一句话总结

> **基于文件系统约定的无状态监控面板：subagent 通过 `temp/{name}/` 下的文件与 dashboard 通信，dashboard 只读文件判定状态、写文件发送指令，双方完全解耦。**