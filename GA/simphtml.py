"""
simphtml — 浏览器页面简化 + JS 执行
HTML 优化由 Rust 实现 (simphtml_rs)，浏览器交互由 Python 处理。
"""

import time
import re

# ── 嵌入 JS ──────────────────────────────────────────────────
js_optHTML = r'''function optHTML(text_only=false) {
function createEnhancedDOMCopy() {  
  const nodeInfo = new WeakMap();  
  const ignoreTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'META', 'LINK', 'COLGROUP', 'COL', 'TEMPLATE', 'PARAM', 'SOURCE'];  
  const ignoreIds = ['ljq-ind'];  
  function cloneNode(sourceNode, keep=false) {  
    if (sourceNode.nodeType === 8 ||   
        (sourceNode.nodeType === 1 && (  
          ignoreTags.includes(sourceNode.tagName) ||   
          (sourceNode.id && ignoreIds.includes(sourceNode.id))  
        ))) {  
      return null;  
    }  
    if (sourceNode.nodeType === 3) return sourceNode.cloneNode(false);  
    const clone = sourceNode.cloneNode(false);
    if ((sourceNode.tagName === 'INPUT' || sourceNode.tagName === 'TEXTAREA') && sourceNode.value) clone.setAttribute('value', sourceNode.value);
    if (sourceNode.tagName === 'INPUT' && (sourceNode.type === 'radio' || sourceNode.type === 'checkbox') && sourceNode.checked) clone.setAttribute('checked', '');
    else if (sourceNode.tagName === 'SELECT' && sourceNode.value) clone.setAttribute('data-selected', sourceNode.value);  
    try { if (sourceNode.matches && sourceNode.matches(':-webkit-autofill')) { clone.setAttribute('data-autofilled', 'true'); if (!sourceNode.value) clone.setAttribute('value', '⚠️受保护-读tmwebdriver_sop的autofill章节提取'); } } catch(e) {}

    const isDropdown = sourceNode.classList?.contains('dropdown-menu') ||   
             /dropdown|menu/i.test(sourceNode.className) || sourceNode.getAttribute('role') === 'menu'; 
    const _ddItems = isDropdown ? sourceNode.querySelectorAll('a, button, [role="menuitem"], li').length : 0;
    const isSmallDropdown = _ddItems > 0 && _ddItems <= 7 && sourceNode.textContent.length < 500;  

    const childNodes = [];  
    for (const child of sourceNode.childNodes) {  
      const childClone = cloneNode(child, keep || isSmallDropdown);  
      if (childClone) childNodes.push(childClone);  
    }  
    if (sourceNode.tagName === 'IFRAME') {
      try {
        const iDoc = sourceNode.contentDocument || sourceNode.contentWindow?.document;
        if (iDoc && iDoc.body && iDoc.body.children.length > 0) {
          const wrapper = document.createElement('div');
          wrapper.setAttribute('data-iframe-content', sourceNode.src || '');
          for (const ch of iDoc.body.childNodes) {
            const c = cloneNode(ch, keep);
            if (c) wrapper.appendChild(c);
          }
          if (wrapper.childNodes.length) childNodes.push(wrapper);
        }
      } catch(e) {}
    }
    if (sourceNode.shadowRoot) {
      for (const shadowChild of sourceNode.shadowRoot.childNodes) {
        const shadowClone = cloneNode(shadowChild, keep);
        if (shadowClone) childNodes.push(shadowClone);
      }
    }

    const rect = sourceNode.getBoundingClientRect();
    const style = window.getComputedStyle(sourceNode);
    const area = (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) <= 0)?0:rect.width * rect.height;
    const isVisible = (rect.width > 1 && rect.height > 1 &&   
                  style.display !== 'none' && style.visibility !== 'hidden' &&   
                  parseFloat(style.opacity) > 0 &&  
                  Math.abs(rect.left) < 5000 && Math.abs(rect.top) < 5000) 
                  || isSmallDropdown;  
    const zIndex = style.position !== 'static' ? (parseInt(style.zIndex) || 0) : 0;
  
    let info = {
          rect, area, isVisible, isSmallDropdown, zIndex,
          style: {  
            display: style.display, visibility: style.visibility,  
            opacity: style.opacity, position: style.position
          }};
    
    const nonTextChildren = childNodes.filter(child => child.nodeType !== 3);  
    const hasValidChildren = nonTextChildren.length > 0;  
          
    if (hasValidChildren) {
      const childrenInfos = nonTextChildren.map(c => nodeInfo.get(c)).filter(i => i && i.rect && i.rect.width > 0 && i.rect.height > 0);
      const bgAlpha = (() => {
        const c = style.backgroundColor;
        if (!c || c === 'transparent') return 0;
        const m = c.match(/rgba?\([^)]+,\s*([\d.]+)\)/);
        return m ? parseFloat(m[1]) : 1;
      })();
      const hasVisualBg = bgAlpha > 0.1 || style.backgroundImage !== 'none' || (style.backdropFilter && style.backdropFilter !== 'none') || style.boxShadow !== 'none';
      
      if (!hasVisualBg && childrenInfos.length > 0) {
        const flowChildren = childrenInfos.filter(cInfo => cInfo.style && cInfo.style.position !== 'fixed' && cInfo.style.position !== 'absolute');
        if (flowChildren.length > 0) {
          let minL = Infinity, minT = Infinity, maxR = -Infinity, maxB = -Infinity;
          for (const cInfo of flowChildren) {
            minL = Math.min(minL, cInfo.rect.left);
            minT = Math.min(minT, cInfo.rect.top);
            maxR = Math.max(maxR, cInfo.rect.right);
            maxB = Math.max(maxB, cInfo.rect.bottom);
          }
          info.rect = { left: minL, top: minT, right: maxR, bottom: maxB, width: maxR - minL, height: maxB - minT };
          info.area = info.rect.width * info.rect.height;
        } else {
          const maxC = childrenInfos.filter(i => i.isVisible).sort((a, b) => b.area - a.area)[0];
          if (maxC && maxC.area > 10000 && (!isVisible || maxC.area > info.area * 5)) info = maxC;
        }
      }
    }

    if (sourceNode.nodeType === 1 && sourceNode.tagName === 'DIV') {    
      if (!hasValidChildren && !sourceNode.textContent.trim()) return null; 
    }  
    if (sourceNode.getAttribute && sourceNode.getAttribute('aria-hidden') === 'true' && !info.isVisible) {
      return null;
    }
    if (info.isVisible || hasValidChildren || keep) {  
      childNodes.forEach(child => clone.appendChild(child));  
      return clone;  
    }  
    return null;  
  }  

  return {  
    domCopy: cloneNode(document.body),  
    getNodeInfo: node => nodeInfo.get(node),  
    isVisible: node => {  
      const info = nodeInfo.get(node);  
      return info && info.isVisible;  
    }  
  };  
}  
const { domCopy, getNodeInfo, isVisible } = createEnhancedDOMCopy();
if (text_only) {
  const blocks = new Set(['DIV','P','H1','H2','H3','H4','H5','H6','LI','TR','SECTION','ARTICLE','HEADER','FOOTER','NAV','BLOCKQUOTE','PRE','HR','BR','DT','DD','FIGCAPTION','DETAILS','SUMMARY']);
  domCopy.querySelectorAll('*').forEach(el => {
    if (blocks.has(el.tagName)) el.insertAdjacentText('beforebegin', '\n');
  });
  domCopy.querySelectorAll('input:not([type=hidden]),textarea,select').forEach(el=>{
    const p=[el.tagName,el.id&&'#'+el.id,el.getAttribute('name')&&'name='+el.getAttribute('name'),el.tagName==='INPUT'&&'type='+(el.getAttribute('type')||'text'),el.getAttribute('placeholder')&&'"'+el.getAttribute('placeholder')+'"',el.getAttribute('data-autofilled')&&'autofilled',el.disabled&&'disabled',el.tagName==='SELECT'&&el.getAttribute('data-selected')&&'="'+el.getAttribute('data-selected')+'"'].filter(Boolean).join(' ');
    el.insertAdjacentText('beforebegin','\n['+p+']\n');
  });
  domCopy.querySelectorAll('button[disabled]').forEach(el=>el.insertAdjacentText('beforebegin','[DISABLED] '));
  return domCopy.textContent;
}
return domCopy.outerHTML;
}'''

