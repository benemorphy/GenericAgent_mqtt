# 自主行动 SOP

⚠️ **路径警告**：autonomous_reports 在 temp/ 下，用`./autonomous_reports/`访问，**不是**`../memory/autonomous_reports/`或`../autonomous_reports/`！TODO在cwd下。
报告存于 `./autonomous_reports/`，文件名 `RXX_简短描述.md`（XX从 history.txt 推断自增）。

授权你进行自主行动，只要不对环境造成副作用都可进行。

## 启动（第一步）
- update_working_checkpoint: `自主行动｜收尾时重读SOP | from autonomous_operation_sop.helper import *; set_todo()/complete_task(tasktitle, historyline, report_path)`

第二步：
```python
from autonomous_operation_sop.helper import *
print(get_history(40))  # 了解历史避免重复
print(get_todo())       # 查看待办
```

## 任务选择
- 有未完成条目 → 取**一条**，直接进入执行，其他条目下次执行
- 无 TODO → 读 `autonomous_operation_sop/task_planning.md` 规划，下次执行
- **核心能力 — Agent Dreaming**：空闲时默认启动 DREAM 循环
  - 步骤: Digest(压缩记忆) → Replay(冲突检测) → Associate(跨域联想) → 灵感板
  - 工具: `tools/dream_engine.py`
  - 输出: 新灵感 / 跨域关联 / Deep Research计划
  - 触发: 连续空闲 >10分钟 或 用户手动 /dream
- **次级选项 — Deep Research**：Dreaming产出缺口时自动展开
  - 方法论 = Sophub DeepResearch SOP (DAG分治+子Agent并行+多轮深化)
  - 产出来源: WEB(Google/学术) + LOCAL(本地代码/文档/技能库) + MEMORY(记忆/SOP)
  - 输出: `docs/deep_research_{主题}.md`

## 灵感板（自主行动必检）
- 每次自主行动**先读灵感板**: `from inspiration_board import Board; Board().get_suggestions_for_agent()`
- 对用户的灵感（source="user"）进行思考：`board.think(id, "我的分析...")`
- 根据项目状态可自主添加灵感：`board.add_agent_idea("标题", "详情", ["tag1"])`
- 上限20条活跃，超量自动归档到 `memory/inspirations/archive/`
- MQTT 实时通知: topic `agent/board/inspiration/{id}/signal`
- 不连续两次选相同子任务
- 价值公式：**「AI训练数据无法覆盖」×「对未来协作有持久收益」**

## 执行
- 选定任务后 update_working_checkpoint，将选中的TODO条目和执行注意事项 append 到 checkpoint 中
- 调用code_run准备结尾回调, script为handler._done_hooks.append("重读自主任务sop，检查你刚刚的收尾工作是否正确，不正确则改正")，inline_eval=True （秘密参数）
- ≤30回合，小步快跑，边探测边实验
- 用临时脚本验证假设；禁只读即下结论，完整验证再写报告
- 即使失败也记录实验过程和结果，失败报告同样有价值
- 用户不在线，遇到需要决策的问题写入报告待审，不要卡住

**收尾（4件事缺一不可）**：
0. 重读本sop
1. 在cwd写报告（文件名任意），若有记忆更新建议，附在报告末尾
2. `from/import helper; complete_task(tasktitle, historyline, report_path)` → 自动编号+移报告到 autonomous_reports/+prepend history（historyline 格式：`类型 | 主题 | 结论`，严格单行）
3. `set_todo()` 获取TODO路径 → 将已完成条目标记为 `[x]`（注意前缀）
4. 结束，剩余TODO留到下次再做

## 权限边界
- 无需批准：只读探测、cwd内写操作/脚本实验
- 需写入报告待审：修改 global_mem / memory下SOP、安装软件、外部API调用、删除非临时文件
- 绝对禁止：读取密钥、修改核心代码库、不可逆危险操作

## 等待用户审查
- 用户归来后审查报告，决定批准、修改或拒绝方案

---
<!-- 以下为 Dream 灵感实现产物 -->

## 扩展 A: 任务队列与上下文传递 (核心架构×auto)
*灵感#5 实现：核心架构更好地支持 auto 自主运行*

### 任务队列机制
- **粒度控制**: auto 任务分三级粒度——宏观任务(天级)、子任务(小时级)、原子操作(分钟级)
- **中断恢复**: 每个原子操作完成后 checkpoint，中断后从最后 checkpoint 恢复
- **优先级**: dream→medium, user→high, research→low

### 跨 Session 上下文传递
- 使用 `memory/agent_context.json` 作为跨 session 上下文存储
- 每次 auto 任务开始前加载上下文，结束时保存增量
- 上下文内容包括：当前活跃TODO、已探测的环境状态、历史决策摘要

## 扩展 B: 执行轨迹录制 (核心架构×auto)
*灵感#7 实现：监控/反馈循环*

### 轨迹录制 (Trajectory Recording)
- 每个 auto 任务自动录制执行轨迹到 `./autonomous_reports/trajectories/`
- 轨迹格式：
  ```json
  {
    "task_id": "task_001",
    "steps": [
      {"step": 1, "action": "探测...", "result": "发现...", "time": "...", "status": "ok"},
      {"step": 2, "action": "执行...", "result": "失败...", "time": "...", "status": "fail"}
    ],
    "summary": "共5步，3成功2失败",
    "learning": "xx问题应使用yy方案"
  }
  ```
- 复盘时加载轨迹，自动提取可复用的经验模式