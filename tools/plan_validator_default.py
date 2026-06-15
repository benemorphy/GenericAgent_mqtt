"""
Shim: re-export from tools.agent.plan_validator_default for backward compatibility.
"""
import warnings
warnings.warn("tools.plan_validator_default is deprecated, use tools.agent.plan_validator_default instead",
              DeprecationWarning, stacklevel=2)

from tools.agent.plan_validator_default import *  # nosec
try:
    from tools.agent.plan_validator_default import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
