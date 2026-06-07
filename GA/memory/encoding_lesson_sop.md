# 编码经验 SOP — Encoding Lesson

> PowerShell `Set-Content` 写入中文文件时，默认使用 **UTF-8 with BOM**，导致：
> 1. 中文注释被破坏（UTF-8 字节被解释为 GBK 乱码）
> 2. 与上游项目（UTF-8 without BOM）产生不必要 diff

## 问题现象

```
# 原始 (正确)
// 1. 用原生 setter 设置值（绕过 React）

# PowerShell Set-Content 后 (乱码)
// 1. 鐢ㄥ師鐢?setter 璁剧疆鍊硷紙缁曡繃 React锛?
```

## 正确做法

```powershell
# [错误] 使用 PowerShell Set-Content
$content = Get-Content file.py -Raw
$content = $content.Replace("A", "B")
Set-Content file.py -Value $content    # ← UTF-8 with BOM, 中文会乱码

# [正确] 使用 Python 读写 (默认 UTF-8 without BOM)
python -c "import pathlib; f=pathlib.Path('file.py'); f.write_text(f.read_text().replace('A','B'))"

# [正确] 使用 Python 移除 BOM
python -c "import pathlib; f=pathlib.Path('file.py'); b=f.read_bytes(); f.write_bytes(b[3:] if b[:3]==b'\xef\xbb\xbf' else b)"
```

## 规则

- **含中文的文件**：始终用 Python 的 `pathlib.write_text()` 读写
- **纯 ASCII 文件**：PowerShell 可用，但推荐统一走 Python
- **校验方法**：`file.ReadBytes()[:3]` 检查是否以 `EF BB BF` 开头