js_findMainList = r'''
function findMainList(container) {
    const result = [];
    function scoreGroup(selector, elements, totalChildren) {
        const coverage = elements.length / totalChildren;
        let specificity = selector.startsWith('.') ? (0.6 + (selector.match(/\./g).length - 1) * 0.1)
            : (selector.includes('.') ? (0.7 + (selector.match(/\./g).length) * 0.1) : 0.3);
        return (coverage * 0.5) + (specificity * 0.5);
    }
    function findTopGroups(container, limit) {
        const children = Array.from(container.children).filter(c => !c.closest('svg'));
        const totalChildren = children.length;
        if (totalChildren < 3) return [];
        const minGroupSize = Math.max(3, Math.floor(totalChildren * 0.2));
        const groups = [];
        const tagFreq = {}, classFreq = {}, tagMap = {}, classMap = {};
        children.forEach(child => {
            const tag = child.tagName.toLowerCase();
            if (tag === "td") return;
            tagFreq[tag] = (tagFreq[tag] || 0) + 1;
            if (!tagMap[tag]) tagMap[tag] = [];
            tagMap[tag].push(child);
            if (child.className) {
                child.className.trim().split(/\s+/).forEach(cls => {
                    if (cls) { classFreq[cls] = (classFreq[cls] || 0) + 1;
                        if (!classMap[cls]) classMap[cls] = [];
                        classMap[cls].push(child); }
                });
            }
        });
        Object.keys(tagFreq).forEach(tag => {
            if (tag !== "div" && tagFreq[tag] >= minGroupSize)
                groups.push({selector: tag, elements: tagMap[tag], score: scoreGroup(tag, tagMap[tag], totalChildren) - 0.5});
        });
        Object.keys(classFreq).forEach(cls => {
            if (classFreq[cls] >= minGroupSize)
                groups.push({selector: '.' + CSS.escape(cls), elements: classMap[cls], score: scoreGroup('.' + cls, classMap[cls], totalChildren)});
        });
        groups.sort((a, b) => b.score - a.score);
        const filtered = groups.filter(g => g.score > 0.2);
        return filtered.slice(0, limit || 3);
    }
    function walk(node, depth) {
        if (depth > 8) return;
        const groups = findTopGroups(node, 3);
        for (const g of groups) {
            const score = (() => {
                if (g.elements.length < 3) return 0;
                const items = g.elements;
                const containerArea = node.getBoundingClientRect().width * node.getBoundingClientRect().height;
                if (containerArea === 0) return 0;
                let totalItemArea = 0, visibleItems = 0, itemAreas = [];
                items.forEach(item => {
                    const r = item.getBoundingClientRect();
                    const area = r.width * r.height;
                    if (area > 0) { totalItemArea += area; itemAreas.push(area); visibleItems++; }
                });
                if (visibleItems < 3) return 0;
                totalItemArea = Math.min(totalItemArea, containerArea * 0.98);
                const areaRatio = totalItemArea / containerArea;
                const areaScore = 40 / (1 + Math.exp(-12 * (areaRatio - 0.4)));
                let uniformityScore = 0;
                if (itemAreas.length >= 3) {
                    const mean = itemAreas.reduce((s, a) => s + a, 0) / itemAreas.length;
                    const variance = itemAreas.reduce((s, a) => s + Math.pow(a - mean, 2), 0) / itemAreas.length;
                    const cv = mean > 0 ? Math.sqrt(variance) / mean : 1;
                    uniformityScore = 20 * Math.exp(-2.5 * cv);
                }
                const baseScore = Math.log2(visibleItems) * 5 + Math.floor(visibleItems / 5) * 0.25;
                const countScore = Math.min(40, baseScore) * Math.max(0.1, uniformityScore / 20);
                const viewportArea = window.innerWidth * window.innerHeight;
                const containerViewportRatio = containerArea / viewportArea;
                const sizeScore = 2 * (1 - 1/(1 + Math.exp(-10 * (containerViewportRatio - 0.25))));
                let layoutScore = 0;
                if (items.length >= 3) {
                    const uniqueRows = new Set(items.map(item => Math.round(item.getBoundingClientRect().top / 5) * 5)).size;
                    const uniqueCols = new Set(items.map(item => Math.round(item.getBoundingClientRect().left / 5) * 5)).size;
                    if (uniqueRows === 1 || uniqueCols === 1) layoutScore = 20;
                    else { const coverage = Math.min(1, items.length / (uniqueRows * uniqueCols));
                        const efficiency = Math.max(0, 1 - (uniqueRows + uniqueCols) / (2 * items.length));
                        layoutScore = 20 * (0.7 * coverage + 0.3 * efficiency); }
                }
                return countScore + areaScore + uniformityScore + layoutScore + sizeScore;
            })();
            if (score > 100) {
                result.push({selector: g.selector, count: g.elements.length, score: score.toFixed(2)});
            }
        }
        for (const child of node.children) walk(child, depth + 1);
    }
    walk(container, 0);
    return result.sort((a, b) => b.score - a.score).slice(0, 5);
}
'''

