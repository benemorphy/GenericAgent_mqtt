"""
Shim: re-export from tools.mcp.ontology_model for backward compatibility.
"""
import warnings
warnings.warn("tools.ontology_model is deprecated, use tools.mcp.ontology_model instead",
              DeprecationWarning, stacklevel=2)

from tools.mcp.ontology_model import *  # nosec
try:
    from tools.mcp.ontology_model import __all__ as _old_all
    __all__ = _old_all
except ImportError:
    pass
