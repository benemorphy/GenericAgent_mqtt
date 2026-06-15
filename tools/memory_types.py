"""
Shim: re-export from tools.utils.memory_types for backward compatibility.
"""
import warnings
warnings.warn("tools.memory_types is deprecated, use tools.utils.memory_types instead",
              DeprecationWarning, stacklevel=2)

from tools.utils.memory_types import *  # nosec
try:
    from tools.utils.memory_types import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