temp_monitor_js = r'''
(function() {
    if (!window._tm) {
        window._tm = { all: new Set(), init: new Set(), id: null, extract: function() {
            const r = new Set();
            document.querySelectorAll('input,textarea,select,[contenteditable]').forEach(el => {
                if (el.tagName === 'SELECT') { const o = el.options[el.selectedIndex]; if (o) r.add(o.text); }
                else if (el.value && el.value.trim()) r.add(el.value.trim().slice(0, 200));
            });
            return r;
        }};
        const initial = window._tm.extract();
        initial.forEach(v => { window._tm.all.add(v); window._tm.init.add(v); });
        window._tm.id = setInterval(() => {
            const current = window._tm.extract();
            current.forEach(v => window._tm.all.add(v));
        }, 500);
    }
})();
'''

# ── 核心函数 ──────────────────────────────────────────────────

def get_main_block(driver, extra_js="", text_only=False):
    """从浏览器获取优化后的页面DOM"""
    js = f"{extra_js}\n{js_optHTML}\nreturn optHTML({str(text_only).lower()});"
    resp = driver.execute_js(js)
    page = resp.get('data', '') if isinstance(resp, dict) else str(resp)
    if text_only:
        page = re.sub(r' {2,}', ' ', page)
        page = re.sub(r'^ +', '', page, flags=re.M)
        page = re.sub(r'(\n\s*){3,}', '\n\n', page)
        return page.strip()
    return page


