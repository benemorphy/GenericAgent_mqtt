# DataHub 金融风控相关数据集搜索结果

> 来源：https://fudankw.cn/search.html
> 搜索关键词：financial
> 搜索时间：2026-05-16
> 结果页数：共252页（每页10条，约2520个数据集）

---

## 第1页结果（共252页）

### 1. Financial (事件序列数据集)
- **任务类型**：high-frequency trading（高频交易）
- **描述**：金融市场交易或波动事件序列数据集，包含2种事件类型（如买入/卖出、价格突变），序列较长（平均2074，最长3319），总事件数约41.5万，反映金融市场的高频动态。
- **来源**：arXiv:2112.13058 (2021)
- **关联风险控制领域**：高频交易风险监控、市场微观结构分析

### 2. Financial Concepts Dataset (Company Disclosures)
- **任务类型**：Capital classification（资本分类）
- **描述**：540条来自S&P 500公司10-K年报的标注句子，覆盖6种金融资本类型（由国际综合报告框架定义）。
- **来源**：arXiv:2311.08704 (2023)
- **关联风险控制领域**：企业财务披露分析、财务健康度评估

### 3. Financial dataset from a high-tech bank
- **任务类型**：Wealth Management（财富管理）
- **描述**：来自金融科技（FinTech）银行的专有数据集，用于客户识别任务，预测用户是否愿意参与财富管理产品。
- **来源**：arXiv:2405.18708 (2024)
- **关联风险控制领域**：银行客户风险画像、金融产品风控

### 4. Financial Variables Dataset (Compustat + SEC)
- **任务类型**：Bankruptcy prediction（破产预测）
- **描述**：5个已知预示破产的关键财务比率的结构化数据集：WC（营运资本/总资产）、RE（留存收益/总负债）、EBIT/总资产、MVE/总负债、SALE/总资产。
- **来源**：arXiv:2312.03194 (2023)
- **关联风险控制领域**：企业破产风险预测、信用风险评估

### 5. Financial Time-Series Dataset
- **任务类型**：Portfolio Allocation（投资组合配置）
- **描述**：真实金融市场数据，包含资产收益时间序列，用于构建样本协方差矩阵以进行精度矩阵估计。
- **来源**：arXiv:2112.01939 (2021)
- **关联风险控制领域**：投资组合风险建模、金融时间序列风险预测

### 6. Financially Augmented Instruction Dataset
- **任务类型**：Earnings report analysis（财报分析）
- **描述**：从英伟达(NVDA)和 AMD 2023年Q3财报中生成的800条定制金融指令数据集，用于指令微调。
- **来源**：arXiv:2412.08179 (2024)
- **关联风险控制领域**：财报自动化分析、风险信号提取

### 7. Financial Phrasebank
- **任务类型**：Finance Sentiment Analysis（金融情感分析）
- **描述**：广泛使用的金融情感分析标注数据集（Malo et al., 2014），包含来自金融新闻的句子及情感标签（正面/负面/中性）。
- **来源**：arXiv:2111.00526 (2021)
- **关联风险控制领域**：市场情绪分析、舆情风险监测

### 8. Financial Sentiment Classification Dataset
- **任务类型**：Financial Sentiment Analysis（金融情感分析）
- **描述**：5,845个样本的三分类金融情感数据集（中性2,879、正面1,362、负面604）。
- **来源**：arXiv:2512.00630 (2025)
- **关联风险控制领域**：细粒度金融情感分析、风险信号识别

### 9. Financial Abbreviation Dataset
- **任务类型**：Abbreviation Recognition（缩略语识别）
- **描述**：从Wikipedia随机选取的192个金融缩略语数据集，用于评估LLM正确展开金融缩写的能。
- **来源**：arXiv:2311.15548 (2023)
- **关联风险控制领域**：金融文档解析、实体识别

### 10. Financial Corpus
- **任务类型**：Financial news classification（金融新闻分类）
- **描述**：大规模金融数据集，包含 **239亿token**（约165亿词），用于领域自适应持续预训练。
- **来源**：arXiv:2110.06696 (2021)
- **关联风险控制领域**：金融领域大模型预训练、风控知识图谱构建

---

## 按风险控制子领域分类

| 子领域 | 相关数据集 |
|--------|-----------|
| 高频交易风险监控 | Financial (事件序列), Financial Time-Series |
| 企业破产/信用风险 | Financial Variables Dataset, Financial Concepts |
| 银行客户风控 | Financial dataset (high-tech bank) |
| 舆情/情感风险 | Financial Phrasebank, Financial Sentiment |
| 财报分析自动化 | Financial Concepts, Financially Augmented Instruction |
| 金融大模型/知识图谱 | Financial Corpus, Financial Abbreviation |

---

## 备注

- 所有数据集均来源于 ArXiv 开放论文，可通过 DOI 链接或 HuggingFace 获取
- 数据集平台：DataHub（复旦大学知识工场实验室）— https://fudankw.cn
