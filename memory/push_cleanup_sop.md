# 整理推送 SOP

> 当你对我说"整理推送"时，我按以下流程执行。

## 一句话
```
整理推送 = 清理temp + 检查README（更新新功能）+ git add→commit→push
```

## 详细流程

### Step 1: 清理 temp/
```python
# 删除临时截图、测试图片、编译缓存
删除 temp/*.png, temp/*.jpg, temp/*.pkl, temp/*.pyc
保留: autonomous_reports/, TODO.txt, 启动脚本(.cmd)
```

### Step 2: 检查 README（中英文）
- 对比 `README.md` 和 `README_EN.md` 的工具生态章节
- 检查新增的工具/功能是否已收录：
  - `tools/` 下的新模块
  - `memory/` 下的新 SOP
  - 重要的配置变更（如 broker 地址）
- 如有遗漏，更新后保持中英文对齐

### Step 3: 安全检查
```bash
git diff --cached | grep -iE "(apikey|secret|password|token)\s*="
```
确认无密钥泄露。

### Step 4: git 操作
```bash
git add -A                                    # 暂存所有改动
git commit -m "描述性提交信息"                 # 提交
git push                                      # 推送到 GitHub
```

### Step 5: 最终确认
```bash
git status                                    # 确认干净
```

## 权限边界
- ✅ 允许：删 temp/ 测试文件、改 README、`git add/commit/push`
- ❌ 不碰：`mykey.py`、`.env`、密钥文件
