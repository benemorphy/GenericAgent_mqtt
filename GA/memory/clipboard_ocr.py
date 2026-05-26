"""
clipboard_ocr — 剪贴板图片OCR + 视觉理解模块
=============================================
能力:
  - OCR: 读取剪贴板图片 → 调用vision_api → 返回识别文字
  - 视觉理解: 读取剪贴板图片 → 调用vision_api → 返回结构化界面描述
依赖: pillow, requests, vision_api (local后端默认: http://localhost:8090)

用法:
    from memory.clipboard_ocr import ocr_clipboard, clipboard_understand
    text = ocr_clipboard()              # 从剪贴板读取并OCR
    desc = clipboard_understand()       # 从剪贴板读取并视觉理解
    desc = clipboard_understand(prompt="描述这个界面的功能")
"""

import io, os
from pathlib import Path
from typing import Optional

try:
    from PIL import ImageGrab, Image
except ImportError:
    ImageGrab = None
    Image = None

import requests

# ===== 默认配置 =====
OCR_BACKEND = os.environ.get("OCR_BACKEND", "local")  # 使用 vision_api 的 backend
OCR_SYSTEM_PROMPT = os.environ.get(
    "OCR_SYSTEM_PROMPT",
    "请精准识别图片中的所有文字，逐行输出，不要多余内容"
)

# ==== 统一视觉入口 ====
from memory.vision_api import ask_vision


def ocr_clipboard(prompt: str = "") -> Optional[str]:
    """
    从Windows剪贴板读取图片并OCR识别
    
    Args:
        prompt: 自定义识别提示词（留空使用默认）
    
    Returns:
        识别文字, 或 None (剪贴板无图片时)
    """
    if ImageGrab is None:
        raise ImportError("PIL (Pillow) 未安装，无法读取剪贴板")
    
    img = ImageGrab.grabclipboard()
    
    if img is None:
        return None
    
    if isinstance(img, list):
        # 剪贴板中是文件列表（如截图工具保存的临时文件）
        paths = [p for p in img if Path(p).suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.gif')]
        if not paths:
            return None
        img = Image.open(paths[0])
    
    # 通过 vision_api 统一入口调用
    text_prompt = prompt or OCR_SYSTEM_PROMPT
    return ask_vision(img, prompt=text_prompt, backend=OCR_BACKEND, timeout=60)


def ocr_image_from_url(url: str, prompt: str = "") -> str:
    """
    对URL图片进行OCR识别
    
    Args:
        url: 图片URL (http/https/data:)
        prompt: 自定义识别提示词
    
    Returns:
        识别文字
    """
    # 下载图片
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    
    text_prompt = prompt or OCR_SYSTEM_PROMPT
    return ask_vision(img, prompt=text_prompt, backend=OCR_BACKEND, timeout=60)


def ocr_image_from_path(filepath: str, prompt: str = "") -> str:
    """
    对本地图片文件进行OCR识别
    
    Args:
        filepath: 图片文件路径
        prompt: 自定义识别提示词
    
    Returns:
        识别文字
    """
    img = Image.open(filepath)
    text_prompt = prompt or OCR_SYSTEM_PROMPT
    return ask_vision(img, prompt=text_prompt, backend=OCR_BACKEND, timeout=60)


def clipboard_understand(prompt: str = "", backend: str = "") -> Optional[str]:
    """
    从剪贴板读取图片并进行视觉理解（非单纯OCR）
    
    用法: 截图 → Ctrl+C复制 → 发 /v → 本函数被调用
    
    Args:
        prompt: 自定义理解提示词（留空使用默认）
        backend: VLM后端，留空使用OCR_BACKEND
    
    Returns:
        理解描述文字, 或 None (剪贴板无图片时)
    """
    if ImageGrab is None:
        raise ImportError("PIL (Pillow) 未安装，无法读取剪贴板")
    
    img = ImageGrab.grabclipboard()
    
    if img is None:
        return None
    
    if isinstance(img, list):
        paths = [p for p in img if Path(p).suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.gif')]
        if not paths:
            return None
        img = Image.open(paths[0])
    
    use_backend = backend or OCR_BACKEND
    text_prompt = prompt or "请详细描述这张图片的内容，包括：界面布局、按钮和输入框的位置与文字、弹窗信息、整体功能。如果是窗口截图，描述窗口状态（是否在加载、有无错误提示等）"
    return ask_vision(img, prompt=text_prompt, backend=use_backend, timeout=60)


# ===== 便捷自测 =====
if __name__ == "__main__":
    import sys
    
    mode = "ocr"
    if len(sys.argv) > 1:
        if sys.argv[1] == "--understand":
            mode = "understand"
        elif sys.argv[1].startswith("http"):
            result = ocr_image_from_url(sys.argv[1])
            print(result)
            sys.exit(0)
        elif sys.argv[1] != "ocr":
            result = ocr_image_from_path(sys.argv[1])
            print(result)
            sys.exit(0)
    
    if mode == "understand":
        print("=== 视觉理解结果 ===")
        result = clipboard_understand()
    else:
        print("=== OCR 识别结果 ===")
        result = ocr_clipboard()
    
    if result:
        print(result)
    else:
        print("剪贴板中无图片，或识别失败")
        print("用法: python clipboard_ocr.py [--understand] [图片URL|本地路径]")