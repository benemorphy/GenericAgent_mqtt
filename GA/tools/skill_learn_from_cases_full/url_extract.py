"""
url_extract.py — 双引擎URL文本提取模块
用于 skill_learn_from_cases 工具的 --from-url 功能

策略：先 requests 抓取静态HTML → 内容不足时自动降级到 TMWebDriver 浏览器引擎（JS渲染）
"""

import re, time, sys

def extract_url_text(url: str, max_chars: int = 15000) -> str:
    """双引擎提取：先requests，内容不足时TMWebDriver降级"""
    
    text = _requests_extract(url, max_chars)
    
    # 如果requests提取太少（<200字符），可能是JS渲染页面，用浏览器降级
    if len(text) < 200:
        print(f"  [URL] requests仅提取{len(text)}字符，尝试TMWebDriver浏览器引擎...")
        browser_text = _tmwebdriver_extract(url, max_chars)
        if browser_text and len(browser_text) > len(text):
            print(f"  [URL] TMWebDriver提取 {len(browser_text)} 字符（优于requests的{len(text)}）")
            text = browser_text
    
    return text


def _requests_extract(url: str, max_chars: int) -> str:
    """requests静态HTML提取"""
    import requests as req
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    try:
        resp = req.get(url, headers=headers, timeout=20, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        html = resp.text
    except Exception as e:
        print(f"  [URL] requests请求失败: {e}")
        return ""
    
    # Remove script/style content
    clean = re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract text from block-level tags
    texts = []
    for tag in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'span', 'article', 'section', 
                'td', 'blockquote', 'pre', 'label', 'a', 'th', 'title', 'textarea']:
        matches = re.findall(f'<{tag}[^>]*>(.*?)</{tag}>', clean, re.DOTALL | re.IGNORECASE)
        for m in matches:
            t = re.sub(r'<[^>]+>', '', m).strip()
            if t and len(t) > 3:
                texts.append(t)
    
    text = '\n'.join(texts)
    
    # Fallback: try body all text
    if not text:
        body = re.search(r'<body[^>]*>(.*)</body>', clean, re.DOTALL | re.IGNORECASE)
        if body:
            text = re.sub(r'<[^>]+>', '', body.group(1))
    
    text = re.sub(r'\s+', ' ', text).strip()
    text = text[:max_chars]
    print(f"  [URL] requests提取 {len(text)} 字符")
    return text


def _tmwebdriver_extract(url: str, max_chars: int, wait_sec: int = 5) -> str:
    """TMWebDriver浏览器引擎提取（处理JS渲染页面）"""
    try:
        import sys as _sys
        import os as _os
        
        # Insert project root in path
        _root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..'))
        _sys.path.insert(0, _root)
        
        import TMWebDriver as _tmwd
        
        driver = _tmwd.TMWebDriver(host='127.0.0.1', port=18765)
        
        # Check if browser is connected
        sessions = driver.get_all_sessions()
        if not sessions:
            print(f"  [URL] ⚠ TMWebDriver: 无浏览器连接")
            return ""
        
        # Navigate to URL using the first available session
        driver.set_session('')  # Use latest active session
        driver.jump(url)
        print(f"  [URL] TMWebDriver 导航到 {url}")
        time.sleep(wait_sec)  # Wait for JS rendering
        
        # Try to extract text via JS
        # Strategy 1: Get structured content from block elements
        js_code = """
        (function() {
            // Try content area first
            var selectors = ['article', 'main', '.content', '#content', '.article', '.post', '.read-content'];
            for (var i = 0; i < selectors.length; i++) {
                var el = document.querySelector(selectors[i]);
                if (el && el.innerText.trim().length > 100) {
                    return el.innerText.trim();
                }
            }
            // Fallback: collect text from all block elements
            var tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'blockquote', 'pre'];
            var parts = [];
            var all = document.querySelectorAll(tags.join(','));
            for (var j = 0; j < all.length; j++) {
                var t = all[j].innerText.trim();
                if (t) parts.push(t);
            }
            if (parts.length > 5) return parts.join('\\n');
            // Last resort: body innerText
            return document.body.innerText || '';
        })()
        """
        
        result = driver.execute_js(js_code, timeout=15)
        text = ''
        if isinstance(result, dict):
            text = result.get('data', '') or result.get('result', '') or ''
        elif isinstance(result, str):
            text = result
        
        text = re.sub(r'\s+', ' ', text).strip()
        text = text[:max_chars]
        print(f"  [URL] TMWebDriver提取 {len(text)} 字符")
        return text
        
    except Exception as e:
        print(f"  [URL] TMWebDriver 引擎异常: {e}")
        import traceback
        traceback.print_exc()
        return ""


def extract_url_cases(url: str, chunk_size: int = 2000) -> list:
    """从URL提取文本并分块返回案例列表"""
    text = extract_url_text(url)
    if not text:
        return []
    
    # Split into chunks
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size].strip()
        if chunk:
            chunks.append({
                "source": "url",
                "type": "article",
                "key": f"{url}#part{i//chunk_size+1}",
                "description": chunk,
                "tags": [],
                "score": 1.0,
                "relevance": "high",
                "title": f"{url} 第{i//chunk_size+1}部分"
            })
    
    print(f"  [URL] 分成 {len(chunks)} 条案例")
    return chunks


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://weread.qq.com/web/reader/88032bc0813abb40ag01891e"
    print(f"测试提取: {url}")
    cases = extract_url_cases(url)
    print(f"\n共 {len(cases)} 条案例")
    for i, c in enumerate(cases[:3]):
        print(f"\n--- Case {i+1} ({len(c['description'])} chars) ---")
        print(c['description'][:300])