def get_temp_texts(driver):
    """获取临时的输入文本变化"""
    js = """function stopStrMonitor() {
        if (!window._tm) return [];
        clearInterval(window._tm.id);
        const final = window._tm.extract();
        const newlySeen = [...window._tm.all].filter(t => !window._tm.init.has(t));
        let result;
        if (newlySeen.length < 8) result = newlySeen;
        else result = newlySeen.filter(t => !final.has(t));
        delete window._tm;
        return result;
    }
    stopStrMonitor();
    """
    try:
        resp = driver.execute_js(js)
        data = resp.get('data', []) if isinstance(resp, dict) else resp
        return list(set(data))
    except Exception:
        return []


def find_changed_elements(before_html, after_html):
    """简单的HTML变化检测（不使用BeautifulSoup）"""
    if before_html == after_html:
        return {"changed": 0}
    # 简单行级对比
    before_lines = before_html.split('\n')
    after_lines = after_html.split('\n')
    
    # 使用最长公共子序列的简化版本
    import difflib
    diff = list(difflib.unified_diff(before_lines, after_lines, n=0))
    changed = len([l for l in diff if l.startswith('+') or l.startswith('-')]) // 2
    
    top_change = ""
    for l in diff:
        if l.startswith('+') and len(l) > 5:
            top_change = l.strip()
            break
    
    result = {"changed": changed}
    if top_change:
        result["top_change"] = top_change[:2000]
    return result


