"""
Shim: re-export from tools.agent.hooks_default for backward compatibility.
"""
import warnings
warnings.warn("tools.hooks_default is deprecated, use tools.agent.hooks_default instead",
              DeprecationWarning, stacklevel=2)

from tools.agent.hooks_default import *  # nosec
try:
    from tools.agent.hooks_default import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
