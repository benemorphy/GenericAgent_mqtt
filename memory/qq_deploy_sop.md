# GenericAgent + QQ 机器人部署 SOP (NapCat + onebot_qq)

## 概述
本SOP指导你从零开始部署 GenericAgent 的 QQ 机器人网关。通过 NapCat 作为 QQ 协议端，onebot_qq 项目作为中间网关，将 QQ 消息转发给 GenericAgent 处理。

**支持系统：Windows / Linux 双平台**

## 前置条件
1. 已安装 GenericAgent（目录结构完整）
2. Python 3.8+
3. 支持系统：Windows / Linux
4. 已安装 QQ NT 版本（推荐 9.9.26+，最低版本 40768）
5. 一个用于机器人的 QQ 账号

---

## 第一部分：NapCat 安装

### 1.1 下载 NapCat

**方法一：GitHub Release（推荐）**

1. 访问 https://github.com/NapNeko/NapCatQQ/releases/tag/v4.18.1
2. 下载对应系统的包：
   - Windows: **NapCat.Shell.Windows.OneKey.zip**
   - Linux: **NapCat.Shell.Linux.x86_64.zip**
3. 解压到任意目录（建议路径不含中文和空格）

**方法二：备用下载**

- 官方文档：https://napneko.github.io/
- 备用文档：https://napcat.top/

### 1.2 安装 NapCat

1. 确保已安装 QQ NT 版本（9.9.26+）并登录过一次
2. 解压 NapCat 到目标目录
   - Windows: `D:\NapCat`
   - Linux: `~/NapCat`
3. 运行：
   - Windows: 运行一键包中的 `napcat.bat` 或 `login.bat`
   - Linux: `./napcat.sh` 或 `bash login.sh`
4. 首次运行会要求登录 QQ（扫码或输入账号密码）
5. 登录成功后，控制台会显示 WebUI 地址（通常是 `http://127.0.0.1:6099`）
6. **注意**：WebUI 的登录密码在控制台输出中查看（默认是随机密码）

### 1.3 NapCat WebUI 配置

1. 浏览器打开 WebUI 地址（如 `http://127.0.0.1:6099`）
2. 输入控制台显示的密码登录
3. 进入 **网络配置** 或 **适配器配置**
4. 找到 **OneBot v11** 适配器
5. 启用 **WebSocket 服务端（正向WS）**
6. 配置参数：
   - Host: `127.0.0.1`
   - Port: `8080`
   - Path: `/onebot/v11/ws`
   - Access Token: 留空（或自定义，需与 onebot_qq 的 .env 一致）
   - 消息格式: `array`（推荐）
7. 保存配置
8. 确认 OneBot 服务状态为 **已启用/运行中**

---

## 第二部分：onebot_qq 项目部署

### 2.1 克隆项目

```bash
# Windows
cd D:\GenericAgent\temp
git clone https://github.com/jlu005807/GA_onebot_qq.git onebot_qq

# Linux
cd ~/GenericAgent/temp
git clone https://github.com/jlu005807/GA_onebot_qq.git onebot_qq
```

> 注意：必须克隆到 GenericAgent 的 temp 目录下，项目依赖 GA 的路径注入。

### 2.2 安装依赖

```bash
# Windows
cd D:\GenericAgent\temp\onebot_qq
pip install -r requirements.txt

# Linux
cd ~/GenericAgent/temp/onebot_qq
pip3 install -r requirements.txt
```

> 如果 onebot_qq 和 GenericAgent 使用同一个虚拟环境，可以跳过此步。

### 2.3 配置 .env

1. 复制配置模板：
```bash
# Windows
copy .env.example .env

# Linux
cp .env.example .env
```

> 如需英文注释模板，可使用 `.env.example-en`

2. 编辑 `.env` 文件，修改以下必填项：

