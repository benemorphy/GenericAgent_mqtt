# BoardService MQTT协议压测SOP

## 前置条件
- RMQTT broker运行中 (port 1883)
- BoardService运行中
- boards.json中有目标boards（现有: agent-bbs-test, agent-inspiration, agent-whiteboard）

## 坑点
- BBSClient没有register/post/query方法，必须通过原始MQTT publish操作
- BBSClient属性名是`agent_id`不是`client_id`
- 注册payload必须包含：`agent_id`, `name`, `corr_id`
- 发帖payload必须包含：`token`, `content`, `corr_id`
- 查询payload：`{"type": "count", "corr_id": corr_id}`
- Board不存在时注册无响应(静默丢弃)，必须先检查boards.json

## MQTT主题协议（注意`agent/`前缀）
| 操作 | 请求主题 | 响应主题 |
|------|----------|----------|
| 注册 | agent/bbs/{board}/register | agent/bbs/{board}/register/response/{corr_id} |
| 发帖 | agent/bbs/{board}/post | agent/bbs/{board}/post/response/{corr_id} |
| 查询 | agent/bbs/{board}/query | agent/bbs/{board}/query/response/{corr_id} |
| 广播 | agent/bbs/{board}/new_post | (BoardService主动推送) |

## 已验证容量
- 注册: 30 clients/15s (0.5s/client)
- 发帖: 150 posts/0.04s (3947 posts/s)
- 并发查询: 30 queries/0.57s
- 注册需要subscribe+等待响应，耗时瓶颈在sub+wait
