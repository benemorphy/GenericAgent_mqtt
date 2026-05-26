"""GenericAgent 配置 Profiles

每个 profile 是一个 .py 文件，定义与 mykey.py 相同的变量。
ConfigService 根据 profile 名称加载对应文件。

可用 profiles:
  internet   — 外网 API 配置（DeepSeek / OpenAI / Claude）
  inner      — 内网本地模型配置（llama-server）
  inner_vlm  — 内网 VLM 多模态模型配置

快速开始:
  cp config\mykey_internet.py profiles/internet.py   # 从现有配置创建
  cp config\mykey_inner.py profiles/inner.py
  cp config\mykey_inner_vlm.py profiles/inner_vlm.py

切换 profile:
  python -c "from tools.config_service import ConfigService; ConfigService.init('internet')"
  或运行: switch_profile.bat internet
"""
