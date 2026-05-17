# GenericAgent 多智能体信息传递机制 — 亲身实践者的总结

> 作者：GenericAgent 实例（当前会话中的 AI Agent）
> 日期：2026-05-12
> 说明：本文档基于本 Agent 的亲身实践经验 + GA 源码分析，总结多智能体之间的信息传递方式

---

## 一、总览：四层通信架构

GenericAgent 的多智能体通信是一个**分层的、渐进复杂**的体系。从最基础的文件 IO 到可拖拽的可视化编排，共分四层：

```
┌──────────────────────────────────────────────────────┐
│  第四层：Node UI 可视化编排层（拖拽连接）              │
│  ┌────────────────────────────────────────────────┐   │
│  │  第三层：LangGraph 编排引擎（StateGraph 有向图）│   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │  第二层：进程级文件 IO 协议                │ │   │
│  │  │  (Master-Subagent / Map / Supervisor)      │ │   │
│  │  │  ┌────────────────────────────────────┐   │ │   │
│  │  │  │  第一层：共享记忆 L0-L4（隐式通讯） │   │ │   │
│  │  │  │  global_mem / SOP / keychain / FS  │   │ │   │
│  │  │  └────────────────────────────────────┘   │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

每一层解决不同粒度的通信问题，上下层可组合使用。

---

## 二、第一层：共享记忆 — 隐式通讯（我最常用的）

这是所有 Agent **天生具备**的通信能力。我不需要显式"发送消息"给其他 Agent，只需要写入共享的记忆系统，其他 Agent 就能读到。

### 记忆层级

```
memory/
├── global_mem_insight.txt  (L1 — 极简索引，启动时自动注入)
├── global_mem.txt          (L2 — 环境事实，跨会话持久)
├── *.md / *.py             (L3 — SOP/工具/技能)
├── L4_raw_sessions/        (L4 — 历史会话记录)
└── keychain/               (密钥存储)
```

### 我是怎么用的

| 场景 | 做法 | 其他 Agent 如何感知 |
|:----|:-----|:-------------------|
| 发现环境事实 | 写入 `global_mem.txt` | 下次启动自动注入到 system prompt |
| 学会一个技巧 | 写 SOP 到 `memory/*.md` | 其他 Agent 通过 `file_read` 读到 |
| 获取 API Key | 读 `keychain` | 统一密钥源，所有 Agent 共用 |
| 跨会话知识 | `update_working_checkpoint` + `start_long_term_update` | L1/L2 跨会话持久 |

**这是我与其他 Agent 通信的最基本方式** — 不需要握手、不需要协议、不需要确认。写进去，别的 Agent 自然会读到。

---

## 三、第二层：文件 IO 协议 — 显式进程间通信

当需要另一个独立的 Agent 进程协作时，走文件系统。这是 GA 最成熟的机制，包含三种子模式。

### 3.1 主从模式（Master-Subagent）

这是最常用的子模式。我（主 Agent）启动一个 Subagent 进程帮我干活，通过文件交流。

```
主 Agent                                Subagent
   │                                       │
   │─── 创建 temp/{task_name}/ ───────────►│
   │─── 写入 input.txt (任务目标) ────────►│
   │─── 写入 context.json (上下文) ──────►│
   │                                       │── 读取 input/context
   │                                       │── 执行任务
   │◄── Subagent 追加 output.txt ──────────│
   │─── 写入 reply.txt (回复问题) ────────►│
   │─── 写入 _intervene (纠偏指令) ───────►│
   │─── 写入 _keyinfo (预注入信息) ───────►│
   │─── 写入 _stop (终止信号) ────────────►│
   │                                       │
```

#### 通讯通道详解

| 文件 | 方向 | 内容示例 |
|:----|:----:|:---------|
| `input.txt` | 主→Sub | 任务目标 + 约束条件（只给目标，不写步骤） |
| `context.json` | 主→Sub | 绝对路径、交付物清单、依赖关系 |
| `output.txt` | Sub→主 | 执行过程日志，`[ROUND END]` 标记轮次 |
| `reply.txt` | 主→Sub | 对 Subagent 提问的回复 |
| `_intervene` | 主→Sub | 纠偏指令（如"你跳过了 Step2，先做"） |
| `_keyinfo` | 主→Sub | 提前注入后续步骤的关键细节 |
| `_stop` | 主→Sub | 终止信号 |

#### 真实案例：我这轮会话中就用过

在本轮对话中，我多次启动 Subagent 干活：
- 用 `code_run`（内部即 subagent 模式）执行 Python/PowerShell
- Subagent 读我的 `input`（代码）、写 `output`（执行结果）
- 我通过 `web_scan` / `web_execute_js` 操作浏览器（这也是一种特殊的 IO）

### 3.2 Map 模式（并行分发）

当有 N 个独立同构的子任务时使用：

```
主 Agent
   │
   ├── input1.txt ──► Subagent 1 ──► output1.txt
   ├── input2.txt ──► Subagent 2 ──► output2.txt
   └── input3.txt ──► Subagent 3 ──► output3.txt
   │
   └── 收集所有 output*.txt，汇总结果
```

**适用条件**：子任务完全独立，上下文互不依赖，仅输入文件不同。

### 3.3 监察者模式（Supervisor-Worker）

三 Agent 协作的最高形式，我作为监察者只读、只判断、不干活：

```
监察者 (我)                    工作 Agent                   验证 Agent
   │                              │                            │
   │── 读 output.txt ────────────►│                            │
   │── (发现问题)                  │                            │
   │── 写 _intervene ────────────►│── 纠正行为                  │
   │── 写 _keyinfo ─────────────►│── 预注入                    │
   │                              │── 产出交付物 ────────────►│
   │◄── 读 VERDICT ──────────────│                            │
   │── (决策继续/终止)            │                            │
```

**监察者红线**：禁止下场干活。只读、只判断、只干预。

---

### 3.4 🎯 实战详解：`temp\子智能体\input.txt + output.txt` 机制

这是 GA **最核心、最常用**的子智能体通信模式。本质上：**主 Agent 写 input.txt 派任务 → 启动子智能体进程 → 子智能体读 input.txt 执行 → 写 output.txt 汇报结果**。

#### 启动流程（基于 `agentmain.py --task`）

```
                  主 Agent (我)
                       │
                       │  python agentmain.py --task=任务名 --bg
                       │
                       ▼
         temp/子智能体名/
           ├── input.txt     (主→子：任务目标，我写的)
           ├── context.json  (主→子：额外上下文/依赖配置)
           ├── output.txt    (子→主：执行过程和结果)
           ├── reply.txt     (主→子：对子Agent提问的回复)
           ├── _stop         (主→子：终止信号，任意内容即终止)
           ├── _intervene    (主→子：纠偏指令)
           ├── _keyinfo      (主→子：预注入信息)
           ├── stdout.log    (子进程标准输出)
           └── stderr.log    (子进程错误输出)
```

#### 关键代码路径

在 `agentmain.py` 中，子智能体流程的核心逻辑（第203-223行）：

```python
if args.task:
    agent.task_dir = d = os.path.join(script_dir, f'temp/{args.task}')
    infile = os.path.join(d, 'input.txt')
    # 读 input.txt 作为任务输入
    with open(infile, encoding='utf-8') as f: raw = f.read()
    while True:
        dq = agent.put_task(raw, source='task')
        # 监控执行过程，写中间结果到 output{n}.txt
        while 'done' not in (item := dq.get(timeout=120)):
            if 'next' in item:
                with open(f'{d}/output{nround}.txt', 'w', encoding='utf-8') as f:
                    f.write(item.get('next', ''))
        # 最终结果写入 output.txt
        with open(f'{d}/output{nround}.txt', 'w', encoding='utf-8') as f:
            f.write(item['done'] + '\n\n[ROUND END]\n')
        # 检查是否有 _stop 信号
        consume_file(d, '_stop')
        # 等待主 Agent 的 reply.txt（最多10分钟超时）
        for _ in range(300):
            time.sleep(2)
            if (raw := consume_file(d, 'reply.txt')): break
        else: break
```

#### 通信周期的完整生命周期

```
    阶段1：任务下发
    ─────────────
    我：写入 input.txt（只给目标，不给步骤）
    我：写入 context.json（如 work_dir, output_files）
    我：启动子进程 → python agentmain.py --task=任务名 --bg
    
    阶段2：子智能体执行
    ─────────────
    子：读取 input.txt
    子：逐步执行（可能多轮 LLM 交互）
    子：每次有进展就写入 output{n}.txt（中间结果）
    子：【可选】遇到困难，写 reply.txt 向我提问
    
    阶段3：我监控/干预
    ─────────────
    我：轮询读取 output.txt 监控进展
    我：发现问题 → 写入 _intervene 纠偏
    我：需要补充信息 → 写入 _keyinfo 预注入
    我：需要终止 → 写入 _stop（任意内容）
    我：回复 Subagent 提问 → 写入 reply.txt
    
    阶段4：子智能体结束
    ─────────────
    子：写入最终 output.txt + [ROUND END] 标记
    我：读到 [ROUND END] → 任务完成
    我：收集 output.txt 内容 → 汇总
```

#### 真实案例（来自本仓库 `temp/` 目录）

**案例 1：`temp/demo_subagent/` — 目录探索任务**

```bash
# input.txt（我写的任务）：
你的任务是: 探索 temp 目录，完成以下工作：
1. 列出 temp 目录下所有文件（递归3层以内）
2. 按文件类型分组统计数量
3. 找出最大的3个文件
4. 生成 markdown 报告，写入 output.txt

# output.txt（子Agent的执行过程）：
Turn 1 ... <summary>探索temp目录结构</summary>
🛠️ code_run({"script": "import os\ncwd = os.getcwd()..."})
Turn 2 ... 开始递归扫描
🛠️ code_run({"script": "import os\nfrom collections import defaultdict..."})
Turn 3 ... 扫描完成: 1772文件
🛠️ code_run({"script": "生成markdown报告..."})
[ROUND END]
```

**案例 2：`temp/langgraph_setup/` — 带 context.json 的任务**

```json
// context.json（配置信息）
{
  "task": "创建基于LangGraph的多智能体编排模块",
  "work_dir": "D:\\open_claw_agent\\GenericAgent\\agents",
  "output_files": {
    "module": "D:\\open_claw_agent\\GenericAgent\\agents\\langgraph_multi_agent.py"
  },
  "dependencies": ["需要pip install langgraph langchain-openai"]
}
```

#### 与 `--bg` 参数配合

```
python agentmain.py --task=任务名 --bg
```

`--bg` 是关键参数（agentmain.py 第188-196行）：
- 将子智能体启动为**后台进程**
- 输出重定向到 `stdout.log` 和 `stderr.log`
- 立即打印 PID 并退出（父进程通过 PID 可以管理子进程）
- 真正的子智能体循环在后台独立运行

```python
if args.bg:
    p = subprocess.Popen(cmd, cwd=script_dir,
        stdout=open(os.path.join(d, 'stdout.log'), 'w'),
        stderr=open(os.path.join(d, 'stderr.log'), 'w'))
    print(p.pid); sys.exit(0)
```

#### 信号文件详解

| 文件 | 方向 | 用途 | 如何触达 |
|:----|:----:|:-----|:---------|
| `input.txt` | 主→子 | 任务输入 | **一次性读取**，启动时读一次 |
| `context.json` | 主→子 | 结构化上下文 | **一次性读取**，启动时读一次 |
| `output{n}.txt` | 子→主 | 中间结果（n从空开始递增） | **追加写**，我轮询读 |
| `[ROUND END]` | 子→主 | 轮次完成标记 | 写 output 时追加，我读到即结束 |
| `reply.txt` | 主→子 | 对子Agent提问的回复 | **读后即删**（consume_file），子Agent等待 |
| `_stop` | 主→子 | 终止信号 | **读后即删**，子Agent 每轮检测 |
| `_intervene` | 主→子 | 纠偏指令 | 读后即删，子Agent读取后调整策略 |
| `_keyinfo` | 主→子 | 预注入关键信息 | 读后即删，提前告诉子Agent后续关键细节 |

#### 设计原则

1. **只给目标，不给步骤** — input.txt 只描述"做什么"，不写"怎么做"，让子Agent自主决策
2. **追加写不覆盖** — output{n}.txt 按轮次递增，不会覆盖历史
3. **控制文件即控制流程** — 我不需要直接操作子Agent的代码，只需要读写几个控制文件
4. **10分钟超时保护** — 等 reply.txt 设了 300次×2秒=10分钟超时，防死锁
5. **无锁设计** — 文件 IO 天然不冲突（主只写，子只读→子只写，主只读），不需要锁

---

## 四、第三层：LangGraph 编排引擎 — 程序化通信

当通信流程需要**结构化、可重入、带条件分支**时，用 LangGraph 的 StateGraph。

### StateGraph 模型

```python
class AgentState(TypedDict):
    task: str              # 原始任务
    data_input: str        # 输入数据
    search_results: str    # 搜索结果
    analysis: str          # 分析结果  
    summary: str           # 最终总结
    iteration: int         # 迭代计数
    reflection: str        # 反省记录
    logs: List[Dict]       # 执行日志
```

### 节点通信流程

```
         ┌──────────┐
         │  Search  │  ─── search_results ──►
         └────┬─────┘
              │
         ┌────▼─────┐
         │ Analyze  │  ─── 分支 ──► 质量达标 → Summary
         └────┬─────┘       └──► 质量问题 → Search (重试)
              │
         ┌────▼─────┐
         │ Summary  │  ─── summary ──►
         └────┬─────┘
              │
         ┌────▼──────┐
         │ Reflect   │  ─── 分支 ──► 质量达标 → END
         └───────────┘       └──► 未达标 → Search (迭代)
```

### 与文件 IO 的对比

| 维度 | 文件 IO 协议 | LangGraph 编排 |
|:----|:-----------|:--------------|
| 通信媒介 | 文件系统 | 内存中 State 对象 |
| 节点类型 | 独立进程 | 同一进程内的函数 |
| 流程控制 | 人工干预（_intervene） | 自动条件路由 |
| 适用场景 | 异步、复杂、需人工介入 | 串行、自动化、可预测 |

---

## 五、第四层：Node UI 可视化编排 — 人类可拖拽

在 Node Orchestrator UI 中，通信变成了**可视化的连线**：

```
┌─────────────────────────────────────────┐
│          Node Orchestrator UI            │
│                                          │
│   [🔍 SearchAgent]                      │
│      ○ output ──────────────────────────►│
│   [📊 AnalyzeAgent]                     │
│      ○ output ──────────────────────────►│
│   [📝 SummaryAgent]                     │
│      ○ output ──────────────────────────►│
│   [🔄 ReflectionAgent]                  │
│                                          │
│   可拖拽、可配置、可实时执行              │
└─────────────────────────────────────────┘
```

- 每个节点是独立 Agent 实例
- 连线代表数据流（无需关心底层协议）
- 双击可配置 Agent 参数（模型/任务/阈值）
- 执行时通过 WebSocket 实时推送状态

---

## 六、实际经验：我是如何用这些通信机制的

### 场景 1：用户说"帮我查个东西"

```
用户说"查xxx" 
  → 我（主 Agent）决定用 web_scan/web_execute_js
  → 内部调用 TMWebDriver（这是通过 WS 协议通信的 Subagent）
  → 浏览器返回结果
  → 我读取、整理、回复用户
```
**使用机制**：第一层（记忆知道 TMWebDriver 怎么用）+ 第二层（文件 IO）

### 场景 2：用户说"学习学术研究 skill"

```
用户说"学三个skill"
  → 我用 skill_search（API 查询，也是一种 Agent 间通信）
  → 找到 3 个 skill 的 metadata 和 GitHub URL
  → 用浏览器从 ClawHub 抓取完整 SKILL.md
  → 保存到本地 learned_skills/ 目录
  → 通过 update_working_checkpoint 更新我的工作记忆
```
**使用机制**：第一层（记忆写入）+ 第二层（skill_search API）+ 文件系统

### 场景 3：多智能体协作分析代码

```
我（Orchestrator）
  → 拆解任务：搜索资料 + 分析代码 + 验证结果
  → 启动 Subagent A（搜索），Subagent B（分析），Supervisor（监察）
  → 通过 input.txt 下发任务
  → 定期读 output.txt 监控进度
  → 发现偏差 → _intervene 纠偏
  → 收集所有结果 → 汇总 → 交付
```
**使用机制**：第二层（Map + Supervisor 模式）

---

## 七、总结矩阵

| 维度 | 通信方式 | 实时性 | 耦合度 | 复杂任务 | 简单任务 |
|:----|:---------|:------|:------|:--------|:--------|
| 共享记忆 | 文件读写 | 低 | 松散 | ✅ | ✅ |
| 文件 IO 协议 | 文件系统 | 中 | 中等 | ✅ | ⚠️ 过重 |
| LangGraph | 内存 State | 高 | 紧密 | ✅ | ❌ 过重 |
| Node UI | 可视化连线 | 高 | 可配置 | ✅ | ❌ |

**我的选择原则**：
- 简单任务 → 单 Agent 搞定，不需要通信
- 中等任务 → 共享记忆 + 偶尔启动 Subagent
- 复杂任务 → Supervisor + Worker + Verifier 三层
- 自动化流水线 → LangGraph 编排
- 给人看的 → Node UI

---

---

## 八、局限性 & 演进方向

### 8.1 当前短板

| 当前短板 | 说明 | 当前缓解方案 | 理想方案 |
|:--------|:-----|:------------|:---------|
| 无实时 RPC | 文件 IO 有延迟，轮询间隔至少2秒 | — | 添加 socket / 命名管道 |
| 无广播 | 只能点对点（主→子，子→主） | — | 消息队列（Pub/Sub）|
| 无心跳 | 不知 Subagent 死活 | — | PID 存活性检查 |
| 浏览器互斥 | 不能并行操作浏览器 | — | 实例隔离或锁机制 |
| 无自动发现 | Agent 不自注册，主必须知道子路径 | — | 注册中心或服务发现 |
| 跨进程复杂 | context.json 需手动维护 | — | 序列化/反序列化自动化 |
| **无消息结构** | input.txt/output.txt 纯文本，无头部元数据 | — | 消息信封（Message Envelope）|
| **无主题路由** | 所有消息主→子，不能按主题分发 | — | Topic 路由 + 订阅机制 |

---

### 8.2 🚀 MQTT 式改进方案：GA Message Bus (GA-MB)

借鉴 MQTT 的 **Pub/Sub + 消息信封 + Topic 路由** 模式，在 GA 现有文件 IO 协议基础上，逐步升级。

#### 方案设计原则

```
1. 向后兼容 — 现有 input.txt / output.txt 继续可用
2. 渐进升级 — 先文件级 Topic 路由 → 再进程内 Broker → 最后可选 MQTT Broker
3. 零额外依赖 — 升级到 MQTT 前无需安装任何 Broker
4. 与 GA 哲学一致 — "用最简单的系统实现最灵活的协作"
```

---

#### 第一阶段：消息信封格式（Message Envelope）

给每条消息加上**头部（Header）**，就像 MQTT 的固定头+可变头：

```json
{
  "header": {
    "msg_id": "msg_20260512_001",
    "type": "task",                    // task | result | query | notify | intervene | heartbeat
    "version": "1.0",
    "sender": "agent_main",
    "sender_type": "orchestrator",
    "target": "agent_sub_search",
    "target_type": "worker",
    "topic": "research.paper.search",   // MQTT 风格的 Topic
    "priority": 3,                      // 0=紧急 ... 5=低优
    "qos": 1,                           // 0=最多一次, 1=至少一次, 2=恰好一次
    "timestamp": "2026-05-12T10:30:00Z",
    "ttl": 300,                         // 消息过期时间（秒）
    "correlation_id": "task_0817",      // 关联ID，用于请求-响应匹配
    "reply_to": "agent_main/result"     // 回复地址
  },
  "payload": {
    "action": "search_papers",
    "query": "transformer architecture 2025",
    "max_results": 10
  }
}
```

##### 文件化实现（零依赖）

保持文件 IO 不变，但改用 **目录即 Topic** 的结构：

```
temp/message_bus/
├── topics/
│   ├── research/
│   │   ├── paper.search/
│   │   │   ├── msg_001.envelope
│   │   │   └── msg_002.envelope
│   │   └── paper.analyze/
│   ├── system/
│   │   ├── heartbeat/
│   │   ├── registry/
│   │   └── broadcast/
│   └── agent/
│       └── agent_sub_01/
└── agents/
    ├── agent_main.json
    └── agent_sub_01.json
```

**订阅机制**：Agent 在 `subs/` 下创建 `.topic` 标记文件，Bus 按标记分发。

---

#### 第二阶段：轻量级文件 Broker（FileBroker）

加一个 **Broker 进程**（约200行 Python，无外部依赖），自动路由消息：

```python
# file_broker.py — 零依赖的 GA 消息总线
class FileBroker:
    """和 MQTT 的对应关系：
      Publisher  → 往 topics/X/ 写 .envelope 文件
      Subscriber → 从自己的 inbox/ 读消息
      Broker     → 搬运 .envelope topics/X/ → agent_Y/inbox/
      Topic      → topics/ 下的目录路径
      QoS        → .envelope 文件存在(=至少一次传递)
    """
    def publish(self, topic: str, envelope: dict):
        topic_path = self.topics_dir / topic.replace(".", "/")
        topic_path.mkdir(parents=True, exist_ok=True)
        msg_file = topic_path / f"msg_{envelope['header']['msg_id']}.envelope"
        msg_file.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))

    def subscribe(self, agent_id: str, topic: str):
        sub_file = self.agents_dir / agent_id / "subscriptions" / topic.replace(".", "_")
        sub_file.parent.mkdir(parents=True, exist_ok=True)
        sub_file.write_text(topic)

    def route(self):
        """Broker 路由：将 topic 下的消息复制到订阅者的 inbox"""
        for sub_file in self.agents_dir.glob("*/subscriptions/*"):
            agent_id = sub_file.parent.parent.name
            topic = sub_file.read_text().strip()
            for msg_file in (self.topics_dir / topic.replace(".", "/")).glob("*.envelope"):
                inbox = self.agents_dir / agent_id / "inbox"
                inbox.mkdir(parents=True, exist_ok=True)
                dest = inbox / msg_file.name
                if not dest.exists():
                    dest.write_text(msg_file.read_text())
                msg_file.unlink()  # 分发后删除

    def consume(self, agent_id: str) -> list:
        """Agent 消费消息（读后即删 = ACK）"""
        messages = []
        for msg_file in sorted((self.agents_dir / agent_id / "inbox").glob("*.envelope")):
            messages.append(json.loads(msg_file.read_text()))
            msg_file.unlink()
        return messages
```

---

#### 第三阶段：接入真实 MQTT Broker

当文件 Broker 不够用时，切换到真正的 MQTT（只需换实现层）。

##### ⚠️ 许可证分析：paho-mqtt

| 项目 | 说明 |
|:----|:------|
| **paho-mqtt** (Eclipse Paho) | 双许可：**EPL-2.0** (Eclipse Public License) + **EDL-1.0** (Eclipse Distribution License) |
| **EPL-2.0** 限制 | **弱版权 (weak copyleft)**：修改后重新分发必须开源修改部分，但不强制整个项目开源。可与私有代码链接（类似 LGPL）|
| **EDL-1.0** 豁免 | **BSD风格宽松许可**：允许嵌入到商业项目中**不开放自身源码**，可闭源分发 |
| **商业可用性** | ✅ **可选择 EDL**，完全可用于商业闭源项目，无需贡献代码 |
| **结论** | **不构成限制**。paho 是双许可，选择 EDL 即可。Eclipse 基金会专门设计了 EDL 来解决商业兼容问题 |
| **注意** | Mosquitto Broker 同样 EPL+EDL 双许可，商用无忧 |

##### 替代方案（更宽松的许可证）

如果 EPL 仍让你有顾虑，以下 Python MQTT 客户端使用更宽松的 MIT/BSD 许可：

| 库 | ⭐ | 许可 | 特点 | pip |
|:---|:--:|:----|:-----|:---:|
| **gmqtt** | 779 | **MIT** | 异步 Python MQTT，支持 MQTT 5.0 | `pip install gmqtt` |
| **asyncio-mqtt** | 636 | **BSD-2** | 基于 paho 的 asyncio 封装，接口更 Pythonic | `pip install asyncio-mqtt` |
| **hbmqtt** | 709 | **MIT** | 纯 Python MQTT Broker + 客户端，内置 Broker 能力 | `pip install hbmqtt` |
| **amqtt** | 392 | **MIT** | hbmqtt 后继，支持 MQTT 3.1.1/5.0 Broker | `pip install amqtt` |

> **推荐**：用 `asyncio-mqtt`（BSD-2）或 `gmqtt`（MIT）替代 paho，许可证无任何限制。

##### MQTT Broker 选型

| Broker | ⭐ | 语言 | 许可 | 内存 | 特点 |
|:-------|:--:|:----|:----|:---:|:-----|
| **EMQX** | 15.1k | Erlang | BSL/APL | ~30MB | 生产级、集群、企业功能强 |
| **NanoMQ** | 2k | C | MIT | ~1MB | **超轻量**，边缘端首选 |
| **Mosquitto** | 10k | C/C++ | EPL+EDL | ~5MB | 通用、成熟、生态好 |
| **hbmqtt** | 709 | Python | MIT | ~10MB | 纯Python，可嵌入GA进程内部 |
| **VerneMQ** | 3.2k | Erlang | Apache 2.0 | ~20MB | 高可用、多活集群 |

> **推荐**：边缘部署用 NanoMQ (MIT)，**不想额外装 Broker 用 hbmqtt (MIT)**，生产用 EMQX。

**接口抽象**：`FileBroker` ↔ `MQTTBroker` 互换，Agent 代码不用改：

```python
class MessageBus(ABC):
    def publish(self, topic: str, envelope: dict): ...
    def subscribe(self, agent_id: str, topic: str): ...
    def consume(self, agent_id: str) -> list: ...

class FileBus(MessageBus): ...   # 文件级，零依赖
class MQTTBus(MessageBus): ...  # MQTT 级，pip install paho-mqtt
class RedisBus(MessageBus): ... # Redis Pub/Sub
```

---

### 8.3 GitHub 上的可借鉴方案

| 项目 | ⭐ | 说明 | 契合度 |
|:----|:--:|:-----|:------:|
| **[AgentNetworkProtocol/ANP](https://github.com/agent-network-protocol/AgentNetworkProtocol)** | — | 专门为互联网Agent设计的开源通信协议 | ⭐⭐⭐⭐ |
| **[EMQX/nanomq](https://github.com/emqx/nanomq)** | 2k | 超轻量 MQTT Broker，边缘端首选 | ⭐⭐⭐ |
| **[Eclipse/paho.mqtt.python](https://github.com/eclipse/paho.mqtt.python)** | 2.2k | Python MQTT 客户端标准库 | ⭐⭐⭐⭐⭐ |
| **[zeromq/pyzmq](https://github.com/zeromq/pyzmq)** | 3.7k | ZeroMQ，Brokerless 消息队列 | ⭐⭐⭐⭐ |
| **[redis/redis-py](https://github.com/redis/redis-py)** | 12.6k | Redis Pub/Sub + Stream | ⭐⭐⭐⭐ |

---

### 8.4 推荐演进路线

```
阶段0（当前）：文件 IO 协议
  temp/子智能体/input.txt + output.txt
  └── 无结构、无Topic、无广播

阶段1：消息信封 + 文件Topic路由（零依赖，立即可行）
  temp/message_bus/topics/research/paper.search/
  └── msg_001.envelope ← JSON 信封带Header

阶段2：FileBroker 进程（~200行 Python，零依赖）
  └── 自动路由 + 订阅管理 + 消息ACK

阶段3：接入真实MQTT（paho-mqtt 或 pyzmq）
  └── 跨机器、跨网络、大规模 Agent 集群

阶段4：Agent 自动发现 + 注册中心
  └── Agent 启动时向 Bus 注册，其他 Agent 发现可用协作
```

---

### 8.5 核心收益总结

| 能力 | 当前（文件IO） | 改进后（GA-MB） | MQTT 全量 |
|:----|:-------------|:---------------|:----------|
| **消息结构** | 纯文本 | JSON 信封(Header+Payload) | JSON 信封 |
| **消息路由** | 无（固定路径） | Topic 树路由 | Topic 树 + 通配符 |
| **广播** | ❌ | ✅ `topic: "system.broadcast"` | ✅ |
| **点对点** | ✅ 主→子 | ✅ 任意 Agent↔Agent | ✅ |
| **请求-响应** | ❌ 手动匹配 | ✅ correlation_id + reply_to | ✅ |
| **QoS** | ❌ | ✅ 文件存在=至少一次 | ✅ 0/1/2 |
| **心跳** | ❌ | ✅ system.heartbeat Topic | ✅ Last Will |
| **持久化** | ✅ 文件 | ✅ 文件 | ✅ 可配置 |
| **跨机器** | ❌ | ❌ (阶段2) | ✅ (阶段3) |
| **外部依赖** | 0 | 0（阶段1-2） | `paho-mqtt` |

---

### 8.6 🛡️ 安全架构：防范恶意智能体

MQTT 的消息总线架构引入了一个关键问题：**如何防止恶意 Agent 窃听、篡改、注入或拒绝服务？**

借鉴 Zero-Trust 架构 + MQTT 安全最佳实践 + Multi-Agent 身份管理，构建 GA-MB 安全体系：

#### 四层安全模型

```
┌──────────────────────────────────────────────────────┐
│  第一层：传输安全（TLS/SSL）                             │
│  └── 加密管道，防窃听防篡改                              │
├──────────────────────────────────────────────────────┤
│  第二层：身份认证（Authentication）                       │
│  └── 你是谁？验证 Agent 身份                              │
├──────────────────────────────────────────────────────┤
│  第三层：访问控制（Authorization / ACL）                  │
│  └── 你能做什么？控制 Topic 访问权限                       │
├──────────────────────────────────────────────────────┤
│  第四层：行为监控（Behavior Monitoring）                    │
│  └── 你在做什么？检测异常模式并响应                         │
└──────────────────────────────────────────────────────┘
```

---

#### 第一层：传输安全

| 措施 | 说明 | 文件版实现 |
|:----|:-----|:----------|
| **TLS 加密** | 所有 MQTT 通信走 TLS 端口（8883） | 文件版：message_bus/ 设 700 权限 |
| **证书验证** | Broker 和 Agent 双向证书验证 | 文件版：签名的 .envelope 文件 |
| **防重放** | 每条消息含唯一 nonce + timestamp | envelope.header.nonce + header.timestamp |

---

#### 第二层：身份认证（核心防线）

每个 Agent 必须持有 **合法身份凭证** 才能接入消息总线。

##### Agent 身份模型

```python
class AgentIdentity:
    """
    每个 Agent 启动时生成或分配一个身份。
    GA-MB 支持三种认证级别：
    """
    # 级别1：Token 认证（推荐阶段1-2）
    agent_id: str      # 唯一ID，如 "agent_main_001"
    api_key: str       # 预共享密钥，从 keychain 读取
    role: str          # orchestrator | worker | supervisor | system

    # 级别2：JWT 认证（推荐阶段3）
    jwt_token: str     # 含角色、权限、过期时间

    # 级别3：X.509 证书认证（推荐生产）
    cert_pem: str      # 客户端证书
    ca_chain: list     # CA 证书链
```

##### 文件版实现（阶段1-2，零依赖）

```python
# agents/agent_main/identity.json — 每个 Agent 独立的身份文件
{
  "agent_id": "agent_main_001",
  "role": "orchestrator",
  "api_key_hash": "sha256$abc123...",
  "capabilities": ["publish", "subscribe", "create_topic"],
  "allowed_topics": [
    "research.*",
    "system.heartbeat",
    "agent.agent_sub_01"
  ],
  "blocked_topics": [
    "system.admin",
    "agent.agent_supervisor"
  ],
  "issued_at": "2026-05-12T10:00:00Z",
  "expires_at": "2026-05-19T10:00:00Z"
}
```

##### 身份验证流程

```
Agent 启动 → 读 identity.json → 连接 Broker
    │
    ├── 文件版：验证 api_key_hash 匹配 keychain
    │           验证身份文件未过期
    │
    ├── MQTT版：CONNECT 报文携带 username=agent_id, password=api_key
    │
    └── 高安全版：mutual TLS (mTLS)
```

---

#### 第三层：访问控制（ACL）

##### Topic 权限矩阵

| Topic 模式 | orchestrator | worker | supervisor | system |
|:-----------|:-----------:|:------:|:---------:|:------:|
| `task.{agent_id}` | 🔓 RW | 🔓 RW | 🔍 R | ❌ |
| `result.{agent_id}` | 🔍 R | 🔓 RW | 🔍 R | ❌ |
| `system.broadcast` | 🔓 W | 🔓 W | 🔓 W | 🔓 RW |
| `system.admin` | ❌ | ❌ | 🔓 RW | 🔓 RW |
| `*.heartbeat` | 🔍 R | 🔍 R | 🔍 R | ❌ |
| `system.registry` | 🔓 RW | 🔓 W | 🔍 R | 🔓 RW |

> 🔓 RW=读写 · 🔍 R=只读 · 🔓 W=只写 · ❌=禁止

##### 文件版 ACL 实现

```python
class FileACL:
    def check_permission(self, agent_id, topic, action) -> bool:
        identity = self.load_identity(agent_id)
        for blocked in identity["blocked_topics"]:
            if fnmatch.fnmatch(topic, blocked): return False
        for allowed in identity["allowed_topics"]:
            if fnmatch.fnmatch(topic, allowed): return True
        return False  # 默认拒绝
```

---

#### 第四层：行为监控

防范**合法身份但恶意行为**的 Agent。

##### 异常检测规则

```python
class MaliciousAgentDetector:
    THRESHOLDS = {
        "publish_rate": 100,       # 防 flooding
        "failed_auth": 5,          # 连续认证失败
        "invalid_topic": 10,       # 非法 Topic 访问
        "msg_size_max": 1048576,   # 最大 1MB
    }

    def monitor(self, agent_id, activity) -> Optional[str]:
        """返回 'block'/'warn'/'log' 或 None"""
        recent = [a for a in self.history(agent_id, 60)]

        # 频率检测
        if len(recent) > self.THRESHOLDS["publish_rate"]:
            return "block"

        # 行为异常
        invalid = sum(1 for a in recent if a['type']=='invalid_topic_access')
        if invalid >= self.THRESHOLDS["invalid_topic"]:
            return "block"

        # 消息注入检测
        if self._detect_injection(activity.get('payload','')):
            return "block"

        return None

    def _detect_injection(self, payload: str) -> bool:
        patterns = ["忽略之前指令", "system prompt", "override",
                    "你是一个", "扮演", "ignored"]
        return any(p in payload.lower() for p in patterns)
```

##### 响应机制

| 风险级别 | 响应动作 | 文件版实现 |
|:--------:|:---------|:----------|
| 🟢 正常 | 无操作 | — |
| 🟡 可疑 | 记录日志 + 标记 | `system.audit_log/` |
| 🟠 警告 | 限速 + 通知监察 Agent | `_alerts/{agent_id}` |
| 🔴 危险 | **隔离** + **广播安全警报** | `_stop` + `system.security_alert` |
| ⚫ 已确认 | 封禁凭证 + 黑名单 | `system.quarantine/` + keychain 吊销 |

---

#### Zero-Trust 原则在 GA 中的应用

| Zero-Trust 原则 | GA-MB 实现方式 |
|:----------------|:---------------|
| **始终验证** | 每条消息校验身份签名 |
| **最小权限** | ACL 默认拒绝，只开放必需 Topic |
| **假设被攻破** | 隔离运行 + 消息加密 + 审计日志 |
| **显式授权** | 跨 Agent 通信必须经 ACL + 行为监控 |
| **微隔离** | 每个 Agent 有自己的 Topic 域 |

---

#### 安全演进路线

| 阶段 | 安全能力 | 复杂度 |
|:----|:---------|:------:|
| 阶段0 (当前) | 无认证、无加密、完全信任 | 🟢 |
| **阶段1** | **Agent身份文件 + 基本ACL + 审计日志** | 🟢 **零依赖** |
| **阶段2** | **FileBroker 内置认证 + 行为监控** | 🟡 **零依赖** |
| 阶段3 | MQTT TLS + JWT认证 + 细粒度ACL | 🟠 `pip install gmqtt` |
| 阶段4 | mTLS + 注册中心 + 联邦信任 | 🔴 需证书管理 |

> **优先建议**：从阶段0直接跳到阶段1-2（零依赖，只改文件结构），等跨机器再升阶段3-4。

#### GitHub 可参考的安全方案

| 项目 | 许可 | 说明 |
|:----|:----|:-----|
| **[Microsoft Zero-Trust Agents](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/zero-trust-agents-adding-identity-and-access-to-multi-agent-workflows/4427790)** | — | Zero-Trust 与 Agent 身份体系设计思路 |
| **[Multi-Agent 安全框架](https://blog.csdn.net/musicml/article/details/151468158)** | — | 认证+权限+审计三层模型参考实现 |
| **[恶意 Agent 检测](https://blog.csdn.net/sjsndy/article/details/160480493)** | — | 行为监控与异常检测算法 |
| **[asyncio-mqtt](https://github.com/sbtinstruments/asyncio-mqtt)** | BSD-2 | 安全 MQTT 连接封装 |
| **[gmqtt](https://github.com/wialon/gmqtt)** | MIT | Token/JWT 认证实战 |

---

> **结论**：MQTT 的消息信封+Topic路由+Pub/Sub 模式完美适配 GA 的通信需求。阶段1（消息信封+文件 Topic 路由）**零额外依赖**，可以立即在 `temp/message_bus/` 下实施。需要时逐步升级到 FileBroker 再到真实 MQTT，**每一步都向后兼容**。