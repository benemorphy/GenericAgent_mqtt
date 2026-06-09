"""
Shim: re-export from tools.skills.brainstorm_swarm for backward compatibility.
"""
import warnings
warnings.warn("tools.brainstorm_swarm is deprecated, use tools.skills.brainstorm_swarm instead",
              DeprecationWarning, stacklevel=2)

from tools.skills.brainstorm_swarm import *  # nosec
try:
    from tools.skills.brainstorm_swarm import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
