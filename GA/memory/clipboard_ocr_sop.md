# Clipboard OCR SOP

**用途**: 读取用户剪贴板中的图片，调用本地OCR模型识别文字，理解用户意图。

## 环境
- OCR服务: `http://localhost:8090` (qwen3-vl-4b-yoyo-instruct-q8_0.gguf)
- 依赖: pillow / requests (已安装)

## 调用方法

```python
from memory.clipboard_ocr import ocr_clipboard, ocr_image_from_url, ocr_image_from_path

# 方式1: 读取剪贴板图片OCR（用户截图/复制图片后调用）
text = ocr_clipboard()
if text:
    print(f"识别到 {len(text)} 字: {text[:500]}")
    # 分析text理解用户意图...

# 方式2: URL图片OCR
text = ocr_image_from_url("https://example.com/image.png")

# 方式3: 本地图片文件OCR
text = ocr_image_from_path("C:/path/to/image.png")
```

## 触发时机
1. **用户主动告知** "我复制了图片/截图了" → 调用 `ocr_clipboard()`
2. **用户发送复杂指令** 但文字难以描述 → 推测用户可能截了图 → 询问后调用
3. **定时监听** (可选) 周期性检查剪贴板变化

## 意图理解流程
```
用户复制图片
    ↓
ocr_clipboard() → 识别文字
    ↓
分析文字 → 推断用户意图
    ↓
执行: 搜索/回答/操作/...
```

## 注意事项
- 剪贴板无图片时返回 `None`
- OCR API超时60秒,大图可能更久
- 识别结果可能含误识别,需结合上下文判断
- 模型名: `qwen3-vl-4b-yoyo-instruct-q8_0.gguf`