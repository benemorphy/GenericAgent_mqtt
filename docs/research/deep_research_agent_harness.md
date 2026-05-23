# Deep Research: Agent Harness 最新进展 (2025-2026)

> WEB节点: Google (The New Stack/OpenAI/Medium/GitHub/arXiv/Preprints/Northflank/DevOps.com)
> 方法论: Sophub DeepResearch SOP (DAG分治+多源合成)

---

## 1. Agent Harness 定义

> **Agent Harness = 把LLM变成生产级Agent的编排层**：管理推理循环、工具调用、上下文压缩、会话持久化、安全沙箱。

## 2. 2025-2026 关键演进

| 方向 | 进展 | 代表 |
|:-----|:------|:------|
| 架构分离 | 编排Harness与计算环境解耦 | OpenAI Agents SDK |
| 沙箱执行 | 原生沙箱隔离代码执行 | OpenAI Sandbox / E2B MicroVM |
| 多Agent编排 | 有状态图调试+HITL中断 | LangGraph |
| A2A协议 | Agent间审批+工具边界控制 | Agent-2-Agent |
| 上下文管理 | 自动压缩+窗口管理 | 模型原生Harness |

## 3. 主流框架对比

| 框架 | 定位 | 核心特性 | 开源 |
|:-----|:------|:---------|:----:|
| **LangGraph** | 生产级多Agent | 有状态图/HITL/调试 | ✅ |
| **OpenAI Agents SDK** | 官方Harness | 模型原生/沙箱/A2A | ✅ |
| **Claude Agent SDK** | Anthropic官方 | 推理循环/工具治理 | ✅ |
| **CrewAI** | 多Agent协作 | 角色分工/讨论Agent | ✅ |
| **AutoGen/AG2** | 学术研究 | 辩论Agent/复杂workflow | ✅ |
| **E2B** | 沙箱即服务 | MicroVM隔离/无状态 | ⚠️ 商业 |

## 4. Agent Harness 核心能力

```
┌────────────────────────────────────────┐
│           Agent Harness                 │
│                                        │
│  ┌──────┐ ┌──────┐ ┌────────┐         │
│  │推理循环│ │工具管理│ │上下文压缩│        │
│  └──────┘ └──────┘ └────────┘         │
│  ┌──────────┐ ┌──────┐ ┌─────────┐    │
│  │会话持久化  │ │安全沙箱│ │HITL审批 │    │
│  └──────────┘ └──────┘ └─────────┘    │
│  ┌──────────┐ ┌───────────┐           │
│  │多Agent编排│ │A2A协议治理 │           │
│  └──────────┘ └───────────┘           │
└────────────────────────────────────────┘
```

## 5. 安全沙箱方案

| 方案 | 隔离级别 | 适用场景 | 厂商 |
|:-----|:---------|:---------|:-----|
| **MicroVM (Firecracker)** | 硬件级 | 多租户云端 | E2B |
| **Kata Containers** | 硬件级 | 企业私有云 | 开源 |
| **gVisor** | 内核级 | 大规模自动缩放 | Modal |
| **Bubblewrap** | 用户态 | 本地开发 | 开源 |
| **Docker沙箱** | 容器级 | 企业on-prem | ClaudeBox |

## 6. 与GenericAgent的映射

| Agent Harness 能力 | GenericAgent 对应 |
|:-------------------|:------------------|
| 推理循环 | agentmain.py / agent_loop.py |
| 工具管理 | tools/ 目录 + skill_search |
| 上下文压缩 | Agent Dreaming + memory系统 |
| 会话持久化 | MQTT BBS + MariaDB persistence |
| 安全沙箱 | PII Masker / 本地VLM / 不联网 |
| HITL审批 | tools/hitl_approval.py + 飞书Bot |
| 多Agent编排 | MAS + AgentBoardWithPersistence |

---

> 基于 Sophub DeepResearch SOP | 参考: OpenAI SDK / LangGraph / E2B / ArXiv Preprints 2026