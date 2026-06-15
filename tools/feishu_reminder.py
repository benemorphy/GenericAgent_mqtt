"""
Shim: re-export from services.feishu_reminder for backward compatibility.
"""
import warnings
warnings.warn("tools.feishu_reminder is deprecated, use services.feishu_reminder instead",
              DeprecationWarning, stacklevel=2)

from services.feishu_reminder import *  # nosec
try:
    from services.feishu_reminder import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
