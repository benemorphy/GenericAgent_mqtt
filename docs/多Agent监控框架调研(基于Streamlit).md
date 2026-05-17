# 多 Agent 监控框架调研（基于 Streamlit）

> 调研时间：2026-05-08
> 范围：支持或内置 Streamlit 监控面板的多 Agent 框架/工具

---

## 1. Agno（原 Phidata）

| 项目 | 说明 |
|:--|:--|
| **简介** | 全栈 Multi-Agent 框架，原生支持 Streamlit 构建监控面板，提供 Agent 运行时环境与可视化工具链 |
| **GitHub** | https://github.com/daavoo/agno |
| **文档** | https://docs.agno.com |

### 监控功能

- **Agent 运行状态监控** — 实时显示步骤数、成功操作数、数据提取量、执行时间
- **日志与追踪** — 记录 Agent 的详细执行过程
- **知识库与记忆管理** — 查看 Agent 的知识注入和记忆状态
- **Streamlit 面板** — 原生提供多列指标卡（`st.columns` + `st.metric`）

### 典型监控指标

```
执行步骤 | 成功操作 | 提取数据量 | 执行时间
```

---

## 2. Browser-Use

| 项目 | 说明 |
|:--|:--|
| **简介** | 浏览器自动化 Agent 框架，提供 Streamlit 数据可视化集成，用于监控自动化任务的执行状态 |
| **相关文章** | https://blog.csdn.net/gitblog_00151/article/details/151004474 |

### 监控功能

- **实时监控仪表板** — 使用 `st.columns` 展示核心指标
- **步骤状态分布图** — 饼图展示各状态占比（成功/失败/进行中）
- **执行统计**：
  - 执行步骤数
  - 成功操作数
  - 提取数据量
  - 总执行时间
- **Streamlit 命令**：`streamlit run streamlit_dashboard.py`

---

## 3. Trae Agent 监控系统

| 项目 | 说明 |
|:--|:--|
| **简介** | AI Agent 可观测性系统，基于 Streamlit 构建的 Web 监控 Dashboard |
| **功能覆盖** | 阿里云 AgentSight 同类方案 |

### 监控功能

- **Token 消耗可视化** — 按时间段查看 Token 消耗趋势
- **Agent 进程状态监控** — 实时监控 Agent 运行状态，支持异常重启
- **Session 链路追踪** — 深入查看每次 Session 的完整 Trace 链路
  - 用户输入
  - 模型提示词
  - 推理思考过程
  - 每步 Token 消耗分布
- **Web Dashboard** — 可部署在远程服务器，本地浏览器访问

---

## 4. AI Agents Masterclass 日志与监控系统

| 项目 | 说明 |
|:--|:--|
| **简介** | OpenAI Agents SDK 配套的日志与监控最佳实践，构建基于 Streamlit + Plotly 的实时监控界面 |
| **相关文章** | https://blog.csdn.net/gitblog_00895/article/details/151096255 |

### 监控功能

- **实时监控仪表板**
- **Token 用量追踪** — 记录每次 LLM 调用的 Token 消耗
- **错误分析** — 通过 `span.set_attribute` 记录成功/失败状态
- **性能可视化** — 集成 Plotly 图表展示趋势
- **OpenTelemetry 集成** — 使用 OTel 标准进行链路追踪

### 代码示例（核心逻辑）

```python
import streamlit as st
import pandas as pd
import plotly.express as px

def create_monitoring_dashboard():
    """创建实时监控仪表板"""
    st.title("AI Agent实时监控")
```

---

## 5. LangChain / LangGraph + StreamlitCallbackHandler

| 项目 | 说明 |
|:--|:--|
| **简介** | LangChain 生态内置 `StreamlitCallbackHandler`，可在 Streamlit 中实时可视化 Agent 的思考与行动过程 |
| **文档** | http://docs.autoinfra.cn/docs/integrations/callbacks/streamlit |

### 监控功能

- **实时 Agent 思维可视化** — 在 Streamlit 中实时展示 Agent 的思考链
- **工具调用可视化** — 逐个展示 Agent 调用的工具及结果
- **行动步骤追踪** — 逐步展示 Agent 从思考到行动的全过程
- **与 LangSmith 联动** — LangSmith 提供更完整的可视化调试与监控平台

### 使用方式

```python
from langchain.callbacks import StreamlitCallbackHandler
import streamlit as st

# 在 Streamlit 应用中直接传入回调
agent.run(input, callbacks=[StreamlitCallbackHandler(st.container())])
```

