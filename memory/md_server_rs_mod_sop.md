# md_server_rs 修改 SOP — 添加多文件类型支持 + 语法高亮

**用途**：给 Rust 单线程 markdown 服务器添加渲染 .rs/.py 等代码文件的能力，并集成 highlight.js 语法高亮。

## 关键修改点

1. **扩展名管理**：添加 `SUPPORTED_EXTS` 常量 + `is_supported()` 函数，统一管理所有支持的文件类型，一处改多处生效
2. **路由判断**：`path.ends_with(".md")` → `is_supported(Path::new(&path))`
3. **渲染分支**：`.md` 走 pulldown-cmark markdown 渲染；其他扩展名用 `<pre><code class="language-{ext}">` 代码块
4. **导航栏**：sidebar 文件列表过滤条件从 `extension() == "md"` 改为 `is_supported()`
5. **语法高亮**：HTML 模板引入 highlight.js CDN（CSS + JS），`hljs.highlightAll()` 自动着色

## 注意事项

- 编译前先 `taskkill /f /im md_server_rs.exe` 释放 exe 文件锁
- walk() 函数搜索所有文件不限扩展名，无需修改
- 扩展名映射到 language-xxx 类名，hljs 自动识别
