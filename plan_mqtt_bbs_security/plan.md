<!-- EXECUTION PROTOCOL (每轮必读)
1. file_read(plan.md)，找到第一个 [ ] 项
2. 该步标注了SOP → file_read 该SOP的速查段
3. 执行该步骤 + Mini验证产出
4. file_patch 标记 [ ] → [✓]+简要结果，然后回到步骤1继续下一个[ ]
5. 所有步骤标记完成后 → 终止检查：file_read(plan.md)确认0个[ ]残留
6. 完成所有步骤后回复 __GOAL_COMPLETE__ 触发自动终止
-->

# MQTT BBS 安全优化实施计划 (Phase 2)

**需求**: 用户已同意手动决策项，实施剩余10项安全/架构优化
**约束**: 
- 不可修改已完成的9项补丁
- TLS配置需要用户确认证书路径
- agent.env操作用户确认后执行
- 所有改动用git追踪

## 探索发现（已完成于审计阶段）
- C1: Mosquitto监听1883明文, 无TLS, 密码文件mosquitto_passwd
- H1: agent.env含明文密码, 未在.gitignore中
- H4: plugin_manager.py自动加载所有.py文件, 无签名校验
- L1: Python BoardService无健康检查端点, 仅Rust版有
- M1: 所有handler无速率限制 (register/post/query/file)
- M5: 测试文件存在但覆盖率低 (test_board_service.py等)
- M8: 无结构化审计日志, 仅log.info/warning
- M2: agent/status retain消息暴露在线状态
- L2: 无覆盖率报告工具链
- C1v2: BoardClient无SSL连接参数

## 执行计划

### Phase 2A: TLS加密 (C1) — 用户环境操作
1. [✓] Mosquitto TLS配置: 修改mosquitto.conf加8883端口+证书路径
   SOP: mqtt_service_config.md
   文件: docker/mosquitto.conf, docker/mosquitto_retain.conf
   操作: 追加listener 8883, certfile, keyfile, cafile; require_certificate false
   结果: native D:\tools\mosquitto\mosquitto.conf已更新; docker/下创建对应配置

2. [✓] 生成自签证书脚本: 写create_certs.ps1
   操作: 用Python cryptography生成CA+服务端证书, 输出至docker/certs/和D:\tools\mosquitto\certs/
   验证: 证书文件存在 (ca.crt, ca.key, server.crt, server.key)
   注意: OpenSSL未安装, 使用Python cryptography替代

3. [✓] BoardClient SSL连接支持: 修改config.py/client.py加ssl参数
   SOP: emqtt_design_principles.md
   文件: GA/Mqtt_bbs_client/config.py, client.py
   操作: 加MQTT_TLS/SSL_CERT环境变量, connect()接受ssl_context参数
   结果: 已预先实现 — config.py有完整TLS环境变量; client.BBSClient有tls_*参数+connect()中tls_set()调用

4. [ ] 更新docker-compose.yml: 暴露8883端口, 挂载certs目录

### Phase 2B: 凭据管理 (H1)
5. [ ] agent.env清洗: 添加.gitignore, 创建agent.env.template模板
   操作: 
   - .gitignore添加agent.env
   - 创建agent.env.template (所有密码字段填<PLEASE_SET>)
   - 当前agent.env值记录到keychain (引用keychain SOP)
   验证: git check-ignore agent.env返回真

### Phase 2C: 插件安全 (H4)
6. [ ] 插件签名校验框架: 修改plugin_manager.py
   文件: Mqtt_bbs_server/plugin_manager.py
   操作: 
   - _load_module()中校验.py文件头签名注释 (# SIG: <sha256>)
   - 签名不匹配/无签名拒绝加载
   - 提供sign_plugin.py工具生成签名
   - 测试: 签名正常加载, 篡改后拒绝

### Phase 2D: 速率限制 (M1)
7. [ ] 全局速率限制: 添加RateLimiter类
   文件: Mqtt_bbs_server/board_config.py 或新建 rate_limiter.py
   操作:
   - 基于滑动窗口(token bucket)的速率限制
   - 按board+action+agent_id限速
   - 配置: 注册5次/min, 发帖30次/min, 查询20次/min
   - 集成到board_handlers.py的每个on_*方法入口

### Phase 2E: 健康检查与审计 (L1 + M8)
8. [ ] Python BoardService添加/healthz /readyz端点
   文件: Mqtt_bbs_server/board_core.py
   操作: 在init/start阶段启动线程HTTP服务器, 响应200
   验证: curl http://localhost:PORT/healthz -> 200

9. [ ] 结构化审计日志系统
   文件: Mqtt_bbs_server/board_config.py (审计日志模块)
   操作:
   - 创建AuditLogger类, 按结构化JSON格式写log
   - 在on_register/on_post/on_query/on_file_*中调用
   - 审计字段: timestamp, board, action, agent_id, token_hash, success, detail, ip

### Phase 2F: 测试与覆盖 (M5 + L2)
10. [ ] 核心handler单元测试
    文件: GA/tests/test_board_handlers.py 或新建
    操作:
    - on_register: 正常注册, 无效agent_id拒绝, 重复注册
    - on_post: 有效token, 无效token, 空content
    - on_query: users返回含token_hash不包含完整token
    - on_file_download: 正常, 超限拒绝
    - post_fast: 有效JWT, 无效JWT拒绝

11. [ ] 测试覆盖率报告配置
    操作:
    - pyproject.toml添加pytest-cov配置
    - 运行: pytest --cov=Mqtt_bbs_server --cov-report=html
    - 输出: htmlcov/index.html

### Phase 2G: Topic清理 (M2)
12. [ ] 无用retain topic清理
    操作:
    - 列出当前所有retain消息: mosquitto_sub -t "#" --retain-only
    - 识别agent/status、旧版本topic
    - 用空消息覆盖清除: mosquitto_pub -t "agent/status" -n -r

---

## 验证检查点
13. [ ] [VERIFY] 启动独立验证subagent
    操作:
    1. 创建verify_context.json
    2. 启动验证subagent检查所有交付物
    3. 读取VERDICT
