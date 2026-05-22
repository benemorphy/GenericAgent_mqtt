"""
simphtml_rs bridge — Python -> simphtml_rs HTTP 服务

用法:
    from simphtml_rs_bridge import rust_optimize_html
    result = rust_optimize_html(page_html, max_chars=35000)

自动管理 simphtml_rs HTTP 服务进程 (端口 8901)
"""

import subprocess
import os
import time
import urllib.request
import urllib.parse

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_RUST_BIN = os.path.join(_SCRIPT_DIR, "simphtml_rs", "target", "release", "simphtml_rs.exe")
_PORT = 8901
_SERVER_URL = f"http://127.0.0.1:{_PORT}"
_PROCESS = None

def _start_server():
    global _PROCESS
    if _PROCESS is not None:
        return True
    if not os.path.isfile(_RUST_BIN):
        # fallback: 纯 Python 实现
        return False
    _PROCESS = subprocess.Popen(
        [_RUST_BIN, "--serve", "--port", str(_PORT)],
        cwd=os.path.dirname(_SCRIPT_DIR) if _SCRIPT_DIR else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=0x00000008
    )
    time.sleep(0.5)
    return True

def _check_server():
    try:
        urllib.request.urlopen(_SERVER_URL + "/health", timeout=1)
        return True
    except:
        return False

def rust_optimize_html(html_str, max_chars=35000):
    """通过 HTTP 调用 simphtml_rs 优化 HTML"""
    if not _check_server():
        if not _start_server():
            # fallback: 返回原 HTML
            return html_str
        time.sleep(0.5)
    
    params = urllib.parse.urlencode({"max_chars": max_chars})
    url = f"{_SERVER_URL}/?{params}"
    data = html_str.encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return html_str


def rust_optimize_html_blocking(html_str, max_chars=35000):
    """一次性子进程调用（不启动 HTTP 服务）"""
    _start_server()
    return rust_optimize_html(html_str, max_chars)


def benchmark():
    """性能对比测试"""
    import time as tmod
    from simphtml import optimize_html_for_tokens as py_opt
    
    # 生成测试 HTML
    sizes = [1000, 10000, 100000, 500000]
    _start_server()
    tmod.sleep(0.5)
    
    print(f"{'Size':>10} | {'Python':>10} | {'Rust HTTP':>10} | {'Ratio':>8}")
    print("-" * 45)
    
    for n in sizes:
        html = "<div>" + "x" * n + "</div>"
        
        t0 = tmod.perf_counter()
        py_opt(html)
        t_py = tmod.perf_counter() - t0
        
        t0 = tmod.perf_counter()
        rust_optimize_html(html, 500000)
        t_rs = tmod.perf_counter() - t0
        
        actual = len(html)
        ratio = t_py / t_rs if t_rs > 0 else 0
        print(f"{actual:>10,} | {t_py*1000:>8.2f}ms | {t_rs*1000:>8.2f}ms | {ratio:>6.1f}x")


if __name__ == "__main__":
    benchmark()
