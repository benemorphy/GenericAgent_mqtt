# 课件可视化 SOP — Mermaid 预渲染 & SVG 手绘图

## 核心原则

课件中的图示分为三类，使用场景不同：
1. **概念关系图** → mermaid flowchart/classDiagram（本体驱动，自动生成）
2. **生物结构图** → 手绘SVG（细胞/组织/器官等，不可用mermaid替代）
3. **其他学科图** → mermaid + CSS辅助

## Mermaid 预渲染管线

```
_build_mermaid_diagram() → ```mermaid文本
  → _save_html() → _prerender_mermaid_in_html()
  → mermaid_prerender.py → mermaid_render.mjs → Puppeteer+Chrome
  → 内联SVG嵌入index.html → CDN回退(备用)
```

## 已知坑点与对策

### 1. CDN类名冲突
**症状**: 页面报 "Syntax error in text mermaid version X.X.X"
**原因**: 预渲染SVG带 `class="mermaid"`，CDN mermaid.js `startOnLoad:true` 扫描后把SVG文本当mermaid语法解析
**修复**: 预渲染SVG用 `class="mermaid-rendered"`，CDN扫描用 `class="mermaid"`，两者不共用
**代码**: `storage.py` → `_prerender_mermaid_in_html` → `return f'<div class="mermaid-rendered">{svg}</div>'`

### 2. 管道符破坏mermaid语法
**症状**: mermaid渲染失败 "Parse error on line 2"
**原因**: edge label中混入 `|` 管道符（如 `A -->|前提|理解细胞膜结构| B`），`|` 是mermaid边标签分隔符
**修复**: 在 `_build_mermaid_diagram` 中对label做 `desc.replace('|', '丨')`
**注意**: 不仅是 `|`，`{` `}` `[` `]` 等mermaid特殊字符也可能导致问题

### 3. HTML实体编码
**症状**: mermaid语法中的 `-->` 在浏览器中显示为 `--&gt;`
**原因**: Python markdown库渲染 ` ```mermaid ` 代码块时做了HTML转义
**修复**: 在预渲染regex替换时调用 `html.unescape(m.group(1))`
**代码**: `storage.py` → `_replace_highlight` → `import html as _html; mmd_text = _html.unescape(...)`

### 4. Mermaid代码块多重格式
**mermaid文本在HTML中有三种格式**:
```
格式1: <div class="mermaid">text</div>           — diagram_renderer.py
格式2: ```mermaid\ntext\n```                      — markdown代码块
格式3: <pre><code class="language-mermaid">text</code></pre>  — Python markdown库渲染后
```
**对策**: `_prerender_mermaid_in_html` 必须同时匹配三种格式
**注意**: 格式2的 `\n` 可能是字面量（`\\n`）也可能是真实换行，regex用 `(?:\\\\n|\\n)` 匹配

### 5. CDN脚本守卫
**问题**: `if not _MERMAID_AVAILABLE:` 守卫在Node.js可用时跳过CDN，但预渲染不总是成功
**修复**: 无条件加载CDN脚本，预渲染SVG与CDN运行时渲染共存
**代码**: 删除 `if not _MERMAID_AVAILABLE:`，直接 `body_parts.append('<script type="module">...`)`

### 6. 字符串转义地狱
**问题**: 在Python code_run中修改regex时，多重转义（raw string + f-string + regex）导致实际写入文件的regex错误
**案例**: `r'```mermaid\\s*(?:\\\\n|\\n)(...)'` 在文件中变成了匹配 `\\n`（双反斜杠+n）而非 `\n`（单反斜杠+n）
**对策**: 写文件时避免Python code_run的代码块方式，改为：
  1. 写一个独立的 `.py` 脚本文件到 `temp/`
  2. 用 `powershell python temp/fix.py` 执行
  3. 在脚本中用 `repr()` 验证最终写入内容

### 7. 概念→模块映射丢失
**症状**: ontology-nav点击无效，moduleMap为空
**原因**: LLM生成的概念（7-8个）在CoursewarePhase后丢失，`cw['concepts']` 为空列表
**修复**: 在generate脚本中，`CoursewarePhase().execute()` 后手动合并LLM概念：
  ```python
  cw['concepts'] = plan_dict.get('concepts', resp.concepts)
  cw['relations'] = plan_dict.get('relations', resp.relations)
  ```

## 手绘SVG细胞图

### 创建新技能的规范流程

1. 创建独立模块: `app/domain/courseware/cell_diagram.py`
2. 实现 `generate_xxx()` 核心函数，返回SVG字符串
3. 实现 `inject_into_html()` 函数，注入到课件HTML
4. 注册API端点: `POST /api/v1/courseware/cell-diagram`
5. 集成到课件生成管线（在 `_make_demo_module` 中自动检测biology）

### SVG 构建原则

- 不用外部库，只用原生SVG标签（ellipse, circle, path, rect, text）
- 径向渐变(radialGradient)模拟细胞器质感
- 描边虚线(dasharray)区分细胞壁vs细胞膜
- 每个组件用独立函数（`_nucleus()`, `_mitochondrion()`, `_channel_protein()`）
- 包含图例(legend)说明颜色/符号含义

### 适用场景

| 图示类型 | 适合工具 | 原因 |
|---------|---------|------|
| 概念关系/流程图 | mermaid | 本体relations自动驱动 |
| 概念分类层级 | mermaid classDiagram | 本体概念结构映射 |
| **生物细胞/组织/器官** | **手绘SVG** | **需要视觉仿真，mermaid不支持圆形细胞** |
| 化学反应/分子结构 | mermaid + CSS | 简单结构用mermaid，复杂用SVG |
| 物理力场/电路 | CSS diagram + SVG | 视复杂度决定 |

## 调试流程

当课件中的图不显示时，按以下顺序排查：

```bash
# 1. 确认HTML中有SVG
python -c "import pathlib; h=pathlib.Path('app/data/coursewares/{cw_id}/index.html').read_text(); print(f'SVGs: {h.count(\"<svg\")}; mermaid残: {h.count(\"```mermaid\")}')"

# 2. 测试mermaid渲染
python -c "
import sys; sys.path.insert(0, '.')
from app.domain.courseware.mermaid_prerender import render_mermaid
text = 'graph LR\\n    A[测试] --> B[通过]'
print(render_mermaid(text)[:200])
"

# 3. 确认CDN脚本是否存在
findstr "cdn.jsdelivr" app/data/coursewares/{cw_id}/index.html

# 4. 检查class冲突
python -c "import pathlib; h=pathlib.Path('app/data/coursewares/{cw_id}/index.html').read_text(); print('冲突:', 'class=\"mermaid\"' in h and not 'mermaid-rendered' in h)"
```
