# VPN 远程新用户登录测试计划

> 生成: 2026-05-29
> 目标: 在远端通过 VPN 访问本机 Gateway，完成新用户邮箱注册、验证码收信、登录的完整流程测试

---

## 环境信息

| 项目 | 值 |
|------|-----|
| 本机 IP | `10.24.242.176`（内网 /24） |
| Gateway 地址 | `http://10.24.242.176:8000` |
| Gateway 绑定 | `0.0.0.0:8000`（重启后 Gateway 自动运行，硬编码端口） |
| MQTT Broker | `127.0.0.1:1883`（Mosquitto，仅本地） |
| MariaDB | `127.0.0.1:3306`（仅本地） |
| SMTP | 126 邮箱，已配置真实发信 |
| 防火墙状态 | 专用配置文件启用，入站默认阻止 |
| VPN 类型 | 待确认（用户VPN连接方式） |

### 已有测试用户

| 邮箱 | 状态 |
|------|------|
| benemorphy@126.com | 已注册，已验证 |

---

## 预检清单

### 本机准备
- [ ] Gateway 8000 已运行（当前: 运行中 PID 4804）
- [ ] MariaDB 3306 已运行（当前: 运行中）
- [ ] Mosquitto 1883 已运行（当前: 运行中）
- [ ] 防火墙开放入站 8000 端口
- [ ] VPN 客户端配置完成，获取远端分配的虚拟 IP

### 远端准备
- [ ] 浏览器可访问 `http://10.24.242.176:8000/`
- [ ] 可接收 126 邮箱验证码（远端需能打开 126 邮箱）

---

## 测试步骤

### Step 1: 开放防火墙入站端口（已完成）

```powershell
# 以管理员身份运行（已执行）
netsh advfirewall firewall add rule name="Gateway 8000" dir=in action=allow protocol=TCP localport=8000
```

### Step 2: 确认 VPN 连通性

1. 远端 Ping 本机 VPN IP 或内网 IP
2. 远端浏览器访问 `http://10.24.242.176:8000/`
3. 确认页面加载正常（应跳转到 /login）

### Step 3: 远端新用户邮箱注册

**注册页面**: `http://10.24.242.176:8000/register`

**API**: `POST http://10.24.242.176:8000/api/email/register`
- `email`: 远端可收信的真实邮箱（建议使用非 126 的邮箱，避免与本机测试账号冲突）
- `password`: 测试密码
- `nickname`: (可选)

预期结果: 注册成功，跳转到 `/login?registered=1`

### Step 4: 请求验证码

**API**: `POST http://10.24.242.176:8000/api/email/send_code`
- `email`: 刚注册的邮箱

预期结果: `{"ok": true, "msg": "验证码已发送"}`

注意事项:
- 60 秒内不能重复发送（频率限制）
- 远端需实际到邮箱收信

### Step 5: 输入验证码完成验证

**API**: `POST http://10.24.242.176:8000/api/email/verify`
- `email`: 注册邮箱
- `code`: 收到的 6 位验证码
- `token`: 从 send_code 响应中获取的 debug_token

预期结果: `{"ok": true, "msg": "验证通过"}`

### Step 6: 邮箱登录

**登录页面**: `http://10.24.242.176:8000/login`（输入邮箱和密码）

**API**: `POST http://10.24.242.176:8000/api/email/login`
- `email`: 注册邮箱
- `password`: 注册密码

预期结果: 登录成功，设置 JWT Cookie，跳转到 `/boards`

### Step 7: 访问 Boards 面板

**URL**: `http://10.24.242.176:8000/boards`

预期结果: 显示 Boards 列表页面（新用户可能为空列表但不报错）

---

## 可能遇到的问题

| 问题 | 解决方案 |
|------|---------|
| 远端无法连接 8000 | 检查防火墙规则 `netsh advfirewall firewall show rule name="Gateway 8000"` |
| 验证码邮件收不到 | 检查 SMTP 环境变量 `SMTP_PASSWORD`，或查看本机 Gateway 日志 |
| 60s 频率限制 | 等待冷却后再试 |
| VPN 路由不通 | 确认 VPN 分配的子网与本机内网是否互通 |
| JWT Cookie 跨域 | 直接浏览器访问，不走反向代理，无需 CORS 配置 |

---

## 回滚方案

- 若防火墙规则导致问题: `netsh advfirewall firewall delete rule name="Gateway 8000"`
- 若需调试模式: 启用验证码 debug 信息（API 已返回 `debug_code` 和 `debug_token`）
- 若 SMTP 降级: 设置 `SMTP_PASSWORD` 为空回到模拟打印模式

---

## 测试结果记录

| 测试项 | 结果 | 备注 |
|--------|------|------|
| Step 1 防火墙配置 | | |
| Step 2 VPN 连通性 | | |
| Step 3 邮箱注册 | | |
| Step 4 请求验证码 | | |
| Step 5 验证码校验 | | |
| Step 6 邮箱登录 | | |
| Step 7 Boards 面板 | | |
