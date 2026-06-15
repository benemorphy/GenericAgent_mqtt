"""
Shim: re-export from tools.security.hitl_approval for backward compatibility.
"""
import warnings
warnings.warn("tools.hitl_approval is deprecated, use tools.security.hitl_approval instead",
              DeprecationWarning, stacklevel=2)

from tools.security.hitl_approval import *  # nosec
try:
    from tools.security.hitl_approval import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
