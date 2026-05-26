"""
Metaso 搜索引擎封装
从 keychain 读取 API key，提供简洁的搜索接口。
依赖: `pip install requests`（如未安装）

用法:
    from tools.metaso_search import metaso_search
    results = metaso_search("你的搜索词", size=5)
    for r in results:
        print(r["title"], r["url"])
"""
import requests
from typing import List, Dict, Optional

BASE_URL = "https://metaso.cn/api/v1"


def _get_api_key() -> str:
    """从 keychain 获取 Metaso API Key"""
    from memory.keychain import keys
    return keys.metaso_api_key.use()


def metaso_search(
    keyword: str,
    scope: str = "webpage",
    size: int = 5,
    include_summary: bool = True,
    concise_snippet: bool = False,
    verify_ssl: bool = False,
    timeout: int = 60,
) -> List[Dict]:
    """Metaso 搜索，返回结构化结果列表

    参数:
        keyword: 搜索关键词
        scope: 搜索范围 (webpage / news / academic 等)
        size: 返回结果数量 (1-20)
        include_summary: 是否包含摘要
        concise_snippet: 是否精简摘要
        verify_ssl: 是否验证 SSL 证书（默认 False 兼容 Windows 证书问题）
        timeout: HTTP 超时秒数（默认 60）

    返回:
        [{"title": str, "url": str, "snippet": str, "score": float}, ...]
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    api_key = _get_api_key()
    resp = requests.post(
        f"{BASE_URL}/search",
        json={
            "q": keyword,
            "scope": scope,
            "size": min(size, 20),
            "includeSummary": include_summary,
            "conciseSnippet": concise_snippet,
        },
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        verify=verify_ssl,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    webpages = data.get("webpages", [])
    results = []
    for w in webpages:
        results.append({
            "title": w.get("title", ""),
            "url": w.get("link", ""),
            "snippet": w.get("snippet", ""),
            "score": w.get("score", 0),
        })
    return results


def metaso_search_text(keyword: str, size: int = 5) -> str:
    """便捷版：直接返回可读文本，适合 web_execute_js / 命令行场景

    返回格式:
        [1] 标题1
            URL: https://...
            摘要: xxx
        [2] 标题2
            ...
    """
    results = metaso_search(keyword, size=size)
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(f"    URL: {r['url']}")
        if r['snippet']:
            lines.append(f"    摘要: {r['snippet']}")
        lines.append("")
    return "\n".join(lines) if lines else "（无结果）"


if __name__ == "__main__":
    import sys
    kw = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "测试搜索"
    print(metaso_search_text(kw))