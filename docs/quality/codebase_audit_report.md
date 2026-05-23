# 代码库反省审计报告

> 生成日期: 2026-05-21
> 范围: GenericAgent_mqtt 全仓库扫描

---

## P0 — 已跟踪文件（推荐删除）

### `=` (0 字节)
- 空文件，git历史显示是误提交的产物，完全无用

### `talking.md` (203 字节)
- 内容："你是一位上海的高中语文老师..."——用户个人角色描述，非项目文档

### `README_CN.md` (18 KB)
- 独立的纯中文README，但**无任何文件引用**（`git grep` 结果为0）
- `README.md` 已是中英双语版（包含完整中文章节），此文件完全冗余

### `docs/` (22个文件, ~120 KB)
- 设计文档目录，虽已加 `.gitignore`，但因历史遗留被git跟踪
- 应取消跟踪（`git rm -r --cached`）

---

## P1 — 本地冗余/废弃（gitignore忽略，仅本地）

| 路径 | 大小 | 说明 |
|------|------|------|
| `CLEAR=1/` | ~0 MB | 废弃的Python虚拟环境（uv创建），不在.gitignore中 |
| `images/` | ~1.3 MB | 含个人照片（陈晖.jpg、陈诺.jpg）和截图，已在gitignore |
| `Snapshots/` | 10 KB | 单个截图，已在gitignore |
| `temp_tools/imgbed.py` | 1.8 KB | 废弃的临时图床工具及日志 |

---

## P2 — mykey 变体泛滥

| 文件 | 行数 | 与 mykey.py 重复 |
|------|------|-----------------|
| `mykey_internet.py` | 481行 | **99%** (366/369行相同) |
| `mykey_template.py` | 426行 | **90%** (334/369行相同) |
| `mykey_inner.py` | 122行 | 内网部署配置变体 |
| `mykey_inner_vlm.py` | 77行 | VLM部署配置变体 |
| `mykey_template_en.py` | 77行 | 英文模板 |

建议: 删除 `mykey_internet.py`（与 `mykey.py` 几乎完全一致）

---

## P3 — memory/ SOP 索引遗漏

以下11个SOP文件存在但未收录到 `global_mem_insight.txt`:

- aesthetic_design_sop
- clipboard_ocr_sop
- code_review_principles
- dream_command_rule
- emqtt_design_principles
- github_contribution_sop
- goal_mode_sop
- procmem_scanner_sop
- qq_deploy_sop
- search_skills_sop
- shutdown_rule
- supervisor_sop
- verify_sop
- vue3_component_sop
- web_testing_sop

---

## P4 — tools/ 中无外部引用的模块

| 文件 | 行数 | 有main | 说明 |
|------|------|--------|------|
| brainstorm_swarm.py | 186 | 是 | 群脑风暴工具 |
| failure_tracker.py | 378 | 是 | 失败追踪器 |
| ffmpeg_utils.py | 113 | 是 | FFmpeg工具 |
| file_sync_agent.py | 127 | 是 | 文件同步Agent |
| learning_log.py | 347 | 是 | 学习日志 |
| lint_filenames.py | 94 | 是 | 文件名检查 |
| md_server.py | 349 | 是 | Markdown服务器 |
| pii_masker.py | 95 | 是 | PII脱敏 |
| skill_review.py | 424 | 是 | 技能复习 |
| worker_persist_test.py | 127 | 是 | 持久化测试 |
| patch_echarts.py | 63 | 否 | ECharts补丁 |
| patch_stats.py | 120 | 否 | 统计补丁 |
| start_webui.py | 24 | 否 | WebUI启动 |
| stats_collector.py | 24 | 否 | 统计收集 |
| test_5agents.py | 89 | 否 | 5Agent测试 |
| test_regression.py | 110 | 否 | 回归测试 |

---
