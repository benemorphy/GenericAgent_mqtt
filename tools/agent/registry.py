#!/usr/bin/env python
"""GA 统一注册中心 (P1: 替代 14+ do_* 手动分发 + 30+ handle_* 硬编码)

用法:
    from tools.agent.registry import TOOL, AGENT, FRONTEND, MEMORY

    @TOOL.register()
    def my_tool(args, response):
        ...

    # 按名称查找
    handler = TOOL.get("my_tool")
"""
import os
import sys
import inspect
import importlib
from typing import Any, Callable, List, Optional


class Registry:
    """轻量注册中心 (mmengine.Registry 兼容接口, 零依赖)"""

    def __init__(self, name: str, locations: List[str] = None):
        self._name = name
        self._modules = {}       # name -> module (已导入)
        self._functions = {}     # name -> function
        self._classes = {}       # name -> class
        self._locations = locations or []

    @property
    def name(self) -> str:
        return self._name

    def register(self, name: str = None, force: bool = False):
        """装饰器: 注册函数/类
        
        @TOOL.register()
        def my_tool(...): ...
        
        @TOOL.register("custom_name")
        class MyClass: ...
        """
        def _wrap(item):
            key = name or item.__name__
            if key in self._functions or key in self._classes:
                if not force:
                    raise KeyError(f"[{self._name}] '{key}' 已注册, 设置 force=True 覆盖")
            if inspect.isfunction(item):
                self._functions[key] = item
            elif inspect.isclass(item):
                self._classes[key] = item
            else:
                self._functions[key] = item
            # P4: 版本化注册快照
            try:
                from tools.utils.resource_version import rvm
                rvm.snapshot("tool", key, {"doc": item.__doc__[:80] if item.__doc__ else "",
                                           "type": "function" if inspect.isfunction(item) else "class"})
            except Exception:
                pass
            return item
        return _wrap

    def register_module(self, module_path: str, name: str = None):
        """按模块路径注册 (如 'tools.codegraph_db')"""
        try:
            mod = importlib.import_module(module_path)
            key = name or module_path.split('.')[-1]
            self._modules[key] = mod
            return mod
        except Exception as e:
            # 静默跳过 (如 agent_runner.py 需要 CLI args)
            return None

    def get(self, name: str) -> Optional[Any]:
        """按名称获取已注册项"""
        if name in self._functions:
            return self._functions[name]
        if name in self._classes:
            return self._classes[name]
        if name in self._modules:
            return self._modules[name]
        return None

    def get_function(self, name: str) -> Optional[Callable]:
        return self._functions.get(name)

    def get_class(self, name: str) -> Optional[type]:
        return self._classes.get(name)

    def list(self) -> List[str]:
        """列出所有注册名"""
        return list(self._functions.keys()) + list(self._classes.keys()) + list(self._modules.keys())

    def list_functions(self) -> List[str]:
        return list(self._functions.keys())

    def list_classes(self) -> List[str]:
        return list(self._classes.keys())

    def discover(self, location: str = None):
        """自动发现: 扫描目录下所有 .py 文件并 import"""
        loc = location or (self._locations[0] if self._locations else None)
        if not loc or not os.path.isdir(loc):
            return []
        discovered = []
        for fname in sorted(os.listdir(loc)):
            if fname.endswith('.py') and not fname.startswith('_'):
                mod_name = fname[:-3]
                mod_path = f"{os.path.basename(loc)}.{mod_name}"
                self.register_module(mod_path, mod_name)
                discovered.append(mod_name)
        return discovered

    def __contains__(self, name: str) -> bool:
        return name in self._functions or name in self._classes or name in self._modules

    def __len__(self) -> int:
        return len(self._functions) + len(self._classes) + len(self._modules)


# ---- 全局注册中心实例 ----
_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOL = Registry("tool", locations=[
    os.path.join(_GA_ROOT, "tools"),
    os.path.join(_GA_ROOT, "memory"),
])
AGENT = Registry("agent", locations=[
    os.path.join(_GA_ROOT, "agents"),
])
FRONTEND = Registry("frontend", locations=[
    os.path.join(_GA_ROOT, "frontends"),
])
MEMORY = Registry("memory", locations=[
    os.path.join(_GA_ROOT, "memory"),
])


# ---- 自动发现已安装工具 ----
def discover_all():
    """扫描并注册所有可发现的工具/前端/记忆模块"""
    results = {
        "tools": TOOL.discover(),
        "frontends": FRONTEND.discover(),
        "memory": MEMORY.discover(),
    }
    return results


if __name__ == "__main__":
    results = discover_all()
    print(f"[Registry] 自动发现结果:")
    for category, items in results.items():
        print(f"  {category}: {len(items)} 项")
        for item in items[:10]:
            print(f"    - {item}")
        if len(items) > 10:
            print(f"    ... 还有 {len(items)-10} 项")
    print(f"\n手动注册工具总数: {len(TOOL)}")
    print(f"已注册: {TOOL.list()[:20]}")
