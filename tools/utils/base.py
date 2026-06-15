"""
工具契约规范 — Phase 1: 标准化接口 + 自动包装

用法:
    from tools.utils.base import BaseTool, ToolResult

    class MyTool(BaseTool):
        name = "my_tool"
        description = "..."
        input_schema = {"type": "object", "properties": {"x": {"type": "string"}}}

        def execute(self, **kwargs) -> ToolResult:
            return ToolResult(ok=True, data=kwargs.get("x"))

旧工具兼容:
    result = tool(**kwargs)  # 自动包装返回值 + 异常捕获
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass
import time


@dataclass
class ToolResult:
    """统一工具返回格式"""
    ok: bool
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0

    def __bool__(self):
        return self.ok

    def unwrap(self) -> Any:
        """成功时返回 data，失败时抛出"""
        if not self.ok:
            raise RuntimeError(self.error)
        return self.data


class BaseTool(ABC):
    """工具基类 — 所有工具的标准接口"""

    name: str = ""
    description: str = ""
    input_schema: dict = {}
    timeout: float = 30.0
    retry_on_error: bool = True

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        ...

    def __call__(self, **kwargs) -> ToolResult:
        """统一入口：自动计时 + 异常包装 + 旧工具兼容"""
        start = time.perf_counter()
        try:
            result = self.execute(**kwargs)
            if isinstance(result, ToolResult):
                result.duration_ms = (time.perf_counter() - start) * 1000
                return result
            # 旧工具返回其他格式 → 自动包装
            duration = (time.perf_counter() - start) * 1000
            return ToolResult(ok=True, data=result, duration_ms=duration)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ToolResult(ok=False, error=str(e), duration_ms=duration)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


def wrap_tool(fn, name: str, description: str = "", input_schema: dict = None,
              timeout: float = 30.0) -> BaseTool:
    """将现有函数包装为 BaseTool 子类实例

    用法:
        from tools.tool_definitions import code_run as _code_run
        code_run = wrap_tool(_code_run, "code_run", "代码执行器")

    Args:
        fn: 现有工具函数
        name: 工具名
        description: 功能描述
        input_schema: JSON Schema
        timeout: 超时(秒)

    Returns:
        BaseTool 实例，调用返回 ToolResult
    """
    cls = type(name, (BaseTool,), {
        'name': name,
        'description': description,
        'input_schema': input_schema or {},
        'timeout': timeout,
        '_fn': staticmethod(fn),
        'execute': lambda self, **kwargs: self._fn(**kwargs),
    })
    return cls()
