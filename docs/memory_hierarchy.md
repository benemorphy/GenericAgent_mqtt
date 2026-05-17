# 记忆层级 L1~L4 目录映射

> **生成时间**: 2026-05-08  
> **来源**: `memory_management_sop.md` + 实际目录验证

---

## 层级 → 路径映射表

| 层级 | 说明 | 路径（基于 `../memory/`） | 实际绝对路径 |
|------|------|---------------------------|-------------|
| **L0** | 元规范 (META-SOP) | `../memory/memory_management_sop.md` | `D:\open_claw_agent\GenericAgent\memory\memory_management_sop.md` |
| **L1** | 极简索引层 (≤30行) | `../memory/global_mem_insight.txt` | `D:\open_claw_agent\GenericAgent\memory\global_mem_insight.txt` |
| **L2** | 事实库层 | `../memory/global_mem.txt` | `D:\open_claw_agent\GenericAgent\memory\global_mem.txt` |
| **L3** | 记录库层 | `../memory/` 下所有 `.md` / `.py` 文件（非 L0/L1/L2 的其余文件） | `../memory/*.md`, `../memory/*.py` 及子目录 |
| **L4** | 历史会话层 | `../memory/L4_raw_sessions/` | `D:\open_claw_agent\GenericAgent\memory\L4_raw_sessions/` |

---

## 实际目录快照

```
D:\open_claw_agent\GenericAgent\memory/
├── 📄 memory_management_sop.md          ← L0（元规范）
├── 📄 global_mem_insight.txt            ← L1（极简索引）
├── 📄 global_mem.txt                    ← L2（事实库）
├── 📄 *.md / *.py  (其余文件)           ← L3（记录库）
│   ├── keychain.py
│   ├── ljqCtrl.py / ljqCtrl_sop.md
│   ├── metaso_search.py / tmwebdriver_sop.md
│   ├── vision_sop.md / ocr_utils.py
│   ├── plan_sop.md / subagent.md / ...
│   └── 📁 skill_search/ 等子目录
└── 📁 L4_raw_sessions/                  ← L4（历史会话）
    └── compress_session.py
```

---

## 各层职责速览

| 层级 | 特征 | 核心职责 |
|------|------|----------|
| **L0** | META-SOP，92行 | 定义记忆管理的元规则（行动验证、不可删改、最小指针等） |
| **L1** | 文本文件，≤30行硬约束 | 为 L2/L3 提供极简导航索引，高频场景→文件名的映射 |
| **L2** | 文本文件，可膨胀 | 存储全局环境性事实（路径、凭证、配置、常量） |
| **L3** | 多个 .md / .py 文件 | SOP 操作步骤、工具封装、子智能体定义 |
| **L4** | 目录，含压缩脚本 | 历史会话自动收集，供回溯上下文 |

---

## 规范须知

- 修改 L1/L2 只能用 `file_patch` 少量修改，禁止 overwrite 或 code run
- 写任何记忆前需先读 META-SOP（L0）核验
- L2/L3 变更时需同步更新 L1 索引行
- L4 由 scheduler 自动反射收集，无需手动管理