"""
weread_extract.py — 微信读书章节提取
用目录(TOC)逐章点击，提取每章内容
"""

import re
import time
import json
import os
import sys

def _get_driver():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, root)
    import TMWebDriver
    d = TMWebDriver.TMWebDriver(host='127.0.0.1', port=18765)
    s = d.get_all_sessions()
    if not s:
        raise ConnectionError('无浏览器连接')
    d.set_session('')
    return d

def _js(driver, code, timeout=15):
    try:
        r = driver.execute_js(code, timeout=timeout)
        if isinstance(r, dict):
            return str(r.get('data', '') or r.get('result', '') or '')
        return str(r)
    except Exception as e:
        return f'[JS_ERR:{e}]'

def _click_cat(driver):
    """切换目录开/关"""
    return _js(driver, "var b=document.querySelector('button.readerControls_item.catalog[title=\"目录\"]');if(b){b.click();return 'ok'}return 'nf'")

def weread_collect_all(url, stop_kw=None):
    if stop_kw is None:
        stop_kw = ['附录', 'Appendix', '索引', 'Index']
    driver = _get_driver()
    driver.jump(url)
    time.sleep(4)

    # 开目录
    _click_cat(driver)
    time.sleep(2)

    # 获取章节
    r = _js(driver, (
        "var items=document.querySelectorAll('.readerCatalog_list_item');"
        "var res=[];"
        "for(var i=0;i<items.length;i++){"
        "var te=items[i].querySelector('.readerCatalog_list_item_title_text');"
        "var t=te?te.textContent.trim():'';"
        "if(t)res.push({idx:i,title:t});"
        "}"
        "return JSON.stringify(res);"
    ))
    try:
        chapters = json.loads(r)
    except:
        chapters = []
    if not chapters:
        return ''

    # 过滤
    filtered = []
    for ch in chapters:
        if any(kw in ch.get('title','') for kw in stop_kw):
            break
        filtered.append(ch)
    print(f'  [WeRead] {len(filtered)}/{len(chapters)} 章（跳过附录）')

    # 逐章提取 - 保持目录打开状态
    all_text = []
    for i, ch in enumerate(filtered):
        title = ch.get('title', f'ch{i+1}')
        idx = ch.get('idx', i)
        print(f'  [{i+1}/{len(filtered)}] {title[:30]}...', end='', flush=True)

        # 关闭目录（如果已开），然后点击章节项
        _js(driver, (
            "var items=document.querySelectorAll('.readerCatalog_list_item');"
            f"if(items[{idx}])items[{idx}].click();"
            "return 'ok';"
        ))
        time.sleep(2.5)

        # 提取
        text = _js(driver, (
            "var pr=document.getElementById('preRenderContainer');"
            "if(pr){var cc=pr.querySelector('.readerChapterContent');"
            "if(cc)return(cc.innerText||'').trim();"
            "return(pr.innerText||'').substring(0,30000).trim();}"
            "return(document.body.innerText||'').substring(0,5000);"
        ))
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 20:
            all_text.append(f'\n=== {title} ===\n{text}')
            print(f' {len(text)}c')
        else:
            print(' 空')

        # 重新打开目录
        _click_cat(driver)
        time.sleep(1)

    full = '\n'.join(all_text)
    print(f'  [WeRead] DONE: {len(full):,} 字符')
    return full

def extract_url_cases(url):
    text = weread_collect_all(url)
    if not text:
        return []
    parts = re.split(r'\n=== ', text)
    cases = []
    for i, p in enumerate(parts):
        if not p.strip():
            continue
        for j in range(0, len(p), 2000):
            seg = p[j:j+2000]
            if seg.strip():
                cases.append({'source':'weread','type':'article','key':f'{url}#c{i+1}p{j//2000+1}','description':seg,'tags':[],'score':1.0,'relevance':'high','title':f'段{i+1}'})
    print(f'  [WeRead] => {len(cases)} 条案例')
    return cases

if __name__ == '__main__':
    u = sys.argv[1] if len(sys.argv) > 1 else 'https://weread.qq.com/web/reader/ba342e93643425f424e4339647839644b356a6c38366b367837383032304e51acdkc4c329b011c4ca4238a0201'
    c = extract_url_cases(u)
    t = sum(len(x['description']) for x in c)
    print(f'\n{len(c)} cases, {t:,} chars')
