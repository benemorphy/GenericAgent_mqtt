"""Slash command registry — replaces fragile monkey-patch chain with explicit dispatch.

The old approach: Each plugin (btw_cmd, continue_cmd) monkey-patches
cls._handle_slash_cmd, creating a fragile implicit chain dependent on import order.

The new approach: Plugins register into a handler list. agentmain dispatches
built-in commands first, then iterates registered handlers.

Usage:
    from tools.slash_cmd_registry import NOT_MINE, register, get_help_texts

    def my_handler(agent, raw_query, display_queue):
        if not raw_query.startswith('/mycmd'): return NOT_MINE
        # ... handle command, put result into display_queue
        return None  # consumed
    
    register('mycmd', my_handler, help_text='/mycmd - do something')
"""

_NOT_MINE = object()
"""Sentinel: handler returns this to signal 'not my command, try next'."""

NOT_MINE = _NOT_MINE  # public alias

_handlers: list = []  # [(handler_fn, help_text), ...]


def register(command_name: str, handler_fn, help_text: str = "") -> None:
    """Register a slash command handler.
    
    Args:
        command_name: Human-readable name (e.g. '/btw'), for help display.
        handler_fn: Callable(agent, raw_query, display_queue) -> 
            None (consumed), str (modified query to process), or NOT_MINE (skip).
        help_text: Description for help display.
    """
    _handlers.append((command_name, handler_fn, help_text))


def dispatch(agent, raw_query, display_queue):
    """Iterate registered handlers in registration order.
    
    Returns:
        None     — consumed by a handler
        str      — modified query to process further
        NOT_MINE — no handler matched
    """
    for _, handler_fn, _ in _handlers:
        result = handler_fn(agent, raw_query, display_queue)
        if result is not _NOT_MINE:
            return result
    return _NOT_MINE


def get_help_texts():
    """Return list of (command_name, help_text) for all registered commands."""
    return [(name, ht) for name, _, ht in _handlers if ht]
