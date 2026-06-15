# Bugfix: HTTP 400 "Messages with role 'tool' must be a response to a preceding message with 'tool_calls'"

Date: 2026-05-29
Author: Agent (diagnosis + fix)
File: `llmcore.py` (GA Core)
Status: Fixed, pending runtime verification

## Symptom

OpenAI API returns HTTP 400 error when `NativeToolClient` makes a second call after receiving `tool_use` from the model:

```
HTTP 400: {"error":{"message":"Messages with role 'tool' must be a response to a preceding message with 'tool_calls'", ...}}
```

This only occurs with OpenAI-based sessions (`NativeOAISession`), not with Claude session (`NativeClaudeSession`). The error triggers on the second `chat()` call in a tool-calling sequence.

## Root Cause

The bug has two parts in the execution chain:

### Primary Root Cause: `BaseSession.ask()` drops tool_use assistant from history

File: `llmcore.py`, line ~336 (original)

```python
# ORIGINAL CODE (faulty)
if content.strip() and not content.startswith("!!!Error:"):
    self.history.append({"role": "assistant", "content": [{"type": "text", "text": content}]})
```

When the model returns `tool_use` blocks (no text content), `content` is empty string `""`, so `content.strip()` is falsy, and the assistant message is **never appended to `self.history`**.

This causes the following chain:

1. **Round 1**: `NativeToolClient.chat()` calls `BaseSession.ask(prompt)` -> model returns `tool_use` -> tool_use assistant NOT saved to history -> only tool_use yielded to caller
2. `NativeToolClient` executes the tool, gets result, then calls `chat()` again with merged message: `{"role": "user", "content": [tool_result..., text...]}`
3. **Round 2**: `BaseSession.ask(merged)` appends merged to history (text field wraps the dict object) -> calls `make_messages()` -> history contains: `[user(round1), user(round2_with_tool_result)]` -- NO assistant between them
4. `raw_ask()` -> `_fix_messages()` -> `_msgs_claude2oai()`
5. **`_msgs_claude2oai`** in the user branch (line ~259): encounters `tool_result` block -> creates `{"role": "tool", "tool_call_id": ...}` message
6. **This `tool` message has NO preceding `assistant` with matching `tool_calls`** -> OpenAI rejects with 400

The same flow works for Claude because Claude's API accepts tool_result in user messages directly; only OpenAI forces the strict `assistant.tool_calls` -> `tool` pairing.

### Secondary Issue: `_msgs_claude2oai` consecutive tool messages

When multiple `tool_result` blocks exist in the same user message (edge case), `_msgs_claude2oai` generates consecutive `{"role": "tool"}` messages without proper separation, also violating OpenAI's schema.

## Fix Applied

### Fix 1: `BaseSession.ask()` — Save tool_use assistant to history

```python
# FIXED CODE (llmcore.py lines 334-341)
tool_uses = [block for block in (content_blocks or []) if block.get('type', '') == 'tool_use']
if tool_uses:
    self.history.append({"role": "assistant", "content": content_blocks})
if tool_uses:
    for block in tool_uses:
        tu = {'name': block.get('name', ''), 'arguments': block.get('input', {})}
        yield f'<tool_use>{json.dumps(tu, ensure_ascii=False)}</tool_use>'
if content.strip() and not content.startswith("!!!Error:"):
    self.history.append({"role": "assistant", "content": [{"type": "text", "text": content}]})
```

Changes:
- Before yielding tool_use, first save the entire `content_blocks` (including tool_use blocks) as an assistant message to `self.history`
- The original text-content append remains unchanged for non-tool responses

### Fix 2: `_msgs_claude2oai` — Prevent consecutive tool messages

```python
# FIXED CODE (llmcore.py lines 274-276)
if text_parts: result.append({"role": "user", "content": text_parts})
# Ensure no consecutive tool messages: insert empty user if needed
if result and len(result) >= 2 and result[-1].get('role') == 'tool' and result[-2].get('role') == 'tool':
    result.insert(-1, {"role": "user", "content": [{"type": "text", "text": "."}]})
```

Adds a guard at the end of the `user` branch to detect and break consecutive `tool` messages by inserting a minimal `user` separator.

## Verification

Simulated full chain (history -> make_messages -> _fix_messages -> _msgs_claude2oai) with re-imported module:

```
=== OpenAI output ===
  [0] user: blocks=1
  [1] assistant: tool_calls=['call_abc123']
  [2] tool: id=call_abc123 paired=OK
  [3] user: blocks=1
[PASS] All tool messages properly paired!
```

Multi-tool same-turn and boundary cases also verified.

## Files Modified

- `llmcore.py` — 2 patches applied:
  - `BaseSession.ask()`: save tool_use assistant to history before yielding
  - `_msgs_claude2oai()`: guard against consecutive tool messages

## Note on Module Reload

Python caches imported modules in `sys.modules`. The running GA process may need to reload `llmcore` or restart to pick up changes. If the error persists after fix, verify the running process imports the updated file.
