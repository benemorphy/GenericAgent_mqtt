"""
GenericAgent 配置 Profiles

每个 profile 是一个 .py 文件，定义与 mykey.py 相同的变量。
ConfigService 根据 profile 名称加载对应文件。

可用 profiles:
  internet   — 外网 API 配置（DeepSeek / OpenAI / Claude）
  inner      — 内网本地模型配置（llama-server）
  inner_vlm  — 内网 VLM 多模态模型配置

快速开始:
  # 从 mykey.py 创建 profile（替换为实际 profile 名称）
  cp mykey.py profiles/internet.py

切换 profile:
  python -c "from tools.utils.config_service import ConfigService; ConfigService.init('internet')"
"""