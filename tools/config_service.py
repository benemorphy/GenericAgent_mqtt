"""
ConfigService — 统一配置服务

职责: 替代 mykey.py 的直接模块导入，提供统一的配置读取接口
目标:
  - 单例模式，全局一个实例
  - 支持 profile 切换（inner/internet/inner_vlm）
  - 支持运行时热加载 + 变更检测
  - 支持 fallback 默认值
  - 向后兼容：不破坏现有 import mykey / reload_mykeys() 调用者

设计原则:
  Phase 1: 包装现有的 mykey 加载逻辑（_load_mykeys / reload_mykeys）
  Phase 2: 引入 profile 系统，替换 switch_mykey.ps1
  Phase 3: 引入 schema 校验 + secrets 管理
"""

import os, json, importlib, time

class ConfigService:
    """统一配置服务 — 单例"""

    _instance = None
    _config = {}
    _profile = 'default'
    _path = None          # 当前配置文件的路径
    _mtime = 0            # 上次加载时的 mtime
    _listeners = []       # 配置变更回调

    # ── 单例 ──────────────────────────────────────────────

    @classmethod
    def instance(cls):
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── 公开 API ──────────────────────────────────────────

    def get(self, key, default=None):
        """安全读取配置项，不存在时返回 default"""
        self._ensure_loaded()
        return self._config.get(key, default)

    def get_model_config(self, name):
        """获取 LLM 模型配置（供 ProviderRegistry 使用）

        返回完整的配置 dict，或 None（如果配置不存在）。
        """
        self._ensure_loaded()
        return self._config.get(name)

    def get_all(self):
        """返回完整配置的浅拷贝"""
        self._ensure_loaded()
        return dict(self._config)

    def reload(self, force=False):
        """重新加载配置

        Args:
            force: 强制重新加载（忽略 mtime 检查）

        Returns:
            (config_dict, changed) 元组
        """
        return self._load(force=force)

    def watch(self, callback):
        """注册配置变更回调

        callback(config_dict) 将在配置变更时被调用。
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unwatch(self, callback):
        """移除配置变更回调"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    @property
    def profile(self):
        """当前配置 profile 名称"""
        return self._profile

    # ── 内部实现 ──────────────────────────────────────────

    def _load(self, force=False):
        """实际的配置加载逻辑

        Phase 1: 沿用原有 mykey.py / mykey.json 加载方式
        Phase 2+: 支持 profile 切换（profiles/internet.py 等）
        """
        # 优先尝试 import mykey（Python 模块方式）
        try:
            import mykey
            importlib.reload(mykey)
            self._path = mykey.__file__
            self._config = {k: v for k, v in vars(mykey).items()
                           if not k.startswith('_')}
            self._profile = 'default'
            changed = True
        except ImportError:
            # fallback: mykey.json
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mykey.json')
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f:
                    self._config = json.load(f)
                self._path = p
                self._profile = 'json'
                changed = True
            else:
                # 没有可用配置
                self._config = {}
                self._path = None
                self._profile = 'none'
                changed = force

        self._mtime = time.time_ns()

        # 通知监听器
        if changed:
            for cb in self._listeners:
                try:
                    cb(self._config)
                except Exception as e:
                    print(f"[ConfigService] Listener error: {e}")

        return self._config, changed

    def _ensure_loaded(self):
        """确保配置已加载，同时检测文件变更（热加载）"""
        if not self._config:
            # 首次加载
            self._load(force=True)
            return

        # 热加载检测：检查文件 mtime
        if self._path and os.path.exists(self._path):
            try:
                current_mtime = os.stat(self._path).st_mtime_ns
                if current_mtime != self._mtime:
                    self._load(force=True)
            except OSError:
                pass  # 文件不可读时忽略
        # 如果 _path 是模块路径（import mykey），无法通过 stat 检测
        # 这种情况下靠显式 reload() 调用


# ── 模块级便利函数（兼容 llmcore 的导入方式）──────────────

def get_config(key, default=None):
    """模块级便利函数 — 等同于 ConfigService.instance().get(key, default)"""
    return ConfigService.instance().get(key, default)

def get_model_config(name):
    """模块级便利函数 — 等同于 ConfigService.instance().get_model_config(name)"""
    return ConfigService.instance().get_model_config(name)

def reload_config(force=False):
    """模块级便利函数 — 等同于 ConfigService.instance().reload(force)"""
    return ConfigService.instance().reload(force=force)
