# 下班模式 — Shutdown SOP

> 当用户说"下班了"或类似表达时执行此流程。

## 执行步骤

用户说"下班了" → 我依次执行：

### Step 1: 记忆保存
```python
# 如果有未保存的关键信息，写入 long-term memory
# 通过 start_long_term_update() 触发
```

### Step 2: 关闭 TMWebDriver 后台
```powershell
# 杀掉 TMWebDriver 进程
Get-CimInstance Win32_Process -Filter "name='python.exe'" |
  Where-Object { $_.CommandLine -like "*TMWebDriver*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Step 3: 关闭 Chrome 浏览器
```powershell
# 关闭 Chrome
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Step 4: 告知用户
输出：下班关闭清单已完成。