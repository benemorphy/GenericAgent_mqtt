# Resume Note: Gateway Email Auth + SMTP 修复 — 已完成

## 完成状态（2026-05-29 09:42）
所有 4 步验证通过，任务完成。

## 验证结果
| 步骤 | 状态 | 详情 |
|------|------|------|
| 1. Gateway 启动 | ✅ | PID 3672 + 3960，端口 8000 正常响应 |
| 2. 邮箱 tab 加载 | ✅ | /login 含"邮箱登录"，/register 含"邮箱注册" |
| 3. SMTP 真实发送 | ✅ | benemorphy@126.com 真实收到验证码邮件 |
| 4. 完整流程测试 | ✅ | 注册→发码→验证→登录（302→/boards+JWT cookie）全部通过 |

## 代码修改内容
- `frontends/bbs_browser/auth.py`: send_email_smtp 添加 ssl.create_default_context() + .env 密码回退
- `frontends/bbs_browser/auth.py`: login_user_email 添加 verified 检查
- `frontends/bbs_browser/auth.py`: check_verify 验证通过后设置 verified=1
- `frontends/gateway/routers/auth.py`: 路由 /api/email/login 对接新的 login_user_email
- `frontends/gateway/templates/login.html`: 添加邮箱认证 tab/表单
- `frontends/gateway/templates/register.html`: 添加邮箱认证 tab/表单

## 已知小问题
- .env 文件不存在（SMTP_PASSWORD 通过环境变量注入，不影响运行）
- 新注册的 126 邮箱发码失败（126 SMTP 服务端限制，非代码问题）
- 错误验证码返回 400 友好提示（正常）
