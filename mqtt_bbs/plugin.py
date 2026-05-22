"""
mqtt_bbs 插件系统 — Plugin 基类与运行时上下文

用法:
    @plugin_hook
    class MyPlugin(Plugin):
        name = "my_plugin"

        def on_load(self, ctx):
            ctx.subscribe("bbs/+/events/post", self.on_post)

        def on_post(self, topic, payload):
            print(f"新帖: {payload}")
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
import logging as _logging

log = _logging.getLogger("mqtt_bbs.plugin")


# ── 标记装饰器 ──────────────────────────────────

def plugin_hook(cls):
    """类装饰器：标记一个 Plugin 子类为可自动发现"""
    if not (isinstance(cls, type) and issubclass(cls, Plugin)):
        raise TypeError(f"@plugin_hook 只能用于 Plugin 子类, 收到 {cls}")
    cls._plugin_hook = True
    return cls


# ── 插件基类 ────────────────────────────────────

class Plugin(ABC):
    """所有插件的基类。子类必须设置 name。"""

    name: str = ""
    version: str = "0.1"
    description: str = ""
    # 运行时由 PluginManager 注入
    _ctx: Optional["PluginContext"] = None

    @property
    def ctx(self) -> "PluginContext":
        if self._ctx is None:
            raise RuntimeError(f"插件 {self.name} 尚未加载")
        return self._ctx

    def on_load(self, ctx: "PluginContext"):
        """插件加载时调用。在此注册 MQTT 订阅、初始化资源。"""
        pass

    def on_unload(self):
        """插件卸载时调用。清理资源。"""
        pass

    def __repr__(self):
        return f"<Plugin {self.name} v{self.version}>"


# ── 插件运行上下文 ──────────────────────────────

class PluginContext:
    """插件运行时的环境：订阅、发布、配置、日志"""

    def __init__(self, plugin: Plugin, manager: "PluginManager",
                 config: Optional[dict] = None):
        self._plugin = plugin
        self._manager = manager
        self.config = config or {}
        self._subscriptions: list[tuple[str, Callable]] = []

    # ── MQTT 操作 ──

    def subscribe(self, topic: str, callback: Callable):
        """订阅 MQTT 主题。callback(topic, payload) 自动异常隔离。"""
        wrapped = self._wrap(callback)
        self._subscriptions.append((topic, callback))
        self._manager._client.subscribe(topic, wrapped)

    def publish(self, topic: str, payload, **kwargs):
        """发布 MQTT 消息。"""
        self._manager._client.publish(topic, payload, **kwargs)

    # ── 配置 ──

    def get_config(self, key: str, default=None):
        return self.config.get(key, default)

    def set_config(self, key: str, value):
        self.config[key] = value

    # ── 生命周期 ──

    def register_filter(self, name: str, callback: Callable,
                        priority: int = 100):
        """注册过滤器到 BoardService 的 handler 链。
        name 格式: 'pre_post', 'post_post', 'pre_register', 'post_register' 等。
        callback(data) -> data 或 None（阻断）。
        """
        self._manager.register_filter(name, callback, priority, self._plugin.name)

    def unregister_all(self):
        """取消本插件所有订阅（由 PluginManager 调用）。"""
        # 注意：实际 MQTT 取消订阅需要 manager 层面支持
        self._subscriptions.clear()

    def _wrap(self, callback: Callable) -> Callable:
        """异常隔离包装器：单回调异常不扩散"""
        import sys

        def safe_handler(topic, payload):
            try:
                callback(topic, payload)
            except Exception as e:
                import traceback
                print(
                    f"[Plugin ERROR] {self._plugin.name}.{callback.__name__}: {e}",
                    file=sys.stderr,
                )
                traceback.print_exc()

        return safe_handler