```ini
# NapCat 的 WebSocket 地址（必填，与 NapCat WebUI 配置一致）
ONEBOT_WS_URL=ws://127.0.0.1:8080/onebot/v11/ws

# 你的管理员 QQ 号（必填，用于权限控制）
ONEBOT_ADMIN_QQ=你的QQ号

# 访问令牌（如果 NapCat 设置了 token 则填，否则留空）
ONEBOT_ACCESS_TOKEN=
```

3. 其他可选配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ONEBOT_ALLOWED_USERS` | `*` | 允许使用的用户列表，`*`表示全部 |
| `ONEBOT_ALLOW_GROUP` | `1` | 是否启用群聊（1=启用） |
| `ONEBOT_ALLOWED_GROUPS` | `*` | 允许的群号，`*`表示全部 |
| `ONEBOT_GROUP_REQUIRE_AT` | 空 | 群聊触发模式：`1/true`=需@机器人；`0/false/空`=任意消息可触发 |
| `ONEBOT_GROUP_TRIGGER_WORDS` | 空 | 群聊触发词，逗号分隔，命中任一即可触发 |
| `ONEBOT_CONTEXT_MESSAGES` | `0` | 传递触发前历史消息条数，`0`关闭，最大`20` |
| `ONEBOT_MAX_MSG_LENGTH` | `500` | 单条消息最大长度 |
| `ONEBOT_MAX_QUEUE_SIZE` | `5` | 每用户待处理队列上限 |
| `ONEBOT_PLAIN_TEXT_HINT` | 内置 | 附加给Agent的文本提示，`0/false/off`可关闭 |
| `ONEBOT_DATA_DIR` | `data` | 附件保存目录，相对路径基于运行目录 |
| `ONEBOT_MAX_FILE_BYTES` | `10485760` | 单附件最大字节数（默认10MB） |

### 2.3.1 常用配置组合

1. **仅@机器人回复**（群内更克制）
   ```
   ONEBOT_GROUP_REQUIRE_AT=1
   ONEBOT_GROUP_TRIGGER_WORDS=
   ONEBOT_CONTEXT_MESSAGES=0
   ```

2. **任意群消息触发**（测试联调常用）
   ```
   ONEBOT_GROUP_REQUIRE_AT=
   ONEBOT_GROUP_TRIGGER_WORDS=
   ONEBOT_CONTEXT_MESSAGES=0
   ```

3. **@或触发词+上下文**（推荐）
   ```
   ONEBOT_GROUP_REQUIRE_AT=1
   ONEBOT_GROUP_TRIGGER_WORDS=小宇,助手,bot
   ONEBOT_CONTEXT_MESSAGES=3
   ```

### 2.4 启动 onebot_qq

```bash
# Windows
cd D:\GenericAgent\temp\onebot_qq
python src/main.py

