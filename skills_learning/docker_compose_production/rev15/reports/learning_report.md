# 技能学习报告: docker_compose_production

| 属性 | 值 |
|------|-----|
| 版本 | rev15 |
| 评分 | 65/100 PASS |
| 案例数 | 6 条 |
| 模式总数 | 18 个 |
| 继承自 rev14 | 16 个 |
| 新增 | 2 个 |

## 知识模式

### 领域专有 (13个)
- [92%] 生产级Docker Compose配置优化：环境变量、资源限制与健康检查
- [90%] 在Docker Compose生产部署中，应使用明确的镜像标签（如版本号或Git提交哈希），而非latest标签，以确保部署的可重复性和可追溯性。
- [88%] 多环境管理与部署策略：开发、测试、生产环境的Compose文件分离与覆盖
- [88%] 使用Docker Compose时，应将敏感信息（如密码、API密钥）通过环境变量或Docker Secrets管理，避免硬编码在配置文件中。
- [85%] Docker Compose与CI/CD集成：自动化构建、测试与部署流水线
- [85%] 生产环境下的Docker Compose文件应配置资源限制（如CPU和内存），防止单个容器耗尽主机资源，保障服务稳定性。
- [85%] 在Docker Compose中，应将持久化数据（如数据库文件）挂载到命名卷（named volumes）而非绑定挂载，以简化备份和迁移。
- [82%] 生产部署中应为每个服务配置健康检查（healthcheck），以便Docker Compose自动检测服务状态并重启异常容器。
- [80%] 生产环境中的网络与安全配置：网络隔离、TLS加密与密钥管理
- [80%] 生产环境中应启用日志驱动（如json-file或syslog），并配置日志轮转策略，避免日志文件无限增长导致磁盘空间耗尽。
- [80%] Docker Compose生产配置中应显式设置网络模式（如自定义bridge网络），避免使用默认网络，以增强服务隔离和安全性。
- [78%] 日志收集、监控与故障恢复：使用Docker Compose集成日志驱动、Prometheus和自动重启策略
- [75%] Docker Compose文件应使用版本3或更高版本，以支持swarm模式或编排工具（如Kubernetes）的兼容性，便于扩展。

### 高级模式 (2个)
- [78%] 生产部署应使用多阶段构建（multi-stage builds）优化镜像大小，减少攻击面并提升部署速度。
- [72%] 生产环境应使用Docker Compose的depends_on条件（如condition: service_healthy）确保服务启动顺序，避免依赖服务未就绪导致错误。

### 基础模式 (1个)
- [80%] 掌握 Docker Compose Production 核心概念和最佳实践

## 参考案例 (6条)

- josiahsiegel/claude-plugin-marketplace/docker-best-practices
- [Docker (software)](https://en.wikipedia.org/wiki/Docker_%28software%29)
- [Mirantis](https://en.wikipedia.org/wiki/Mirantis)
- [The Other Woman (2014 film)](https://en.wikipedia.org/wiki/The_Other_Woman_%282014_film%29)
- [Kubeflow](https://en.wikipedia.org/wiki/Kubeflow)
- [Amanda Somerville](https://en.wikipedia.org/wiki/Amanda_Somerville)