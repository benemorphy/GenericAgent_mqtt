# MQTT_BBS 实现 Goal Hive 方案 — 2026-05-29

基于 GenericAgent Goal Hive 机制的 MQTT 原生实现计划。

## 现状

### GenericAgent Goal Hive 架构
- Agent BBS(HTTP FastAPI + SQLite)
- Master: reflect/goal_mode.py (独立进程, HTTP轮询BBS)
- Workers: reflect/agent_team_worker.py (独立进程, HTTP轮询BBS)
- 人工选PORT, 人工管理 session

### 当前 MQTT_BBS 已有能力
- BoardService (MQTT broker :1883) 运行中
- MQTT BBS协议: BoardClient (注册/发帖/查询/MQTT pub-sub)
- WorkerAgent (reflect/agent_team_worker.py) 已实现MQTT接单
- Goal Mode (reflect/goal_mode.py) 单Agent持续模式
- Slash命令注册 (tools/slash_cmd_registry.py)
- Mqtt_bbs_server PluginManager

## 三组件 + 一协议

```
/goalhive <目标描述> [--timeout <分钟>] [--workers <数量>]
```

### MQTT 主题拓扑 (Hive Session 空间)

hive/{session_id}/post/         # BBS公告板帖子
hive/{session_id}/task/         # 子任务队列
hive/{session_id}/task/{id}/    # 具体子任务
hive/{session_id}/status/       # Master状态广播
hive/{session_id}/worker/       # Worker心跳/注册 (含Last Will)

利用MQTT retain持久化状态, 无需SQLite。利用Last Will检测worker崩溃。

### 1. tools/slash_hive.py — /goalhive 命令处理器
- 生成 session_id (hive_{timestamp}_{uuid[:4]})
- 创建 temp/hive_{session_id}/ 工作目录
- 用BoardClient在 hive/{id}/post/ 发第一帖 (任务目标+Master职责)
- 后台启动master: start /b python agentmain.py --reflect reflect/hive_master.py
- 后台启动workers: start /b python agentmain.py --reflect reflect/agent_team_worker.py --hive {id}
- 报告用户后退出当前进程

### 2. reflect/hive_master.py — Hive Master 反射脚本
- 启动时读 hive session 配置
- 订阅 hive/{id}/post/ 查看worker产出
- 在 hive/{id}/task/ 发布子任务
- 定期在 hive/{id}/status/ 广播进度
- 循环: 验收 -> 纠偏 -> 再派发 (同GenericAgent Master duty)
- 通过 done_prompt 收尾

### 3. reflect/agent_team_worker.py 修改
- 新增 --hive 参数: 传入 hive session id
- 有 hive id → 只订阅 hive/{id}/task/ 空间 (隔离)
- 无 hive id → 原样全局接单
- 其余复用现有 MQTT WorkerAgent 逻辑

## 实施路线

### P1: /goalhive 命令 + session启动
新文件: tools/slash_hive.py (1文件)
注册到 slash_cmd_registry

### P2: Hive Master reflect脚本
新文件: reflect/hive_master.py (1文件)
实现调度/验收/纠偏循环

### P3: Worker hive隔离适配
修改: reflect/agent_team_worker.py (小改)
hive 模式隔离 topic 空间

### P4: GA版 goal_hive_sop.md
新文件: memory/goal_hive_sop.md (1文件)
描述MQTT版Hive启动流程和主题协议
