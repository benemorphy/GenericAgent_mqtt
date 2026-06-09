"""
Shim: re-export from services.heartbeat_memory for backward compatibility.
"""
import warnings
warnings.warn("tools.heartbeat_memory is deprecated, use services.heartbeat_memory instead",
              DeprecationWarning, stacklevel=2)

from services.heartbeat_memory import *  # nosec
try:
    from services.heartbeat_memory import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