# Linux
cd ~/GenericAgent/temp/onebot_qq
python3 src/main.py
```

启动成功后，控制台应显示：
- WebSocket 连接成功
- GenericAgent 后台线程启动
- OneBot 服务就绪

---

## 第三部分：验证与测试

### 3.1 基础功能测试

1. **私聊测试**：用其他 QQ 给机器人发送一条消息，确认有回复
2. **群聊测试**：在群里 @机器人 发送消息，确认有回复
3. **附件测试**：发送图片/文件，检查 `data/image` 和 `data/file` 目录是否有落盘文件

### 3.2 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 (connection refused) | 检查 NapCat 是否启动、OneBot WS 是否启用、端口是否正确 |
| Token 验证失败 (retcode=1403) | 检查 NapCat token 与 .env 的 `ONEBOT_ACCESS_TOKEN` 是否一致 |
| 群聊不回复 | 确认消息有 @机器人、`ONEBOT_ALLOW_GROUP=1`、群号在白名单中 |
| 附件未保存 | 检查 NapCat 上报的附件 URL/path 是否有效，确认 `ONEBOT_MAX_FILE_BYTES` 不过小 |
| 启动报 websockets 参数错误 | 升级 websockets：`pip install --upgrade websockets` |
| 群聊只想要@触发 | 设置 `ONEBOT_GROUP_REQUIRE_AT=1`，清空 `ONEBOT_GROUP_TRIGGER_WORDS` |
| 想要触发词触发 | 设置 `ONEBOT_GROUP_TRIGGER_WORDS=词1,词2`，逗号分隔 |
| Agent 没有上下文 | 设置 `ONEBOT_CONTEXT_MESSAGES=3`（或其他数值） |
| 消息被截断 | 调大 `ONEBOT_MAX_MSG_LENGTH` |
| 用户消息丢失 | 调大 `ONEBOT_MAX_QUEUE_SIZE`，或让 Agent 快速处理 |
| 附件保存失败 | 检查 `ONEBOT_DATA_DIR` 路径权限，确认 `ONEBOT_MAX_FILE_BYTES` 足够 |
| Linux python命令不存在 | 使用 `python3` 替代 `python` |

### 3.3 日志查看

- onebot_qq 日志：`temp/onebot_YYYYMMDD_HHMMSS.log`（每次启动生成新文件）
- NapCat 日志：NapCat 控制台输出

---

## 第四部分：高级配置（可选）

### 4.1 开机自启动

**Windows：**
将启动命令写入批处理文件，放入 Windows 启动目录：

```bat
@echo off
cd /d D:\GenericAgent\temp\onebot_qq
python src/main.py
```

**Linux：**
使用 systemd 或 crontab：

```bash
# crontab 示例
@reboot cd ~/GenericAgent/temp/onebot_qq && python3 src/main.py &
```

### 4.2 多机器人实例

如需运行多个机器人账号，每个实例需要：
- 独立的 NapCat 实例（不同端口）
- 独立的 onebot_qq 目录（复制一份，修改 .env 端口）
- 修改 `lock_port` 避免冲突

---

## 文件结构参考

```
GenericAgent/
├── temp/
│   └── onebot_qq/          # 本项目
│       ├── src/             # 源代码
│       ├── data/            # 附件存储
│       │   ├── image/
│       │   ├── record/
│       │   └── file/
│       ├── .env             # 配置文件
│       ├── .env.example     # 配置模板（中文注释）
│       ├── .env.example-en  # 配置模板（英文注释）
│       ├── requirements.txt # Python 依赖
│       └── README.md
```

## 相关链接

- 项目仓库：https://github.com/jlu005807/GA_onebot_qq
- NapCat GitHub：https://github.com/NapNeko/NapCatQQ
- NapCat 文档：https://napneko.github.io/

## 更新日志

- 2026-05-05：初始版本，包含 NapCat 安装、onebot_qq 配置、验证测试完整流程
- 2026-05-05：新增配置表、常用配置组合、FAQ
- 2026-05-05：新增 Linux 双平台支持、`python3` 命令、`.env.example-en` 英文模板、日志文件名格式说明
- 2026-05-09：新增消息过滤说明，防止工具调用信息泄漏到QQ聊天

---

## 附录：消息过滤机制

### 问题描述
Agent 回复中可能包含工具调用信息（如 `🛠️ file_read(...)`），这些信息不应发送给用户。

### 过滤实现
`onebot_message.py` 中的 `normalize_outgoing_content()` 函数负责过滤：

```python
def normalize_outgoing_content(content: str) -> str:
```

当前过滤规则：
1. 丢弃 `LLM Running (Turn N) ...` 状态行
2. 丢弃 `code_run({...})` 格式的工具调用行
3. 丢弃 markdown 代码围栏标记
4. 折叠多余空行

### 常见泄漏原因
- 工具调用格式为 `🛠️ tool_name({...})` 时，`code_run(` 匹配不到，会漏过
- 多行工具调用块未闭合时，后续内容可能被误吞

### 修复建议
在 `normalize_outgoing_content` 的正则匹配中增加对 `🛠️` 前缀的过滤：
```python
# 在现有 code_run 过滤前增加
if re.match(r"^[🛠️]\s*\w+\(", stripped):
    continue
```