---

## 6. OpenAI Agents SDK（内置追踪 + Streamlit 集成）

| 项目 | 说明 |
|:--|:--|
| **简介** | OpenAI 官方 Agents SDK，内置追踪（Tracing）功能，可通过 Streamlit Dashboard 展示运行状态 |
| **相关文章** | https://www.hubwiz.com/blog/unpacking-openai-agents-sdk/ |

### 监控功能

- **内置追踪** — 自动记录 Agent 循环和工具调用
- **OpenAI Dashboard** — 官方仪表板可视化 Agent 行为
- **Trace & Span 分解** — 将每个 Agent 循环拆解为 trace 和 span
- **性能瓶颈分析** — 帮助识别延迟、错误和优化点
- **OpenTelemetry 集成** — 通过 Pydantic Logfire SDK 导出到 Application Insights 等后端

---

## 7. Langfuse（LLM 可观测性平台）

| 项目 | 说明 |
|:--|:--|
| **简介** | LLM 应用可观测性平台，可集成到多 Agent 框架中（如 Agno/Phidata），提供监控与分析能力 |
| **官网** | https://langfuse.com |
| **集成示例** | https://blog.gitcode.com/6fc5fb6497b6c2e92824553cfb002f9a.html |

### 监控功能（非 Streamlit 原生，但可集成）

- **LLM 调用追踪** — 监控模型 API 调用、用户输入、提示词、输出
- **Prompt 管理** — 版本控制与管理提示词
- **评估与指标** — 对 Agent 输出进行质量评估
- **成本分析** — 跟踪 Token 消耗和模型定价

---

## 8. AgentSight（eBPF 可观测性）

| 项目 | 说明 |
|:--|:--|
| **简介** | 基于 eBPF 的 AI Agent 可观测性工具，提供 Web Dashboard 可视化 |
| **文档** | https://help.aliyun.com/zh/alinux/how-to-use-agentsight |

### 监控功能

- **Token 消耗趋势** — 按时间段查看机器的 Token 消耗趋势
- **Agent 进程状态** — 实时监控并提供异常重启能力
- **Session 详情** — 完整 Trace 链路（输入 → 提示词 → 推理 → Token 分布）

---

## 总结对比

| 框架/工具 | Streamlit 原生支持 | 核心监控维度 | 开源 | 适用场景 |
|:--|:--:|:--|:--:|:--|
| **Agno** | ✅ 原生 | Agent 状态、执行步骤、数据量、执行时间 | ✅ | 通用多 Agent 系统 |
| **Browser-Use** | ✅ 原生 | 步骤、成功操作、数据量、时间、状态分布 | ✅ | 浏览器自动化 Agent |
| **Trae Agent** | ✅ 原生 | Token 消耗、进程状态、Session 链路 | ❓ | AI Agent 可观测性 |
| **AI Agents Masterclass** | ✅ 原生 | Token 用量、错误分析、性能趋势 | ✅ | OpenAI Agents SDK |
| **LangChain/LangGraph** | ✅ StreamlitCallbackHandler | 思维链、工具调用、行动步骤 | ✅ | LangChain 生态 |
| **OpenAI Agents SDK** | ⚡ 可集成 | 内置追踪、Trace/Span、性能瓶颈 | ✅ | OpenAI Agent 开发 |
| **Langfuse** | ⚡ 可集成 | LLM 调用、Prompt 管理、评估、成本 | ✅ | LLM 可观测性 |
| **AgentSight** | ❌ Web 自有 UI | Token 趋势、进程、Session Trace | ❌ | 生产环境可观测性 |

> **说明：** ✅ 原生支持 = 框架自带 Streamlit 监控面板或专门提供 Streamlit 集成方案；  
> ⚡ 可集成 = 框架本身不依赖 Streamlit，但社区有配套的 Streamlit Dashboard 示例或可对接。

---

## 关键趋势

1. **Streamlit 已成为 Agent 监控面板的首选前端** — 轻量、Python 原生、开发快
2. **监控指标趋同** — 大多聚焦于：执行步骤数、Token 消耗、成功率/错误率、执行时间
3. **OpenTelemetry 成为底层标准** — 多数框架通过 OTel 导出追踪数据
4. **链路追踪（Tracing）是核心能力** — 从用户输入 → Agent 思考 → 工具调用 → 输出的完整链路