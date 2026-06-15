"""生成器安全的流式重试装饰器 + 工具函数"""

import functools
import time
import requests

_RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504, 529}

def _delay(resp, attempt):
    """指数退避，优先读取 Retry-After header"""
    try:
        ra = float((resp.headers or {}).get("retry-after"))
    except:
        ra = None
    return max(0.5, ra if ra is not None else min(30.0, 1.5 * (2 ** attempt)))

def should_retry(status_code):
    """判断 HTTP 状态码是否可重试"""
    return status_code in _RETRYABLE

def is_retryable_exception(e):
    """判断异常是否可重试"""
    return isinstance(e, (requests.Timeout, requests.ConnectionError))


def retry_stream(max_attempts_fn='max_retries'):
    """
    生成器安全的流式重试装饰器。

    专门为 yield-from 场景设计：内层生成器 yield !!!Error: 前缀字符串
    标记失败时，外层捕获后重试整个生成器。

    Args:
        max_attempts_fn: 返回最大重试次数的可调用对象或 session 属性名
    """
    def decorator(gen_func):
        @functools.wraps(gen_func)
        def wrapper(*args, **kwargs):
            sess = args[0] if args else None
            max_retries = 0
            if callable(max_attempts_fn):
                max_retries = max_attempts_fn(sess) if sess else 0
            else:
                max_retries = getattr(sess, max_attempts_fn or 'max_retries', 0)

            for attempt in range(max_retries + 1):
                gen = gen_func(*args, **kwargs)
                had_error = False
                try:
                    while True:
                        chunk = next(gen)
                        if isinstance(chunk, str) and chunk.startswith("!!!Error:"):
                            had_error = True
                        yield chunk
                except StopIteration as e:
                    if had_error and attempt < max_retries:
                        d = _delay(None, attempt)
                        print(f"[LLM Retry] error, retry in {d:.1f}s ({attempt+1}/{max_retries+1})")
                        time.sleep(d)
                        continue  # 重试整个生成器
                    return e.value  # 成功或用尽重试次数，返回结果
                except (requests.Timeout, requests.ConnectionError) as e:
                    err = f"!!!Error: {type(e).__name__}"
                    yield err
                    if attempt < max_retries:
                        d = _delay(None, attempt)
                        print(f"[LLM Retry] {type(e).__name__}, retry in {d:.1f}s ({attempt+1}/{max_retries+1})")
                        time.sleep(d)
                        continue  # 重试
                    return [{"type": "text", "text": err}]
            return
        return wrapper
    return decorator
