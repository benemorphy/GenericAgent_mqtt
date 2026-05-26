"""Claude Provider — SSE 解析 + Provider 类。

Phase 2 提取自 llmcore.py:
  - _parse_claude_sse (原L84)
  - _parse_claude_json (原L92)
  - _apply_claude_thinking (原L500, BaseSession的方法, 提取为独立函数)
  - ClaudeProvider (提供注册表集成)

依赖: 通过函数参数接收调用上下文，不使用全局变量。
"""

import json


def _parse_claude_json(data, record_usage=None):
    """Parse Claude non-streaming response. 
    Yields text chunks, returns content_blocks.
    
    Args:
        data: API response dict
        record_usage: optional callable(usage_dict, api_type) for usage tracking
    """
    content_blocks = data.get("content", [])
    if record_usage:
        record_usage(data.get("usage", {}), "messages")
    for b in content_blocks:
        if b.get("type") == "text":
            yield b.get("text", "")
        elif b.get("type") == "thinking":
            yield ""
    return content_blocks


def _parse_claude_sse(resp_lines, record_usage=None):
    """Parse Anthropic SSE stream. 
    Yields text chunks, returns list[content_block].
    
    Args:
        resp_lines: iterable of raw response lines
        record_usage: optional callable(usage_dict, api_type) for usage tracking
    """
    content_blocks = []
    current_block = None
    tool_json_buf = ""
    stop_reason = None
    got_message_stop = False
    warn = None

    for line in resp_lines:
        if not line:
            continue
        line = line.decode('utf-8') if isinstance(line, bytes) else line
        if not line.startswith("data:"):
            continue
        data_str = line[5:].lstrip()
        if data_str == "[DONE]":
            break
        try:
            evt = json.loads(data_str)
        except Exception as e:
            print(f"[SSE] JSON parse error: {e}, line: {data_str[:200]}")
            continue
        evt_type = evt.get("type", "")

        if evt_type == "message_start":
            usage = evt.get("message", {}).get("usage", {})
            if record_usage:
                record_usage(usage, "messages")
        elif evt_type == "content_block_start":
            block = evt.get("content_block", {})
            if block.get("type") == "text":
                current_block = {"type": "text", "text": ""}
            elif block.get("type") == "thinking":
                current_block = {"type": "thinking", "thinking": "", "signature": ""}
            elif block.get("type") == "tool_use":
                current_block = {
                    "type": "tool_use",
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": {},
                }
                tool_json_buf = ""
        elif evt_type == "content_block_delta":
            delta = evt.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if current_block and current_block.get("type") == "text":
                    current_block["text"] += text
                if text:
                    yield text
            elif delta.get("type") == "thinking_delta":
                if current_block and current_block.get("type") == "thinking":
                    current_block["thinking"] += delta.get("thinking", "")
            elif delta.get("type") == "signature_delta":
                if current_block and current_block.get("type") == "thinking":
                    current_block["signature"] = current_block.get("signature", "") + delta.get("signature", "")
            elif delta.get("type") == "input_json_delta":
                tool_json_buf += delta.get("partial_json", "")
        elif evt_type == "content_block_stop":
            if current_block:
                if current_block["type"] == "tool_use":
                    try:
                        current_block["input"] = json.loads(tool_json_buf) if tool_json_buf else {}
                    except:
                        current_block["input"] = {"_raw": tool_json_buf}
                content_blocks.append(current_block)
                current_block = None
        elif evt_type == "message_delta":
            delta = evt.get("delta", {})
            stop_reason = delta.get("stop_reason", stop_reason)
            out_usage = evt.get("usage", {})
            out_tokens = out_usage.get("output_tokens", 0)
            if out_tokens:
                print(f"[Output] tokens={out_tokens} stop_reason={stop_reason}")
        elif evt_type == "message_stop":
            got_message_stop = True
        elif evt_type == "error":
            err = evt.get("error", {})
            emsg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            warn = f"\n\n!!!Error: SSE {emsg}"
            break
        elif evt_type == "ping":
            pass
        else:
            print(f"[SSE] Unknown event type: {evt_type}")

    if not warn:
        if not got_message_stop and not stop_reason:
            warn = "\n\n[!!! 流异常中断，未收到完整响应 !!!]"
        elif stop_reason == "max_tokens":
            warn = "\n\n[!!! Response truncated: max_tokens !!!]"

    # Flush remaining
    if current_block:
        if current_block["type"] == "tool_use":
            try:
                current_block["input"] = (
                    json.loads(tool_json_buf) if tool_json_buf else {}
                )
            except:
                current_block["input"] = {"_raw": tool_json_buf}
        content_blocks.append(current_block)
        current_block = None

    if warn:
        print(f"[WARN] {warn.strip()}")
        content_blocks.append({"type": "text", "text": warn})
        yield warn

    return content_blocks


def _apply_claude_thinking(self, payload):
    """Apply Claude thinking config to payload.
    原 BaseSession 的方法，提取为独立函数。
    self 需有 thinking_type 和 thinking_budget_tokens 属性。
    """
    if self.thinking_type:
        thinking = {"type": self.thinking_type}
        if self.thinking_budget_tokens:
            thinking["budget_tokens"] = self.thinking_budget_tokens
        payload["thinking"] = thinking


# ── Claude Provider 注册 ──

from tools.llm_providers import ProviderRegistry, ProviderProtocol


class ClaudeProvider(ProviderProtocol):
    """Claude 原生 Provider — 使用 llmcore.NativeClaudeSession。"""
    NAME = "claude"

    @classmethod
    def match(cls, cfg_name: str) -> bool:
        low = cfg_name.lower()
        return 'claude' in low and 'native' in low

    @classmethod
    def create_session(cls, cfg: dict):
        from llmcore import NativeClaudeSession
        return NativeClaudeSession(cfg=cfg)


class ClaudeLegacyProvider(ProviderProtocol):
    """旧的 Claude API Provider — 使用 llmcore.ClaudeSession。"""
    NAME = "claude_legacy"

    @classmethod
    def match(cls, cfg_name: str) -> bool:
        low = cfg_name.lower()
        return 'claude' in low and 'native' not in low

    @classmethod
    def create_session(cls, cfg: dict):
        from llmcore import ClaudeSession
        return ClaudeSession(cfg=cfg)


# 自动注册
ProviderRegistry.register(ClaudeProvider)
ProviderRegistry.register(ClaudeLegacyProvider)
