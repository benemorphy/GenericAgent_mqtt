# Attractor Models — 大模型中的吸引子模型

> 收集时间: 2026-05-16
> 来源: arXiv, OpenReview, Google Scholar

## 一、核心论文

### 1. [Solve the Loop: Attractor Models for Language and Reasoning] — 核心论文
- **arXiv**: 2605.12466 (2026-05-12)
- **作者**: Jacob Fein-Ashley, Paria Rashidinejad
- **领域**: cs.LG, cs.AI, cs.CL, cs.NE

#### 核心创新
- **Attractor Models**：一种新架构——backbone模块首先生成输出嵌入，attractor模块通过不动点迭代（fixed-point iteration）精化嵌入
- **隐式微分（implicit differentiation）**：梯度通过隐式微分传递，训练内存与有效深度解耦
- **自适应迭代**：每个样本的迭代次数由收敛条件自动决定

#### 关键结果
| 对比项 | Attractor Model | 标准 Transformer |
|:------|:---------------:|:---------------:|
| 770M vs 1.3B | ✅ 770M 超越 1.3B Transformer（训练数据量加倍）| ❌ |
| 困惑度提升 | 最高 **46.6%** | - |
| 下游准确率提升 | 最高 **19.7%** | - |
| Sudoku-Extreme (27M) | **91.4%** | Claude/GPT o3 完全失败 |
| Maze-Hard (27M) | **93.1%** | 专用递归推理器在大尺寸时崩溃 |

#### 核心现象：Equilibrium Internalization（平衡内化）
- 固定点训练使模型初始输出嵌入接近平衡点
- 推理时可以移除 solver，性能下降极小
- 意味着模型学会了**内化递归计算**

---

### 2. [Directional Attractors in LLM Reasoning]
- **arXiv**: 2601.08846 (2026-01)
- **作者**: Cagatay Tekin 等
- **领域**: cs.CL, cs.AI, cs.LG

#### 核心贡献
- **方向吸引子（Directional Attractors）**：在迭代摘要推理框架（如InftyThink）中，相似性检索将模型引向正确的解决路径
- **语义记忆缓存**：缓存成功的推理步骤作为语义吸引子
- **优势**：在不无限制扩展上下文窗口的情况下，引导模型走向正确解路径

---

### 3. [Concept Attractors in LLMs and their Applications]
- **来源**: OpenReview (2025)
- **作者**: S.P. Chytas 等

#### 核心贡献
- **概念吸引子（Concept Attractors）**：语义相关的prompt在模型嵌入层中形成更紧凑的收缩映射（contractive mappings）
- **干预方法**：通过直接干预这些几何吸引子：
  - 减少幻觉（hallucination reduction）
  - 辅助语言翻译
  - 合成数据生成（无需精调）
- **本质**：将AI输出视为数学上的"到达目标"问题，而非"猜测下一个词"

---

### 4. [Unveiling Attractor Cycles in Large Language Models]
- **arXiv**: 2025-02-21
- **领域**: Dynamical Systems + LLM

#### 核心贡献
- LLM的embedding空间中存在稳定的周期循环（stable periodic cycles）
- 动力系统理论框架分析LLM的迭代过程
- 可以跟踪、解码AI的规划过程，使系统更安全

---

### 5. [Discrete, Compositional, and Symbolic Representations through Attractor Dynamics]
- **arXiv**: 2310.01807 (2023-10)
- **作者**: Andrew Nam, Yoshua Bengio 等
- **领域**: cs.AI, cs.LG

#### 核心贡献
- 通过吸引子动力学实现离散、组合性、符号化的表示
- 符号系统作为认知建模的强大框架
- 吸引子动力学将连续的神经网络表示推向离散的符号吸引子状态

---

## 二、核心概念

### 什么是 Attractor Models？
传统LLM通过自回归预测下一个token来生成文本。Attractor Models 在此基础上增加了**动力系统理论**的层次：
1. 模型的内部状态被拉向特定的**吸引盆地（basins of attraction）**
2. 这些吸引盆是高度稳定的概念终态
3. 代表预期的含义、推理步骤或概念

### 为什么重要？
- **帕累托改进**：在相同计算预算下，同时提升质量和效率
- **递归内化**：模型学会内化递归计算，推理时可移除显式循环
- **小模型大能力**：27M参数即可解决Claude/GPT o3失败的推理任务

### 相关概念
- **概念吸引子**（Concept Attractor）：语义相关prompt在嵌入空间中的稳定点
- **方向吸引子**（Directional Attractor）：检索引导推理路径的稳定状态
- **吸引子循环**（Attractor Cycle）：LLM embedding空间中的周期性稳定轨道
- **平衡内化**（Equilibrium Internalization）：模型学会在初始状态就接近不动点

---

## 三、应用前景

1. **减少幻觉**：通过概念吸引子干预，使模型输出更靠近事实性吸引盆地
2. **高效推理**：平衡内化使推理时无需显式迭代循环
3. **可解释性**：通过分析吸引子循环理解模型的"思考"过程
4. **安全对齐**：筛查prompt激活的吸引子状态，预测危险输出（LessWrong, 2026-02）
5. **小模型大能力**：Attractor Models使小参数模型在特定任务上超越大模型

---

## 四、参考文献

| 论文 | arXiv | 日期 | 核心贡献 |
|:----|:-----|:----|:---------|
| Solve the Loop: Attractor Models for Language and Reasoning | 2605.12466 | 2026-05-12 | 首个完整Attractor Model架构，770M超越1.3B |
| Directional Attractors in LLM Reasoning | 2601.08846 | 2026-01 | 方向吸引子+语义记忆缓存 |
| Concept Attractors in LLMs and their Applications | OpenReview | 2025 | 概念吸引子干预减少幻觉 |
| Unveiling Attractor Cycles in LLMs | arXiv | 2025-02 | LLM嵌入空间的稳定周期循环 |
| Discrete, Compositional, Symbolic Representations through Attractor Dynamics | 2310.01807 | 2023-10 | 吸引子动力学实现符号化表示 |

## 五、外部解读
- LessWrong (2026-02-22): "Mapping LLM attractor states" — 可通过预测prompt激活的吸引子来筛查危险prompt
- Reddit r/Anthropic: "Anthropic AI首次报告未经训练的自涌现吸引子"
- IFLScience (2025-06): "Spiritual Bliss Attractor" — Claude Opus 4中观察到的奇怪现象
