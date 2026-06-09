"""
Shim: re-export from services.todo_manager for backward compatibility.
"""
import warnings
warnings.warn("tools.todo_manager is deprecated, use services.todo_manager instead",
              DeprecationWarning, stacklevel=2)

from services.todo_manager import *  # nosec
try:
    from services.todo_manager import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
