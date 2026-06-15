"""
Shim: re-export from tools.llm_providers._llm for backward compatibility.
"""
import warnings
warnings.warn("tools._llm is deprecated, use tools.llm_providers._llm instead",
              DeprecationWarning, stacklevel=2)

from tools.llm_providers._llm import *  # nosec
try:
    from tools.llm_providers._llm import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
