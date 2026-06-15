"""
GUI视觉理解工具 - 双层架构(默认使用本地OCR)

用法:
    from gui_vision import understand_window, compare_ui_states, list_windows

    # 默认: 本地OCR
    state = understand_window("Chrome")

    # 指定后端: "offline"(OCR) | "local"(VLM) | "auto"(VLM→OCR回退)
    state = understand_window("记事本", backend="offline")
    state = understand_window("记事本", backend="local")   # 需要VLM服务

后端: offline(rapidocr OCR) → local(本地VLM, 需启动)
默认: offline (rapidocr)
"""
import time
import traceback
import ctypes
from pathlib import Path

# ===================== 可选依赖 =====================
_HAS_VISION = False
_HAS_WIN32 = False
_HAS_PYGETWINDOW = False
_HAS_OCR = False

try:
    from vision_api import ask_vision, LOCAL_MAX_PIXELS
    _HAS_VISION = True
except ImportError:
    ask_vision = None
    LOCAL_MAX_PIXELS = 200000  # fallback默认值

try:
    import win32gui
    import win32con
    _HAS_WIN32 = True
except ImportError:
    win32gui = None

try:
    import pygetwindow as gw
    _HAS_PYGETWINDOW = True
except ImportError:
    gw = None

try:
    from ocr_utils import ocr_image
    _HAS_OCR = True
except ImportError:
    ocr_image = None

from PIL import Image, ImageGrab

# ===================== 常量 =====================
VLM_TIMEOUT = 180  # VLM分析超时(秒) - 旧常量，保留兼容
JPEG_QUALITY = 85

# 超时配置(秒) - 每个后端独立超时
BACKEND_TIMEOUTS = {
    'local': 180,   # local VLM 超时(含模型推理, qwen3-vl-4b约50-100s)
    'offline': 15,  # offline OCR 超时(大图约10s, 留余量)
    'auto': 5,      # auto模式的local阶段超时(快速失败以回退)
}

# 降级事件日志路径
_DEGRATION_LOG = Path(__file__).resolve().parent.parent / "temp" / "gui_vision_degration.log"


