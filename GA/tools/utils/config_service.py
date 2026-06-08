#!/usr/bin/env python3
"""
ConfigService — 统一配置加载与热重载

从 mykey.py 扫描所有配置变量，支持 profile 切换与运行时热重载。

用法:
  from tools.utils.config_service import ConfigService
  cfg = ConfigService.instance()
  all_configs = cfg.reload()
  llm_config  = cfg.get('native_claude_config0')
  model_cfg   = cfg.get_model_config('cc-relay-1')
"""

import os
import sys
import importlib.util
import threading


class ConfigService:
    """配置服务（单例）"""

    _instance = None
    _lock = threading.Lock()

    # ── 变量名扫描关键字（与 mykey.py 描述一致） ──
    _SESSION_KEYWORDS = ('api', 'config', 'cookie')
    _KNOWN_SESSION_TYPES = {
        'native_claude': 'NativeClaudeSession',
        'native_oai':    'NativeOAISession',
        'claude':        'ClaudeSession',
        'oai':           'LLMSession',
        'mixin':         'MixinSession',
    }

    def __init__(self):
        self._config = {}
        self._mtime = 0
        self._profile = None
        self._mykey_path = None

    # ── 单例 ──

    @classmethod
    def instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def init(cls, profile: str = None):
        """初始化/切换 profile"""
        inst = cls.instance()
        inst._profile = profile
        inst.reload(force=True)
        return inst

    # ── 配置加载 ──

    def reload(self, force: bool = False):
        """重新加载 mykey.py 配置

        Args:
            force: 是否强制重载（忽略 mtime）

        Returns:
            (config_dict, changed) 元组
        """
        mykey_path, mtime = self._resolve_mykey()
        if not force and mykey_path == self._mykey_path and mtime == self._mtime:
            return self._config, False

        # 加载 mykey 模块
        config = self._load_mykey(mykey_path)

        self._config = config
        self._mykey_path = mykey_path
        self._mtime = mtime
        return self._config, True

    def _resolve_mykey(self):
        """确定 mykey.py 路径和修改时间"""
        # 优先 profile
        if self._profile:
            script_dir = os.path.dirname(os.path.abspath(__file__))  # GA/tools/
            ga_dir = os.path.dirname(script_dir)  # GA/
            profile_path = os.path.join(ga_dir, 'profiles', f'{self._profile}.py')
            if os.path.isfile(profile_path):
                return profile_path, os.path.getmtime(profile_path)

        # 默认 mykey.py (在 GA/ 下)
        script_dir = os.path.dirname(os.path.abspath(__file__))  # GA/tools/
        ga_dir = os.path.dirname(script_dir)  # GA/
        default_path = os.path.join(ga_dir, 'mykey.py')
        if os.path.isfile(default_path):
            return default_path, os.path.getmtime(default_path)

        # fallback: 当前目录
        fallback = 'mykey.py'
        if os.path.isfile(fallback):
            return os.path.abspath(fallback), os.path.getmtime(fallback)

        raise FileNotFoundError(
            f"mykey.py not found (profile={self._profile}, "
            f"searched: {default_path})"
        )

    def _load_mykey(self, path: str) -> dict:
        """加载 mykey.py 并提取配置变量"""
        # 用 importlib 加载模块
        spec = importlib.util.spec_from_file_location('_mykey_loader', path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {path}")
        mod = importlib.util.module_from_spec(spec)
        # 保留旧模块引用避免 gc
        sys.modules['_mykey_loader'] = mod
        spec.loader.exec_module(mod)

        config = {}
        for var_name in dir(mod):
            if var_name.startswith('_'):
                continue
            val = getattr(mod, var_name)
            # 扫描 session 配置（dict 类型 + 含关键字）
            if isinstance(val, dict):
                if any(kw in var_name.lower() for kw in self._SESSION_KEYWORDS):
                    # 对含 'name' 的配置建立别名索引
                    if isinstance(val.get('name'), str):
                        config[val['name']] = val
                    config[var_name] = val
            # 直接可用的标量/列表配置
            elif not callable(val) and not isinstance(val, type):
                config[var_name] = val

        return config

    # ── 查询接口 ──

    def get(self, key: str, default=None):
        """获取指定配置项"""
        self.reload(force=False)
        return self._config.get(key, default)

    def get_all(self) -> dict:
        """获取全部配置"""
        self.reload(force=False)
        return dict(self._config)

    def get_model_config(self, cfg_name: str) -> dict:
        """按名称查找模型配置

        先精确匹配 name 字段，再回退到变量名匹配。
        """
        self.reload(force=False)
        # 1. 精确匹配 name 字段
        for key, val in self._config.items():
            if isinstance(val, dict) and val.get('name') == cfg_name:
                return val
        # 2. 变量名匹配
        if cfg_name in self._config:
            val = self._config[cfg_name]
            if isinstance(val, dict):
                return val
        return {}

    # ── 调试 ──

    def __repr__(self):
        return (f"<ConfigService profile={self._profile} "
                f"keys={len(self._config)} mtime={self._mtime:.0f}>")
