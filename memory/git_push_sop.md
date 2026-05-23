# Git 推送 SOP

## 核心原则
**推送前必须进行安全审计**，防止 API Token、密码等敏感信息泄露到远程仓库。

## 推送流程

### 1. 安全审计（前置）
推送前自动检查：
- ✅ 待推送文件列表
- ✅ 扫描文件内容中的敏感模式（`sk-`、`ghp_`、`api_key`、`token`、`password`、`secret`、`-----BEGIN PRIVATE KEY-----` 等）
- ✅ 检查 `.gitignore` 是否覆盖了 mykey、.env 等敏感文件

### 2. 一键推送（自动绕过 PR 保护）
```bash
python scripts/git_push.py "提交信息"
```
自动完成：
1. 创建临时分支 → commit → push
2. 通过 GitHub API 创建 PR
3. squash-merge 到 main
4. 删除临时分支
5. 切回 main 并 pull

### 3. 跳过审计（仅确认安全时）
```bash
python scripts/git_push.py "提交信息" --skip-audit
```

## 配置要求
- `mykey.py` 中配置 `github_token = "github_pat_xxxx"`
  - Token 权限：Contents: write, Pull requests: write
  - 生成地址：https://github.com/settings/tokens

## .gitignore 保护
以下敏感文件已在 `.gitignore` 中：
- `mykey.py` — API 密钥配置
- `.env` — 环境变量
- `auth.json` — 认证文件
- `memory/*` — 本地记忆数据

> ⚠️ 新增敏感文件时记得更新 `.gitignore`