def _log_degration_event(event_type: str, reason: str, meta: dict = None):
    """记录降级事件并输出到控制台

    Args:
        event_type: 事件类型 (如 'vlm_timeout', 'vlm_fail', 'fallback_to_offline')
        reason: 降级原因
        meta: 窗口元信息(可选)
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{event_type}] {reason}"
    if meta:
        entry += f" | window='{meta.get('title', 'unknown')}'"
    print(f"  ⚠️ 降级事件: {entry}")
    try:
        with open(_DEGRATION_LOG, 'a', encoding='utf-8') as f:
            f.write(entry + "\n")
    except Exception:
        pass
MAX_PIXELS = LOCAL_MAX_PIXELS  # 与vision_api本地后端一致: 截图与VLM入图统一尺寸限制
VLM_MAX_SIDE = 400  # VLM入图最长边阈值(px), qwen3-vl-4b实测: >400px时响应>100s, ≤400px可控制在60s内
UI_PROMPT = """请详细描述这个界面，列出所有可见的UI元素，每个元素包含坐标信息。格式：
- [label|10%,20%,30%,5%] 文本内容
- [button|50%,30%,15%,8%] 按钮文字
- [input|20%,10%,60%,5%] 输入框占位文字
- [link|...] 链接文字
- [icon|...] 图标描述
- [dialog|...] 弹窗标题和内容
- [other|...] 其他元素描述
坐标格式: left_x%, top_y%, width%, height% (相对于图片宽高的百分比,0-100)
最后给出界面整体功能摘要。"""


# ===================== VLM缓存 =====================
_WINDOW_CACHE = {}
_WINDOW_CACHE_TTL = 60  # 缓存有效期(秒)

def _get_cache_key(meta: dict) -> tuple:
    """生成缓存key: (窗口标题, 宽度, 高度)"""
    return (meta.get('title', ''), meta.get('width', 0), meta.get('height', 0))

def _check_cache(cache_key: tuple):
    """检查是否有有效的缓存结果"""
    if cache_key in _WINDOW_CACHE:
        entry = _WINDOW_CACHE[cache_key]
        if time.time() - entry['timestamp'] < _WINDOW_CACHE_TTL:
            return entry['result']
        else:
            del _WINDOW_CACHE[cache_key]
    return None

def _set_cache(cache_key: tuple, result: dict):
    """写入缓存"""
    _WINDOW_CACHE[cache_key] = {
        'result': result,
        'timestamp': time.time(),
    }


# ===================== 窗口工具 =====================

def _set_dpi_aware():
    """设置DPI感知，确保物理坐标准确"""
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def list_windows():
    """列出所有可见窗口及其元信息"""
    if not _HAS_PYGETWINDOW or not _HAS_WIN32:
        return []
    _set_dpi_aware()
    windows = gw.getWindowsWithTitle('')
    result = []
    for w in windows:
        hwnd = w._hWnd if hasattr(w, '_hWnd') else 0
        try:
            cls = win32gui.GetClassName(hwnd) if hwnd else ''
        except Exception:
            cls = ''
        result.append({
            'title': w.title or '',
            'class': cls,
            'hwnd': hwnd,
            'rect': [w.left, w.top, w.right, w.bottom] if hasattr(w, 'left') else [],
            'visible': w.visible if hasattr(w, 'visible') else False,
            'active': w.isActive if hasattr(w, 'isActive') else False,
        })
    return result


def _get_window_meta(hwnd: int) -> dict:
    """提取窗口元信息"""
    if not _HAS_WIN32:
        return {}
    try:
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        rect = list(win32gui.GetWindowRect(hwnd))
        visible = win32gui.IsWindowVisible(hwnd) != 0
        focused = hwnd == win32gui.GetForegroundWindow()

        # 客户区
        client = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))

        # 子窗口
        children = []
        def _enum_child(child_hwnd, _):
            try:
                children.append({
                    'hwnd': child_hwnd,
                    'title': win32gui.GetWindowText(child_hwnd),
                    'cls': win32gui.GetClassName(child_hwnd),
                })
            except Exception:
                pass
        win32gui.EnumChildWindows(hwnd, _enum_child, None)

        return {
            'title': title,
            'class': cls,
            'hwnd': hwnd,
            'rect': rect,  # [left, top, right, bottom] 物理坐标
            'client_rect': [client[0], client[1], client[2], client[3]],
            'client_origin': [client_left, client_top],
            'width': rect[2] - rect[0],
            'height': rect[3] - rect[1],
            'visible': visible,
            'focused': focused,
            'child_count': len(children),
        }
    except Exception as e:
        return {'error': str(e)}


def _capture_window(title: str):
    """
    按标题关键词查找窗口、激活、截取客户区
    返回: (img: PIL.Image, hwnd: int, meta: dict)
    """
    if not _HAS_PYGETWINDOW:
        raise RuntimeError("pygetwindow未安装")
    _set_dpi_aware()

    wins = gw.getWindowsWithTitle(title)
    if not wins:
        raise RuntimeError(f"未找到标题包含'{title}'的窗口")

    target = wins[0]
    hwnd = target._hWnd if hasattr(target, '_hWnd') else 0

    # 激活窗口
    try:
        target.activate()
        time.sleep(0.2)
    except Exception:
        pass  # 某些窗口不允许激活

    meta = _get_window_meta(hwnd) if hwnd else {}

    # 截取客户区
    if hwnd and _HAS_WIN32:
        client = win32gui.GetClientRect(hwnd)
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        right = left + client[2]
        bottom = top + client[3]
        # 保存客户区原点(物理坐标)，供坐标转换使用
        meta['client_origin'] = (left, top)
    else:
        # fallback: 用窗口矩形
        rect = meta.get('rect', [0, 0, 800, 600])
        left, top, right, bottom = rect
        meta['client_origin'] = (left, top)

    # 限制最小尺寸
    if right - left < 10 or bottom - top < 10:
        raise RuntimeError(f"窗口区域过小: {right-left}x{bottom-top}")

    img = ImageGrab.grab(bbox=(left, top, right, bottom))

    # 统一缩放：与vision_api._prepare_image保持一致的max_pixels逻辑
    w, h = img.size
    # 保存原始尺寸，供坐标缩放使用
    meta['original_width'] = w
    meta['original_height'] = h
    if w * h > MAX_PIXELS:
        scale = (MAX_PIXELS / (w * h)) ** 0.5
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        print(f"  📐 截图缩放: {w}×{h} → {new_w}×{new_h}")
        # 同步更新meta，确保截图尺寸与VLM入图尺寸一致
        meta['width'] = new_w
        meta['height'] = new_h

    return img, hwnd, meta


# ===================== VLM分析 =====================

# REMOVED: _analyze_vlm (lines 272-366) - archived in _archives/


# ===================== 离线分析 =====================

def _analyze_offline(img, hwnd: int, window_meta: dict = None) -> dict:
    """无VLM模式：窗口元信息+OCR文本+bbox坐标"""
    meta = _get_window_meta(hwnd) if hwnd else (window_meta or {})

    # 计算原始截图到当前resize后图像的缩放比例
    orig_w = meta.get('original_width', img.width)
    orig_h = meta.get('original_height', img.height)
    scale_x = orig_w / img.width if img.width > 0 else 1.0
    scale_y = orig_h / img.height if img.height > 0 else 1.0

    # OCR文字提取 + 坐标转换
    ocr_texts = []
    ui_elements = []
    if _HAS_OCR:
        try:
            result = ocr_image(img)
            if result and result.get('details'):
                for d in result['details']:
                    bbox_raw = d.get('bbox', [])
                    text = d.get('text', '')
                    conf = d.get('conf', 0)
                    if not bbox_raw or not text:
                        continue
                    # rapidocr bbox格式: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                    if isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                        xs = [p[0] for p in bbox_raw]
                        ys = [p[1] for p in bbox_raw]
                        x = int(min(xs) * scale_x)
                        y = int(min(ys) * scale_y)
                        w = int((max(xs) - min(xs)) * scale_x)
                        h_val = int((max(ys) - min(ys)) * scale_y)
                    elif isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                        # 格式: [x1, y1, x2, y2]
                        x = int(bbox_raw[0] * scale_x)
                        y = int(bbox_raw[1] * scale_y)
                        w = int((bbox_raw[2] - bbox_raw[0]) * scale_x)
                        h_val = int((bbox_raw[3] - bbox_raw[1]) * scale_y)
                    else:
                        continue

                    element = {
                        'type': 'text',
                        'text': text,
                        'bbox': [x, y, w, h_val],
                        'confidence': conf,
                    }
                    ui_elements.append(element)
                    ocr_texts.append(text)

            if result and result.get('lines') and not ocr_texts:
                ocr_texts = result['lines']
        except Exception:
            pass

    return {
        "status": "ok" if ui_elements else "unavailable",
        "ui_elements": ui_elements,
        "ocr_texts": ocr_texts,
        "window_meta": meta,
        "img_size": [orig_w, orig_h],
        "client_origin": meta.get('client_origin', None),
        "error": None if ui_elements else "未识别到文本元素",
        "summary": f"窗口'{meta.get('title', '')}' - OCR识别到{len(ui_elements)}个元素",
    }


# ===================== 坐标转换工具 =====================

def element_to_screen_coords(state: dict, element: dict) -> tuple:
    """
    将UI元素的bbox(截图像素坐标)转换为屏幕物理坐标，供 ljqCtrl.Click() 使用。

    参数:
        state: understand_window() 返回的完整状态dict
        element: ui_elements 中的某个元素，需含 'bbox': [x, y, w, h]

    返回:
        (screen_x, screen_y) 物理像素坐标，即元素bbox中心在屏幕上的物理位置
        若信息不足返回 None
    """
    bbox = element.get('bbox')
    client_origin = state.get('client_origin')
    if not bbox or len(bbox) < 4 or not client_origin or len(client_origin) < 2:
        return None
    # bbox: [x, y, w, h] 相对截图左上角(原始截图像素坐标)
    # client_origin: (left, top) 客户区左上角屏幕物理坐标
    center_x = bbox[0] + bbox[2] // 2
    center_y = bbox[1] + bbox[3] // 2
    screen_x = client_origin[0] + center_x
    screen_y = client_origin[1] + center_y
    return (screen_x, screen_y)


def element_bbox_to_screen_rect(state: dict, element: dict) -> list:
    """
    将元素bbox转换为屏幕物理矩形 [left, top, right, bottom]。
    用于区域截图或调试。
    """
    bbox = element.get('bbox')
    client_origin = state.get('client_origin')
    if not bbox or len(bbox) < 4 or not client_origin or len(client_origin) < 2:
        return None
    return [
        client_origin[0] + bbox[0],
        client_origin[1] + bbox[1],
        client_origin[0] + bbox[0] + bbox[2],
        client_origin[1] + bbox[1] + bbox[3],
    ]


# ===================== 主API =====================

# REMOVED: understand_window (lines 483-606) - archived in _archives/


def compare_ui_states(state1: dict, state2: dict) -> dict:
    """对比两次UI状态，返回差异"""
    diff = {
        "has_change": False,
        "new_dialogs": [],
        "disappeared_dialogs": [],
        "added_elements": [],
        "removed_elements": [],
        "summary": "无变化"
    }

    # 1. 窗口元信息对比
    m1 = state1.get("window_meta", {})
    m2 = state2.get("window_meta", {})
    t1 = m1.get("title", "")
    t2 = m2.get("title", "")
    if t1 != t2:
        diff["has_change"] = True
        diff["title_changed"] = f"{t1} → {t2}"

    # 2. 弹窗对比
    s1_dialogs = state1.get("ui_elements", [])
    s2_dialogs = state2.get("ui_elements", [])
    d1_texts = {d.get("text", "") for d in s1_dialogs if d.get("type") in ("dialog", "alert", "popup")}
    d2_texts = {d.get("text", "") for d in s2_dialogs if d.get("type") in ("dialog", "alert", "popup")}
    new_d = list(d2_texts - d1_texts)
    gone_d = list(d1_texts - d2_texts)
    if new_d:
        diff["new_dialogs"] = new_d
        diff["has_change"] = True
    if gone_d:
        diff["disappeared_dialogs"] = gone_d
        diff["has_change"] = True

    # 3. 全部UI元素对比（用text作标识）
    all1 = {e.get("text", "") for e in s1_dialogs}
    all2 = {e.get("text", "") for e in s2_dialogs}
    added_el = [e for e in s2_dialogs if e.get("text", "") not in all1]
    removed_el = [e for e in s1_dialogs if e.get("text", "") not in all2]
    if added_el:
        diff["added_elements"] = added_el
        diff["has_change"] = True
    if removed_el:
        diff["removed_elements"] = removed_el
        diff["has_change"] = True

    # 4. 概要
    parts = []
    if diff.get("title_changed"):
        parts.append(f"窗口切换: {diff['title_changed']}")
    if new_d:
        parts.append(f"新弹窗({len(new_d)}): {new_d[:3]}")
    if gone_d:
        parts.append(f"弹窗消失({len(gone_d)}): {gone_d[:3]}")
    if added_el:
        parts.append(f"新元素({len(added_el)}): {[(e['type'],e['text'][:10]) for e in added_el[:3]]}")
    if removed_el:
        parts.append(f"元素消失({len(removed_el)}): {[(e['type'],e['text'][:10]) for e in removed_el[:3]]}")
    if not parts and not diff["has_change"]:
        parts.append("无变化")
    diff["summary"] = "; ".join(parts)

    return diff


# ===================== 自测试 =====================

if __name__ == "__main__":
    print("=== gui_vision 自测试 ===\n")

    print("可用窗口:")
    for w in list_windows()[:8]:
        print(f"  {w['title'][:50]} | visible={w['visible']}")

    target = "PowerShell"
    print(f"\n--- offline模式: '{target}' ---")
    result = understand_window(target, backend="offline")
    print(f"  status: {result['status']}")
    print(f"  backend: {result['backend_used']}")
    print(f"  窗口标题: {result['window_meta'].get('title','')}")
    print(f"  OCR文本数: {len(result['ocr_texts'])}")
    print(f"  summary: {result['summary']}")
