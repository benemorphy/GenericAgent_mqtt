# 技能学习报告: docker_compose_production

| 属性 | 值 |
|------|-----|
| 版本 | rev16 |
| 评分 | 92/100 PASS |
| 案例数 | 6 条 |
| 模式总数 | 18 个 |
| 继承自 rev15 | 18 个 |
| 新增 | 0 个 |

## 知识模式

### 领域专有 (11个)
- [92%] 生产级Docker Compose配置优化：环境变量、资源限制与健康检查
- [90%] 使用Docker Compose时，应将敏感信息（如密码、API密钥）通过环境变量或Docker Secrets管理，避免硬编码在docker-compose.yml文件中。
- [90%] 在Docker Compose文件中使用命名卷（named volumes）或绑定挂载（bind mounts）持久化数据，并定期备份卷数据，确保数据不因容器重启而丢失。
- [90%] 在Docker Compose中为生产环境指定镜像标签为具体版本（如v1.2.3），避免使用latest标签，确保部署的可重复性和可追溯性。
- [88%] 多环境管理与部署策略：开发、测试、生产环境的Compose文件分离与覆盖
- [85%] Docker Compose与CI/CD集成：自动化构建、测试与部署流水线
- [85%] 使用Docker Compose定义多容器应用时，应明确指定服务依赖关系（depends_on），确保容器按正确顺序启动，并考虑健康检查（healthcheck）以增强生产环境的可靠性。
- [85%] 为生产环境配置日志驱动和日志轮转（如使用json-file驱动并设置max-size和max-file），避免容器日志无限增长导致磁盘空间耗尽。
- [85%] 生产环境中应使用Docker Compose的restart策略（如always或unless-stopped）确保容器在崩溃后自动重启，提高服务可用性。
- [80%] 生产环境中的网络与安全配置：网络隔离、TLS加密与密钥管理
- [78%] 日志收集、监控与故障恢复：使用Docker Compose集成日志驱动、Prometheus和自动重启策略

### 高级模式 (4个)
- [80%] 在生产部署中，应为每个服务配置资源限制（如CPU、内存），通过Docker Compose的deploy.resources设置，防止单个服务耗尽主机资源。
- [80%] 为每个服务定义网络（networks），将前端、后端和数据库隔离到不同网络，减少攻击面并控制服务间通信。
- [75%] 使用Docker Compose的healthcheck指令为关键服务定义健康检查，结合depends_on的condition: service_healthy，确保依赖服务就绪后再启动下游服务。
- [70%] 使用Docker Compose的profiles功能区分开发、测试和生产环境配置，避免维护多个docker-compose文件，同时保持配置一致性。

### 基础模式 (1个)
- [80%] 掌握 Docker Compose Production 核心概念和最佳实践

## 参考案例 (6条)

- josiahsiegel/claude-plugin-marketplace/docker-best-practices
- [Docker (software)](https://en.wikipedia.org/wiki/Docker_%28software%29)
- [Mirantis](https://en.wikipedia.org/wiki/Mirantis)
- [The Other Woman (2014 film)](https://en.wikipedia.org/wiki/The_Other_Woman_%282014_film%29)
- [Amanda Somerville](https://en.wikipedia.org/wiki/Amanda_Somerville)
- [Kubeflow](https://en.wikipedia.org/wiki/Kubeflow)