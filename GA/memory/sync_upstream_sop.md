# 同步上游更新 SOP — Sync with Upstream

> 适用于保持 fork 与上游项目一致 (`D:\00synchronize\GenericAgent`)

## 完整流程

```bash
cd D:\00synchronize\GenericAgent

# 1. 获取上游最新
git fetch upstream

# 2. 合并上游到本地 main
git checkout main
git merge upstream/main

# 3. 解决冲突（如有）
#   - 手动编辑冲突文件
#   - git add <冲突文件>
#   - git commit

# 4. 推送到 fork
git push origin main
```

## 首次重置（丢弃所有本地修改）

```bash
git fetch upstream
git reset --hard upstream/main
git push origin main --force
```

---

**注意**: 本地特化功能在 `D:\open_claw_agent\Beneh\GA`，`GenericAgent` 保持纯上游。
