# MindFlow 课件管线 SOP

## 首页数据源
- `list_coursewares_page()` 只读 MariaDB `courseware_registry` 表
- DB 不可用时返回空页，绝不回退文件系统

## 生成→上首页完整流程
1. POST /api/v1/courseware/generate → `save_courseware()` → 写入 `coursewares` 表 + 文件系统 cw.json
2. ReviewPublishPhase 质检（当前未接入管线）
3. 通过后调用 `register_courseware(grade, subject, topic, cw_id)` → REPLACE INTO `courseware_registry`
4. 首页自动读取 `courseware_registry` 显示

## 已知断点（2026-06-05）
- `register_courseware()` 在 storage.py:506 存在但从未被调用
- 审核阶段未接入生成管线
- 直接后果：生成课件后首页为空

## 关键提交
- git 07ed541: 建立了 audit/registry/homepage 完整流程

## 注册表约束
- 唯一键 `uk_gst` 保证 (grade, subject, topic) 不重复
- 重复时 REPLACE INTO 自动覆盖为最新
