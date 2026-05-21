# GenericAgent 配置 Profiles

## 简介

Profiles 是配置环境模版系统，替代原有的 `switch_mykey.ps1` 文件复制方案。

## 可用 Profiles

| Profile | 说明 | 配置来源 |
|---------|------|---------|
| `internet` | 外网 API 模式 | `profiles/internet.py` |
| `inner` | 内网本地模型 | `profiles/inner.py` |
| `inner_vlm` | 内网 VLM 多模态 | `profiles/inner_vlm.py` |

## 创建 Profile

从已有的 mykey 配置创建：

```bash
# 将现有的配置复制为 profile 文件
cp config\mykey_internet.py   profiles/internet.py
cp config\mykey_inner.py      profiles/inner.py
cp config\mykey_inner_vlm.py  profiles/inner_vlm.py
```

编辑 `profiles/<name>.py` 填入真实的 API key 和端点地址即可。

## 切换 Profile

### 方式一：Python 命令行

```bash
python -c "from tools.config_service import ConfigService; ConfigService.init('internet')"
```

### 方式二：使用脚本

```bash
switch_profile.bat internet
```

### 方式三：在代码中

```python
from tools.config_service import ConfigService
cs = ConfigService.instance()
cs.init('inner')           # 切换到内网配置
cfg = cs.get_all()         # 获取当前配置
current = cs.profile_name  # 当前 profile 名称
```

## 向后兼容

未初始化 profile 时，ConfigService 默认从 `mykey.py` 加载，
与 Phase 1/2 行为完全一致，不影响现有代码。
