# Rust 开发经验教训 (2026-05-22)

> 基于 md_server_rs + simphtml_rs 的完整开发经历

---

## 1. 工具链

### Windows GNU 工具链的 dlltool 问题
Rust 的 `stable-x86_64-pc-windows-gnu` 工具链在 Windows 上需要 `dlltool.exe` 来创建 Windows DLL 的导入库。自带的 `self-contained/dlltool.exe` 不支持 x86_64（仅有 32-bit 支持）。

**解决方案**: 下载 [w64devkit](https://github.com/skeeto/w64devkit) (73MB)，把它的 `as.exe` 和 `dlltool.exe` 复制到 Rust self-contained 目录。

### 环境变量
编译所需的环境变量：
- `GCC_EXEC_PREFIX` = `D:\tools\w64devkit\libexec\gcc\`
- `LIBRARY_PATH` = w64devkit 的 gcc lib 目录 + mingw lib 目录
- `PATH` 前导: w64devkit/bin + ~/.cargo/bin + Rust self-contained

## 2. 字符串转义地狱

### Python 写 Rust 源码的问题
用 Python 的 `'''...'''` 或 `r"""..."""` 写 Rust 源码时，Python 会把 `\"` 处理为转义字符 `"`，导致 Rust 字符串字面量在 `"` 处提前终止。

**表现**: Rust 编译报 `expected \`,\`, found \`/\`` 或 `prefix \`btn\` is unknown`。

**根因**: Python 三引号字符串中 `\"` 被转为 `"`，Rust 的 `format!(..."class=\"parent-btn"...")` 变成了 `format!(..."class="parent-btn"...")`，字符串在 `class="` 处提前结束。

**正确做法**: 
- 使用 `file_write` 工具直接写文件（不经过 Python 字符串处理）
- 或在 format 字符串中用单引号属性: `<a href='...'>` 替代 `<a href="...">`
- 或在 Rust 中写 `'\"'` 来避免转义

### 原始字符串的 `"#` 陷阱
Rust 的 `r#"..."#` 原始字符串以 `"#` 为终止符。JavaScript 中的 `querySelectorAll("#sidebar")` 包含 `"#` 会提前终止原始字符串。

**解决方案**: 使用 `r##"..."##` 多一层 `#`。

## 3. Borrow Checker 教训

### 函数拆分策略
当需要同时读和写同一个数据时（如 cutlist 检测后修改 HTML），拆成两个函数：
- `detect_hints(data: &str) -> Vec<Hint>` 只读
- 主函数收集 hints 后统一修改

### Regex 临时值
```rust
// 错误: Regex 临时值在语句结束时释放
let cleaned = Regex::new(r"\\s+").unwrap().replace_all(html, " ");

// 正确: 绑定到变量
let re = Regex::new(r"\\s+").unwrap();
let cleaned = re.replace_all(html, " ");
```

## 4. HTTP 服务实践

### 请求体解析
`req.lines()` 只去掉 `\n` 保留 `\r`，导致 `"\r".is_empty()` 为 false——HTTP 头部结束的空行永远检测不到。

**修复**: `line.trim().is_empty()` 替代 `line.is_empty()`。

### Path::join 的绝对路径陷阱
`Path::join("/file.md")` 会替换基路径（因为以 `/` 开头被认为绝对路径）。HTTP 请求路径有前导 `/`，需先 `trim_start_matches('/')`。

## 5. Rust MCP 工具推荐

| 工具 | 用途 | 解决什么问题 |
|------|------|------------|
| `dexwritescode/rust-mcp` | rust-analyzer MCP 封装 | 19 个工具: get_diagnostics/find_definition/cargo_build |
| `mcp-debugger` | LLDB 调试 | 单步调试 Rust 程序（async/panic） |
| `Zakarialabib/rustools-mcp` | 全栈助手 | 自动修复 borrow checker 错误、项目知识图谱、实时查 docs.rs |

---

## 总结

Rust 迁移在 2 个工作日内完成了 `md_server_rs`（Markdown 浏览器）和 `simphtml_rs`（HTML 简化引擎）的 HTTP 服务化实现，性能达到 78,672 req/s 吞吐量、15ms 处理 1MB HTML。关键收益在并发场景和大页面处理上体现，单次 subprocess 调用的 ~24ms 固定开销被降至 <3ms。

最大的时间消耗来自编译环境配置和字符串转义问题，而非 Rust 本身的开发难度。后续可考虑配置 Rust MCP 工具链来加速这类开发。
