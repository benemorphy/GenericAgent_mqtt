"""
PluginManager — 插件发现、加载、卸载、热重载

用法:
    mgr = PluginManager(client, plugin_dir="./plugins")
    mgr.discover_and_load()       # 自动扫描加载
    mgr.load("plugins/my_ext.py") # 手动加载单个
    mgr.unload("my_ext")          # 卸载
    mgr.reload("my_ext")          # 热重载
    print(mgr.list_plugins())     # 列出所有插件
"""

import importlib.util
import inspect
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Optional

from . import config as cfg
from .plugin import Plugin, PluginContext, log


class PluginManager:
    """插件管理器"""

    def __init__(self, client, plugin_dir: str = None, configs: dict = None):
        """
        Args:
            client: BBSClient 实例（用于订阅/发布）
            plugin_dir: 插件目录（默认 ./plugins）
            configs: {plugin_name: {key: val}} 插件配置字典
        """
        self._client = client
        self._plugin_dir = plugin_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins"
        )
        self._configs = configs or {}
        self._plugins: dict[str, Plugin] = {}       # name -> Plugin
        self._modules: dict[str, str] = {}           # name -> source path
        self._lock = threading.Lock()

    # ── 公开 API ──

    def discover_and_load(self):
        """扫描插件目录，自动加载所有 @plugin_hook 标记的插件"""
        plugin_dir = Path(self._plugin_dir)
        if not plugin_dir.is_dir():
            log.warning(f"插件目录不存在: {self._plugin_dir}")
            return []

        loaded = []
        for pyfile in sorted(plugin_dir.glob("*.py")):
            if pyfile.name.startswith("_"):
                continue
            try:
                plugins = self._load_module(str(pyfile))
                loaded.extend(plugins)
            except Exception as e:
                log.error(f"加载插件文件失败 {pyfile.name}: {e}")
                traceback.print_exc()
        return loaded

    def load(self, module_path: str) -> list[str]:
        """从指定路径加载插件文件"""
        return self._load_module(module_path)

    def unload(self, name: str) -> bool:
        """卸载指定插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin is None:
                log.warning(f"插件未加载: {name}")
                return False
            try:
                plugin.on_unload()
            except Exception as e:
                log.error(f"插件 {name} on_unload 失败: {e}")
            # 清理 PluginContext 中的订阅
            if plugin._ctx:
                plugin._ctx.unregister_all()
            del self._plugins[name]
            mod_path = self._modules.pop(name, None)
            # 尝试从 sys.modules 移除
            if mod_path:
                mod_name = self._path_to_modname(mod_path)
                sys.modules.pop(mod_name, None)
            log.info(f"  [Plugin] 已卸载: {name}")
            return True

    def reload(self, name: str) -> bool:
        """热重载指定插件"""
        mod_path = self._modules.get(name)
        if not mod_path:
            log.warning(f"插件 {name} 无源文件路径，无法重载")
            return False
        self.unload(name)
        # 清除缓存
        for key in list(sys.modules.keys()):
            if name in key:
                sys.modules.pop(key, None)
        loaded = self._load_module(mod_path)
        return len(loaded) > 0

    def list_plugins(self) -> list[dict]:
        """列出所有已加载插件"""
        result = []
        with self._lock:
            for name, plugin in self._plugins.items():
                result.append({
                    "name": name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "source": self._modules.get(name, ""),
                })
        return result

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def trigger_event(self, topic: str, data: dict):
        """发布 events 主题事件（供 BoardService 调用）"""
        self._client.publish(topic, data, retain=False, qos=1)

    # ── 内部方法 ──

    def _load_module(self, filepath: str) -> list[str]:
        """加载单个 .py 文件，返回发现的插件名列表"""
        filepath = os.path.abspath(filepath)
        filename = os.path.basename(filepath)
        mod_name = filename.replace(".py", "")

        # 动态导入
        spec = importlib.util.spec_from_file_location(mod_name, filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {filepath}")
        mod = importlib.util.module_from_spec(spec)
        # 注入到 sys.modules 避免重复导入问题
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)

        # 扫描模块中 @plugin_hook 标记的 Plugin 子类
        loaded = []
        for name, obj in inspect.getmembers(mod):
            if (inspect.isclass(obj) and issubclass(obj, Plugin)
                    and obj is not Plugin and getattr(obj, "_plugin_hook", False)):
                plugin = obj()
                plugin._ctx = PluginContext(plugin, self,
                                            self._configs.get(plugin.name, {}))
                with self._lock:
                    self._plugins[plugin.name] = plugin
                    self._modules[plugin.name] = filepath
                try:
                    plugin.on_load(plugin._ctx)
                    log.info(f"  [Plugin] 已加载: {plugin}  ({filepath})")
                    loaded.append(plugin.name)
                except Exception as e:
                    log.error(f"  [Plugin] {plugin.name} on_load 失败: {e}")
                    traceback.print_exc()
                    with self._lock:
                        self._plugins.pop(plugin.name, None)
                        self._modules.pop(plugin.name, None)
        return loaded

    @staticmethod
    def _path_to_modname(path: str) -> str:
        return os.path.splitext(os.path.basename(path))[0]
