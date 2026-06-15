# 真实邮箱验证码发送计划

> 生成: 2026-05-28 | 执行: 次日
> 目标: 将 send_verify_code 从模拟模式切换为真实 SMTP 发信，用真实邮箱接收验证码

---

## 背景

当前 `send_verify_code()` 只打印日志不真发邮件。

```
line 202: # 模拟发送（生产环境接入 SMTP）
line 203: print(f"[SIMULATED EMAIL] To: {email}  Code: {code}  Token: {token[:16]}...")
```

已有的工作已验证（开发模式）:
- `POST /api/verify/send` — 200 OK，透传 debug_code/debug_token
- `POST /api/verify/check` — 200 OK，验证通过
- 验证码 10 分钟有效

---

## 执行步骤

### Step 1: 选择 SMTP 服务商

考察 126 邮箱的 SMTP 配置（benemorphy@126.com）:

| 选项 | 说明 |
|------|------|
| 126 免费邮箱 SMTP | smtp.126.com:465(SSL) / :25 — 需开启 POP3/SMTP 并获取授权码 |
| 第三方邮件服务 | SendGrid / Mailgun / SMTP2GO — 更稳定但需额外注册 |

**推荐**: 先试 126 免费 SMTP（已知邮箱+密码/授权码即可）

### Step 2: 添加 SMTP 配置到 config.py

```python
# SMTP
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.126.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "benemorphy@126.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # 授权码
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "true").lower() == "true"
```

### Step 3: 安装/确认依赖

```bash
# smtplib 是标准库，无需额外安装
```

### Step 4: 修改 send_verify_code() 函数

在 auth.py 中:
1. 导入 smtplib, email.mime
2. 编写 `send_email_smtp(to, code)` 函数
3. 替换 `send_verify_code` 中的 `print(...)` 为真实 SMTP 调用
4. 保留 debug 返回字段用于紧急排查

参考代码:

```python
import smtplib
from email.mime.text import MIMEText
from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_SSL

def send_email_smtp(to: str, code: str) -> bool:
    """通过 SMTP 发送验证码邮件"""
    msg = MIMEText(f"您的验证码是: {code}\n有效期 10 分钟", "plain", "utf-8")
    msg["Subject"] = f"BBS 验证码: {code}"
    msg["From"] = SMTP_USER
    msg["To"] = to
    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception as e:
        print(f"[SMTP ERROR] {e}")
        return False
```

### Step 5: 测试验证

```powershell
curl -X POST http://localhost:8001/api/verify/send -d "email=benemorphy@126.com"
# -> 200, 检查 126 邮箱收件箱

curl -X POST http://localhost:8001/api/verify/check ^
  -d "email=benemorphy@126.com&code=收到的验证码&token=debug_token"
# -> 200, {"message": "验证通过"}
```

### Step 6: 生产化收尾

- [x] 将 SMTP_PASSWORD 改为仅从环境变量读取（去掉 config.py 的默认值）—— 默认值已有 `""`
- [x] 添加频率限制（60 秒内不能重复发送）—— `_last_send_time` 字典 + 429 响应
- [x] 添加重试逻辑 —— `send_email_smtp()` 自动重试 1 次（间隔 1s）

---

## 前置检查清单（开始前）

- [ ] Mosquitto 已重启（管理员权限 `net stop mosquitto && net start mosquitto`）
- [ ] Gateway 8001 正常运行（.venv uvicorn）
- [ ] benemorphy@126.com 已在 users 表中有记录
- [ ] 准备好 126 邮箱的 SMTP 授权码（需登录网页版 126 邮箱开启 POP3/SMTP）
- [ ] 测试 `/api/verify/send` 和 `/api/verify/check` 在模拟模式已正常工作

---

## 回滚方案

如果 SMTP 发送失败:
1. 将 auth.py 中 `send_email_smtp(...)` 改回 `print(...)` 模式
2. 或添加 ENV 开关: `SMTP_ENABLED=false` 时走模拟