def get_html(driver, cutlist=False, maxchars=35000, instruction="", extra_js="", text_only=False):
    """获取简化后的页面HTML"""
    # 自动导入Rust桥接
    try:
        from tools.simphtml_rs_bridge import rust_optimize_html
    except ImportError:
        rust_optimize_html = None
    
    page = get_main_block(driver, extra_js=extra_js, text_only=text_only)
    
    if text_only:
        return page
    
    # 使用Rust桥接进行HTML优化（替换旧的optimize_html_for_tokens + BeautifulSoup）
    if rust_optimize_html:
        try:
            optimized = rust_optimize_html(page, maxchars)
            return optimized
        except Exception:
            pass
    
    # 降级：直接返回原始页面
    if len(page) > maxchars:
        page = page[:maxchars] + f'\n\n[TRUNCATED {len(page) - maxchars} chars]\n\n'
    return page


def execute_js_rich(script, driver, no_monitor=False):
    """执行JS，监控页面变化"""
    last_html = None
    if not no_monitor:
        try:
            last_html = get_html(driver, cutlist=False, extra_js=temp_monitor_js, maxchars=9999999)
        except Exception:
            pass
    
    result = None
    error_msg = None
    reloaded = False
    newTabs = []
    
    try:
        before_sids = set(driver.get_session_dict().keys())
        print(f"Executing: {script[:250]} ...")
        response = driver.execute_js(script)
        result = response['data'] if isinstance(response, dict) and 'data' in response else response.get('result') if isinstance(response, dict) else response
        if isinstance(response, dict) and response.get('closed', 0) == 1:
            reloaded = True
        time.sleep(1)
    except Exception as e:
        error = e.args[0] if e.args else str(e)
        if isinstance(error, dict):
            error.pop('stack', None)
        error_msg = str(error)
        print(f"Error: {error_msg}")
    
    rr = {
        "status": "failed" if error_msg else "success",
        "js_return": result,
        "tab_id": getattr(driver, 'default_session_id', None)
    }
    
    if reloaded:
        rr['reloaded'] = reloaded
    
    # 检测新标签页
    if isinstance(response, dict) and response.get('newTabs'):
        rr['newTabs'] = response['newTabs']
    else:
        try:
            after = driver.get_session_dict()
            before = before_sids if not error_msg else set()
            new_sids = {k: v for k, v in after.items() if k not in before}
            if new_sids:
                rr['newTabs'] = [{'id': k, 'url': v} for k, v in new_sids.items()]
                rr['suggestion'] = "页面已刷新，以上新标签页在执行期间连接。"
        except Exception:
            pass
    
    if error_msg:
        rr['error'] = error_msg
    
    if no_monitor:
        return rr
    
    # 收集临时文本变化
    if not reloaded:
        try:
            rr['transients'] = get_temp_texts(driver)
        except Exception:
            rr['transients'] = []
    
    # DOM变化检测
    if not reloaded and len(newTabs) == 0:
        try:
            current_html = get_html(driver, cutlist=False, maxchars=9999999)
            if last_html is None:
                raise Exception("no baseline")
            diff_data = find_changed_elements(last_html, current_html)
            change_count = diff_data.get('changed', 0)
            top_change = diff_data.get('top_change', '')
            diff_summary = f"DOM变化量: {change_count}"
            if top_change:
                diff_summary += f"\n最显著变化:\n{top_change}"
            transients = rr.get('transients', [])
            if change_count == 0 and not transients and len(newTabs) == 0:
                diff_summary += " (页面无变化)"
                rr['suggestion'] = "页面无明显变化"
            rr['diff'] = diff_summary
        except Exception:
            rr['diff'] = "页面变化监控不可用"
    
    return rr



