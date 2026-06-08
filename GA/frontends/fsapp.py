import json
import os
import re
import sys
import threading
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GA_ROOT = os.path.join(PROJECT_ROOT, "GA")
FRONTENDS_ROOT = os.path.join(GA_ROOT, "frontends")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, FRONTENDS_ROOT)
sys.path.insert(0, GA_ROOT)
os.chdir(PROJECT_ROOT)
from agentmain import GeneraticAgent
from frontends.chatapp_common import format_restore, create_agent
from frontends.continue_cmd import handle_frontend_command as handle_continue_frontend, reset_conversation

agent, mykeys = create_agent(verbose=False)
from tools.feishu_reminder import ReminderManager, start_reminder_checker, format_reminder_list, REMIND_HELP
from tools.todo_manager import TodoManager
from tools.hitl_approval import approve, reject, get_pending_list
from Mqtt_bbs_server import AgentBoardWithPersistence

import traceback
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

_TAG_PATS = [r"<" + t + r">.*?</" + t + r">" for t in ("thinking", "summary", "tool_use", "file_content")]
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tiff", ".tif"}
_AUDIO_EXTS = {".opus", ".mp3", ".wav", ".m4a", ".aac"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
_FILE_TYPE_MAP = {
    ".opus": "opus",
    ".mp4": "mp4",
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "doc",
    ".xls": "xls",
    ".xlsx": "xls",
    ".ppt": "ppt",
    ".pptx": "ppt",
}
_MSG_TYPE_MAP = {"image": "[image]", "audio": "[audio]", "file": "[file]", "media": "[media]", "sticker": "[sticker]"}

TEMP_DIR = os.path.join(GA_ROOT, "temp")
MEDIA_DIR = os.path.join(TEMP_DIR, "feishu_media")
os.makedirs(MEDIA_DIR, exist_ok=True)


_TRUNC_TAIL = 300  # 截断兜底时保留原文尾部字符数


def _clean(text):
    for pat in _TAG_PATS:
        text = re.sub(pat, "", text or "", flags=re.DOTALL)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_files(text):
    return re.findall(r"\[FILE:([^\]]+)\]", text or "")


def _strip_files(text):
    return re.sub(r"\[FILE:[^\]]+\]", "", text or "").strip()


def _display_text(text):
    cleaned = _strip_files(_clean(text))
    if cleaned:
        return cleaned
    tail = (text or "").strip()[-_TRUNC_TAIL:]
    return "（无文本输出）" + (f"\n…{tail}" if tail else "")


def _to_allowed_set(value):
    if value is None:
        return set()
    if isinstance(value, str):
        value = [value]
    return {str(x).strip() for x in value if str(x).strip()}


def _parse_json(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _extract_share_card_content(content_json, msg_type):
    parts = []
    if msg_type == "share_chat":
        parts.append(f"[shared chat: {content_json.get('chat_id', '')}]")
    elif msg_type == "share_user":
        parts.append(f"[shared user: {content_json.get('user_id', '')}]")
    elif msg_type == "interactive":
        parts.extend(_extract_interactive_content(content_json))
    elif msg_type == "share_calendar_event":
        parts.append(f"[shared calendar event: {content_json.get('event_key', '')}]")
    elif msg_type == "system":
        parts.append("[system message]")
    elif msg_type == "merge_forward":
        parts.append("[merged forward messages]")
    return "\n".join([p for p in parts if p]).strip() or f"[{msg_type}]"


def _extract_interactive_content(content):
    parts = []
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            return [content] if content.strip() else []
    if not isinstance(content, dict):
        return parts
    title = content.get("title")
    if isinstance(title, dict):
        title_text = title.get("content", "") or title.get("text", "")
        if title_text:
            parts.append(f"title: {title_text}")
    elif isinstance(title, str) and title:
        parts.append(f"title: {title}")
    elements = content.get("elements", [])
    if isinstance(elements, list):
        for row in elements:
            if isinstance(row, dict):
                parts.extend(_extract_element_content(row))
            elif isinstance(row, list):
                for el in row:
                    parts.extend(_extract_element_content(el))
    card = content.get("card", {})
    if card:
        parts.extend(_extract_interactive_content(card))
    header = content.get("header", {})
    if isinstance(header, dict):
        header_title = header.get("title", {})
        if isinstance(header_title, dict):
            header_text = header_title.get("content", "") or header_title.get("text", "")
            if header_text:
                parts.append(f"title: {header_text}")
    return [p for p in parts if p]


def _extract_element_content(element):
    parts = []
    if not isinstance(element, dict):
        return parts
    tag = element.get("tag", "")
    if tag in ("markdown", "lark_md"):
        content = element.get("content", "")
        if content:
            parts.append(content)
    elif tag == "div":
        text = element.get("text", {})
        if isinstance(text, dict):
            text_content = text.get("content", "") or text.get("text", "")
            if text_content:
                parts.append(text_content)
        elif isinstance(text, str) and text:
            parts.append(text)
        for field in element.get("fields", []) or []:
            if isinstance(field, dict):
                field_text = field.get("text", {})
                if isinstance(field_text, dict):
                    content = field_text.get("content", "") or field_text.get("text", "")
                    if content:
                        parts.append(content)
    elif tag == "a":
        href = element.get("href", "")
        text = element.get("text", "")
        if href:
            parts.append(f"link: {href}")
        if text:
            parts.append(text)
    elif tag == "button":
        text = element.get("text", {})
        if isinstance(text, dict):
            content = text.get("content", "") or text.get("text", "")
            if content:
                parts.append(content)
        url = element.get("url", "") or (element.get("multi_url", {}) or {}).get("url", "")
        if url:
            parts.append(f"link: {url}")
    elif tag == "img":
        alt = element.get("alt", {})
        if isinstance(alt, dict):
            parts.append(alt.get("content", "[image]") or "[image]")
        else:
            parts.append("[image]")
    for child in element.get("elements", []) or []:
        parts.extend(_extract_element_content(child))
    for col in element.get("columns", []) or []:
        for child in (col.get("elements", []) if isinstance(col, dict) else []):
            parts.extend(_extract_element_content(child))
    return parts


def _extract_post_content(content_json):
    def _parse_block(block):
        if not isinstance(block, dict) or not isinstance(block.get("content"), list):
            return None, []
        texts, images = [], []
        if block.get("title"):
            texts.append(block.get("title"))
        for row in block["content"]:
            if not isinstance(row, list):
                continue
            for el in row:
                if not isinstance(el, dict):
                    continue
                tag = el.get("tag")
                if tag in ("text", "a"):
                    texts.append(el.get("text", ""))
                elif tag == "at":
                    texts.append(f"@{el.get('user_name', 'user')}")
                elif tag == "img" and el.get("image_key"):
                    images.append(el["image_key"])
        text = " ".join([t for t in texts if t]).strip()
        return text or None, images

    root = content_json
    if isinstance(root, dict) and isinstance(root.get("post"), dict):
        root = root["post"]
    if not isinstance(root, dict):
        return "", []
    if "content" in root:
        text, imgs = _parse_block(root)
        if text or imgs:
            return text or "", imgs
    for key in ("zh_cn", "en_us", "ja_jp"):
        if key in root:
            text, imgs = _parse_block(root[key])
            if text or imgs:
                return text or "", imgs
    for val in root.values():
        if isinstance(val, dict):
            text, imgs = _parse_block(val)
            if text or imgs:
                return text or "", imgs
    return "", []


APP_ID = str(mykeys.get("fs_app_id", "") or "").strip()
APP_SECRET = str(mykeys.get("fs_app_secret", "") or "").strip()
ALLOWED_USERS = _to_allowed_set(mykeys.get("fs_allowed_users", []))
PUBLIC_ACCESS = not ALLOWED_USERS or "*" in ALLOWED_USERS
AGENT_TIMEOUT_SEC = 900

agent = GeneraticAgent()
threading.Thread(target=agent.run, daemon=True).start()
client, user_tasks = None, {}

# 提醒管理器
_reminder = ReminderManager()
_reminder_send = lambda oid, txt: send_message(oid, txt) if oid else None
_todo_mgr = TodoManager()
_master_board = None  # 延迟初始化 AgentBoardWithPersistence
_bbs_push_client = None  # BBS 桥接客户端
_inspiration_board = None  # 延迟初始化灵感板（单例，防止MQTT client_id冲突）
_bbs_push_chats = set()  # 订阅 BBS 推送的飞书聊天

def _get_board():
    global _master_board
    if _master_board is None:
        try:
            _master_board = AgentBoardWithPersistence("feishu_bot")
            print("[MQTT BBS] AgentBoardWithPersistence 已连接 (feishu_bot)")
        except Exception as e:
            print(f"[MQTT BBS] 连接失败: {e}")
    return _master_board

def _get_inspiration_board():
    """获取灵感板单例（避免重复创建导致MQTT client_id冲突）"""
    global _inspiration_board
    if _inspiration_board is None:
        from tools.inspiration_board import Board as _InspBoard
        _inspiration_board = _InspBoard(bbs_backend=True)
    return _inspiration_board

def _init_bbs_push():
    """初始化 BBS→飞书 推送线程"""
    global _bbs_push_client
    if _bbs_push_client is not None:
        return
    # 加载 MQTT 认证凭据（优先从环境变量读取，避免硬编码密钥）
    if not os.environ.get('MQTT_USERNAME'):
        os.environ['MQTT_USERNAME'] = 'feishu_bbs_bridge'
    if not os.environ.get('MQTT_PASSWORD'):
        # 从 mykeys 读取密码（如未配置，在本地 dev 环境使用默认密码）
        _mqtt_pwd = str(mykeys.get("mqtt_password", "") or "").strip()
        if _mqtt_pwd:
            os.environ['MQTT_PASSWORD'] = _mqtt_pwd
        else:
            print("[WARN] MQTT_PASSWORD 未设置，使用开发环境默认密码")
            os.environ['MQTT_PASSWORD'] = 'feishu_bridge_2024'
    for _retry in range(3):
        try:
            from Mqtt_bbs_client.board_client import BoardClient as _BC
            _bbs_push_client = _BC("feishu_bbs_bridge", board="agent-bbs-test")
            _bbs_push_client.connect()
            _bbs_push_client.subscribe("bbs/+/post", _on_bbs_new_post)
            print("[BBS桥接] ✅ BBS->飞书 推送已启动")
            
            # Nexus: 额外订阅 goal_nexus 主题（人机协作决策）
            _bbs_push_client.subscribe("bbs/goal_nexus/review", _on_nexus_request)
            _bbs_push_client.subscribe("bbs/goal_nexus/tasks", _on_nexus_request)
            print("[Nexus桥接] ✅ goal_nexus 人机协作推送已启动")
            break
        except Exception as e:
            print(f"[BBS桥接] 初始化失败(第{_retry+1}次): {e}")
            if _retry < 2:
                import time; time.sleep(2 ** _retry)

# 记录最近推送的帖子ID，避免重复推送
_bbs_pushed_ids = set()
_BBS_PUSHED_MAX = 10000  # 防止内存泄漏
def _on_bbs_new_post(topic, payload):
    """BBS 新帖回调 → 推送到飞书"""
    global _bbs_push_chats, _bbs_pushed_ids
    if not _bbs_push_chats or not isinstance(payload, dict):
        return
    post_id = payload.get("id", 0)
    if post_id in _bbs_pushed_ids:
        return
    # 控制集合大小，防内存泄漏
    if len(_bbs_pushed_ids) >= _BBS_PUSHED_MAX:
        _bbs_pushed_ids = set(list(_bbs_pushed_ids)[-_BBS_PUSHED_MAX//2:])
    _bbs_pushed_ids.add(post_id)
    if len(_bbs_pushed_ids) > 1000:
        _bbs_pushed_ids.clear()
    
    content = payload.get("content", "")
    author = payload.get("author", "?")
    board = topic.split("/")[1] if topic.count("/") >= 1 else "?"
    msg = f"📢 [BBS/{board}] {author}: {str(content)[:200]}"
    
    for chat_id in list(_bbs_push_chats):
        try:
            send_message(chat_id, msg, receive_id_type="chat_id")
        except Exception as e:
            print(f"[BBS桥接] ⚠️ 推送失败到 {chat_id}: {e}")

# ── Nexus: 人机协作决策处理 ──
_NEXUS_PUSH_CHATS = set()
def _on_nexus_request(topic, payload):
    """Nexus 人机协作请求 → 推送到飞书卡片"""
    if not isinstance(payload, dict):
        return
    content = payload.get("content", payload)
    if isinstance(content, dict):
        decision_text = content.get("decision", str(content)[:500])
        options = content.get("options", [])
        rec = content.get("recommendation", "")
        corr_id = content.get("corr_id", "")
    else:
        decision_text = str(content)[:500]
        options, rec, corr_id = [], "", ""
    for chat_id in list(_NEXUS_PUSH_CHATS):
        try:
            card = {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": "Goal Agent 需要决策"}, "template": "blue"},
                "elements": [
                    {"tag": "markdown", "content": f"**{decision_text}**"},
                    {"tag": "hr"},
                ]
            }
            if options and corr_id:
                buttons = []
                for opt in options[:5]:  # 最多5个按钮
                    btn = {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": str(opt)[:30]},
                        "value": {"corr_id": str(corr_id), "choice": str(opt)},
                        "type": "primary" if opt == rec else "default",
                    }
                    buttons.append(btn)
                card["elements"].append({"tag": "action", "actions": buttons})
            elif options:
                card["elements"].append({"tag": "markdown", "content": "**选项**:\n" + chr(10).join([f"- {o}" for o in options])})
            if rec and not corr_id:
                card["elements"].append({"tag": "markdown", "content": f"**推荐**: {rec}"})
            if corr_id:
                card["elements"].append({"tag": "note", "elements": [{"tag": "plain_text", "content": f"corr_id: {corr_id}"}]})
            send_message(chat_id, json.dumps(card), msg_type="interactive", use_card=True, receive_id_type="chat_id")
        except Exception as e:
            print(f"[Nexus] 推送失败: {e}")


# ── Nexus: 卡片交互回调（用户点击按钮） ──
def _on_nexus_card_action(data):
    """处理飞书卡片按钮点击 → 发布到 bbs/goal_nexus/response
    
    Args:
        data: P2CardActionTrigger 事件对象
    Returns:
        P2CardActionTriggerResponse 或 None
    """
    global _bbs_push_client
    try:
        action = getattr(data.event, 'action', None) if hasattr(data, 'event') else None
        if not action:
            action = data.get('action') if isinstance(data, dict) else None
        if not action:
            print("[NexusCard] 无法获取 action 数据")
            return None
        
        # action.value 应包含 corr_id 和 choice
        value = getattr(action, 'value', None) or (action.get('value') if isinstance(action, dict) else None)
        if not value:
            print("[NexusCard] action 中无 value 字段")
            return None
        
        corr_id = value.get('corr_id', '')
        choice = value.get('choice', '')
        if not corr_id or not choice:
            print(f"[NexusCard] value 缺少 corr_id/choice: {value}")
            return None
        
        # 通过 BBS 发布响应
        payload = {
            "v": 1,
            "action": "response",
            "corr_id": corr_id,
            "choice": choice,
        }
        if _bbs_push_client:
            _bbs_push_client.publish(
                "bbs/goal_nexus/response",
                json.dumps(payload, ensure_ascii=False),
                qos=1
            )
            print(f"[NexusCard] 已发送 corr_id={corr_id}, choice={choice}")
        else:
            print(f"[NexusCard] BBS 客户端未就绪，无法发送响应")
        
        # 返回响应（Toast 提示）
        resp = lark.CardActionTriggerResponse()
        resp.toast = lark.CallBackToast()
        resp.toast.type = "success"
        resp.toast.content = f"已收到你的选择: {choice}"
        return resp
    except Exception as e:
        print(f"[NexusCard] 处理异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def _query_db_output(task_id):
    """从MariaDB查任务output（绕过wait_task时序）"""
    try:
        import pymysql
        _db_pwd = os.environ.get('DB_PASSWORD', 'mariadb')
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password=_db_pwd,
                               database='mqtt_bbs', connect_timeout=3, autocommit=True)
        cur = conn.cursor()
        cur.execute("SELECT payload FROM retained_messages WHERE topic=%s",
                    (f"board/task/{task_id}/output",))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except Exception:
        return []


def create_client():
    return lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).log_level(lark.LogLevel.INFO).build()


def _card_raw(elements):
    return json.dumps({
        "schema": "2.0",
        "config": {"streaming_mode": False, "width_mode": "fill"},
        "body": {"elements": elements},
    }, ensure_ascii=False)


def _card(text):
    return _card_raw([{"tag": "markdown", "content": text}])


def _send_raw(receive_id, payload, msg_type, rtype):
    try:
        body = CreateMessageRequest.builder().receive_id_type(rtype).request_body(
            CreateMessageRequestBody.builder().receive_id(receive_id).msg_type(msg_type).content(payload).build()
        ).build()
        r = client.im.v1.message.create(body)
        if r.success():
            return r.data.message_id if r.data else None
        print(f"发送失败: {r.code}, {r.msg}")
    except Exception as e:
        print(f"[ERROR] _send_raw 网络异常: {e}")
    return None


def _patch_card(message_id, card_json):
    return _patch_card_result(message_id, card_json)[0]


def _patch_card_result(message_id, card_json):
    try:
        body = PatchMessageRequest.builder().message_id(message_id).request_body(
            PatchMessageRequestBody.builder().content(card_json).build()
        ).build()
        r = client.im.v1.message.patch(body)
        if not r.success():
            print(f"[ERROR] patch_card 失败: {r.code}, {r.msg}")
        msg = f"{getattr(r, 'code', '')} {getattr(r, 'msg', '')}".lower()
        return r.success(), ("230099" in msg or "11310" in msg or "element exceeds the limit" in msg)
    except Exception as e:
        print(f"[ERROR] _patch_card 网络异常: {e}")
        return False, False


def send_message(receive_id, content, msg_type="text", use_card=False, receive_id_type="open_id"):
    if use_card:
        return _send_raw(receive_id, _card(content), "interactive", receive_id_type)
    if msg_type == "text":
        return _send_raw(receive_id, json.dumps({"text": content}, ensure_ascii=False), "text", receive_id_type)
    return _send_raw(receive_id, content, msg_type, receive_id_type)


def update_message(message_id, content):
    return _patch_card(message_id, _card(content))


def _upload_image_sync(file_path):
    try:
        with open(file_path, "rb") as f:
            request = CreateImageRequest.builder().request_body(
                CreateImageRequestBody.builder().image_type("message").image(f).build()
            ).build()
            response = client.im.v1.image.create(request)
            if response.success():
                return response.data.image_key
            print(f"[ERROR] upload image failed: {response.code}, {response.msg}")
    except Exception as e:
        print(f"[ERROR] upload image failed {file_path}: {e}")
    return None


def _upload_file_sync(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    file_type = _FILE_TYPE_MAP.get(ext, "stream")
    file_name = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            request = CreateFileRequest.builder().request_body(
                CreateFileRequestBody.builder().file_type(file_type).file_name(file_name).file(f).build()
            ).build()
            response = client.im.v1.file.create(request)
            if response.success():
                return response.data.file_key
            print(f"[ERROR] upload file failed: {response.code}, {response.msg}")
    except Exception as e:
        print(f"[ERROR] upload file failed {file_path}: {e}")
    return None


def _download_image_sync(message_id, image_key):
    try:
        request = GetMessageResourceRequest.builder().message_id(message_id).file_key(image_key).type("image").build()
        response = client.im.v1.message_resource.get(request)
        if response.success():
            data = response.file.read() if hasattr(response.file, "read") else response.file
            return data, response.file_name
        print(f"[ERROR] download image failed: {response.code}, {response.msg}")
    except Exception as e:
        print(f"[ERROR] download image failed {image_key}: {e}")
    return None, None


def _download_file_sync(message_id, file_key, resource_type="file"):
    if resource_type == "audio":
        resource_type = "file"
    try:
        request = GetMessageResourceRequest.builder().message_id(message_id).file_key(file_key).type(resource_type).build()
        response = client.im.v1.message_resource.get(request)
        if response.success():
            data = response.file.read() if hasattr(response.file, "read") else response.file
            return data, response.file_name
        print(f"[ERROR] download {resource_type} failed: {response.code}, {response.msg}")
    except Exception as e:
        print(f"[ERROR] download {resource_type} failed {file_key}: {e}")
    return None, None


def _download_and_save_media(msg_type, content_json, message_id):
    data, filename = None, None
    if msg_type == "image":
        image_key = content_json.get("image_key")
        if image_key and message_id:
            data, filename = _download_image_sync(message_id, image_key)
            if not filename:
                filename = f"{image_key[:16]}.jpg"
    elif msg_type in ("audio", "file", "media"):
        file_key = content_json.get("file_key")
        if file_key and message_id:
            data, filename = _download_file_sync(message_id, file_key, msg_type)
            if not filename:
                filename = file_key[:16]
            if msg_type == "audio" and filename and not filename.endswith(".opus"):
                filename = f"{filename}.opus"
    if data and filename:
        file_path = os.path.join(MEDIA_DIR, os.path.basename(filename))
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path, filename
    return None, None


def _describe_media(msg_type, file_path, filename):
    if msg_type == "image":
        return f"[image: {filename}]\n[Image: source: {file_path}]"
    if msg_type == "audio":
        return f"[audio: {filename}]\n[File: source: {file_path}]"
    if msg_type in ("file", "media"):
        return f"[{msg_type}: {filename}]\n[File: source: {file_path}]"
    return f"[{msg_type}]\n[File: source: {file_path}]"


def _send_local_file(receive_id, file_path, receive_id_type="open_id"):
    if not os.path.isfile(file_path):
        send_message(receive_id, f"⚠️ 文件不存在: {file_path}", receive_id_type=receive_id_type)
        return False
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _IMAGE_EXTS:
        image_key = _upload_image_sync(file_path)
        if image_key:
            send_message(receive_id, json.dumps({"image_key": image_key}, ensure_ascii=False), msg_type="image", receive_id_type=receive_id_type)
            return True
    else:
        file_key = _upload_file_sync(file_path)
        if file_key:
            msg_type = "media" if ext in _AUDIO_EXTS or ext in _VIDEO_EXTS else "file"
            send_message(receive_id, json.dumps({"file_key": file_key}, ensure_ascii=False), msg_type=msg_type, receive_id_type=receive_id_type)
            return True
    send_message(receive_id, f"⚠️ 文件发送失败: {os.path.basename(file_path)}", receive_id_type=receive_id_type)
    return False


def _send_generated_files(receive_id, raw_text, receive_id_type="open_id"):
    for file_path in _extract_files(raw_text):
        _send_local_file(receive_id, file_path, receive_id_type)


def _build_user_message(message):
    msg_type = message.message_type
    message_id = message.message_id
    content_json = _parse_json(message.content)
    parts, image_paths = [], []
    if msg_type == "text":
        text = str(content_json.get("text", "") or "").strip()
        if text:
            parts.append(text)
    elif msg_type == "post":
        text, image_keys = _extract_post_content(content_json)
        if text:
            parts.append(text)
        for image_key in image_keys:
            file_path, filename = _download_and_save_media("image", {"image_key": image_key}, message_id)
            if file_path and filename:
                parts.append(_describe_media("image", file_path, filename))
                image_paths.append(file_path)
            else:
                parts.append("[image: download failed]")
    elif msg_type in ("image", "audio", "file", "media"):
        file_path, filename = _download_and_save_media(msg_type, content_json, message_id)
        if file_path and filename:
            parts.append(_describe_media(msg_type, file_path, filename))
            if msg_type == "image":
                image_paths.append(file_path)
        else:
            parts.append(f"[{msg_type}: download failed]")
    elif msg_type in ("share_chat", "share_user", "interactive", "share_calendar_event", "system", "merge_forward"):
        parts.append(_extract_share_card_content(content_json, msg_type))
    else:
        parts.append(_MSG_TYPE_MAP.get(msg_type, f"[{msg_type}]"))
    return "\n".join([p for p in parts if p]).strip(), image_paths


def _fmt_tool_call(tc):
    name = tc.get('tool_name', '?')
    args = {k: v for k, v in (tc.get('args') or {}).items() if not k.startswith('_')}
    return f"- `{name}`({json.dumps(args, ensure_ascii=False)[:200]})"


def _build_step_detail(resp, tool_calls):
    """从 LLM response + tool_calls 组装单步展开详情（纯函数）。"""
    parts = []
    thinking = (getattr(resp, 'thinking', '') or '').strip() if resp else ''
    if thinking:
        parts.append(f"### 💭 Thinking\n{thinking}")
    if tool_calls:
        parts.append("### 🛠 Tool Calls\n" + "\n".join(_fmt_tool_call(tc) for tc in tool_calls))
    content = _display_text((getattr(resp, 'content', '') or '')).strip() if resp else ''
    if content and content != '...':
        parts.append(f"### 📝 Output\n{content}")
    return "\n\n".join(parts)


class _TaskCard:
    """飞书任务卡片：单卡片持续 patch；每步一个独立折叠面板（header 显示 summary，展开看详情）。"""
    _DETAIL_LIMIT = 8000
    _FINAL_LIMIT = 6000

    def __init__(self, receive_id, rid_type):
        self.rid, self.rtype = receive_id, rid_type
        self.steps = []          # [(summary, detail), ...]
        self.status = "🤔 思考中..."
        self.final = None
        self.msg_id = None
        self.page_no = 1
        self.turn_no = 0
        self.turn_base = 1
        self.note = None

    def _step_panel(self, idx, summary, detail):
        detail = detail or "_(无输出)_"
        if len(detail) > self._DETAIL_LIMIT:
            detail = detail[:self._DETAIL_LIMIT] + f"\n\n…(已截断,共 {len(detail)} 字符)"
        return {
            "tag": "collapsible_panel", "expanded": False,
            "header": {"title": {"tag": "plain_text", "content": f"Turn {idx} · {summary}"}},
            "elements": [{"tag": "markdown", "content": detail}],
        }

    def _build(self):
        # 用最新 step summary 或 final output 做头部，而不是状态
        topic = self.final[:60] if self.final else (
            self.steps[-1][0][:60] if self.steps else self.status
        )
        header = f"**{topic}**"
        if self.page_no > 1:
            header += f"\n\n📄 工作卡片 {self.page_no}"
        els = [{"tag": "markdown", "content": header}]
        if self.note:
            els.append({"tag": "markdown", "content": self.note})
        for i, (s, d) in enumerate(self.steps, self.turn_base):
            els.append(self._step_panel(i, s, d))
        if self.final:
            els += [{"tag": "hr"}, {"tag": "markdown", "content": self.final}]
        return _card_raw(els)

    def _push(self):
        card = self._build()
        if self.msg_id:
            return _patch_card_result(self.msg_id, card)
        else:
            self.msg_id = _send_raw(self.rid, card, "interactive", self.rtype)
            return bool(self.msg_id), False

    def _rollover(self):
        self.page_no += 1
        self.msg_id = None
        self.final = None
        self.note = "⚠️ 上一张工作卡片达到飞书限制，本页继续展示后续进展。"

    # ── 公开接口 ──

    def start(self):
        self._push()

    def step(self, summary, detail=""):
        self.turn_no += 1
        step = (summary, detail)
        self.steps.append(step)
        self.status = f"⏳ 工作中 · Turn {self.turn_no}"
        ok, limit = self._push()
        if limit:
            self.steps.pop()
            self._rollover()
            self.turn_base = self.turn_no
            self.steps = [step]
            self._push()

    def done(self, text):
        self.status = "✅ 已完成"
        self.final = (text or "_(无文本输出)_")[:self._FINAL_LIMIT]
        ok, limit = self._push()
        if limit:
            self._rollover()
            self.steps = []
            self.turn_base = self.turn_no + 1
            self.final = (text or "_(无文本输出)_")[:self._FINAL_LIMIT]
            self._push()

    def fail(self, msg):
        self.status = f"❌ {msg}"
        self._push()


def _make_task_hook(card, done_event, on_final):
    """飞书任务 hook：每轮 patch 卡片状态；结束触发 on_final(raw) 处理附件。"""
    def hook(ctx):
        try:
            if ctx.get('exit_reason'):
                resp = ctx.get('response')
                raw = resp.content if hasattr(resp, 'content') else str(resp)
                card.done(_display_text(raw))
                on_final(raw)
                done_event.set()
            elif ctx.get('summary'):
                detail = _build_step_detail(ctx.get('response'), ctx.get('tool_calls') or [])
                card.step(ctx['summary'], detail)
        except Exception as e:
            print(f"[fs hook] error: {e}")
    return hook


_dedup_msg_ids = {}  # message_id -> timestamp, 5秒去重

def _is_duplicate_msg(message_id: str) -> bool:
    now = time.time()
    # 清理过期记录
    stale = [k for k, v in _dedup_msg_ids.items() if now - v > 5]
    for k in stale:
        del _dedup_msg_ids[k]
    if message_id in _dedup_msg_ids:
        return True
    _dedup_msg_ids[message_id] = now
    return False

def handle_message(data):
    event, message, sender = data.event, data.event.message, data.event.sender
    open_id = sender.sender_id.open_id
    chat_id = message.chat_id
    # 消息去重（飞书长连接重连可能重放事件）
    if hasattr(message, 'message_id') and _is_duplicate_msg(message.message_id):
        print(f"[去重] 忽略重复消息: {message.message_id}")
        return
    if not PUBLIC_ACCESS and open_id not in ALLOWED_USERS:
        print(f"未授权用户: {open_id}")
        return
    user_input, image_paths = _build_user_message(message)
    if not user_input:
        if chat_id:
            send_message(chat_id, f"⚠️ 暂不支持处理此类飞书消息：{message.message_type}", receive_id_type="chat_id")
        else:
            send_message(open_id, f"⚠️ 暂不支持处理此类飞书消息：{message.message_type}")
        return
    print(f"收到消息 [{open_id}] ({message.message_type}, {len(image_paths)} images): {user_input[:200]}")
    # 群聊消息自动提取待办
    if chat_id and message.message_type == "text":
        extracted = _todo_mgr.extract_todos(user_input)
        for todo_text in extracted:
            _todo_mgr.add(todo_text, open_id=open_id, source="群聊", chat_id=chat_id)
            print(f"  📋 已提取待办: {todo_text}")
    if message.message_type == "text" and user_input.startswith("/"):
        return handle_command(open_id, user_input, chat_id)

    def run_agent():
        user_tasks[open_id] = {"running": True}
        receive_id = chat_id or open_id
        rid_type = "chat_id" if chat_id else "open_id"
        done_event = threading.Event()
        hook_key = f"fs_{open_id}"
        card = _TaskCard(receive_id, rid_type)
        card.start()
        on_final = lambda raw: _send_generated_files(receive_id, raw, receive_id_type=rid_type)
        if not hasattr(agent, '_turn_end_hooks'): agent._turn_end_hooks = {}
        agent._turn_end_hooks[hook_key] = _make_task_hook(card, done_event, on_final)
        try:
            agent.put_task(user_input, source="feishu", images=image_paths)
            start = time.time()
            while not done_event.wait(timeout=3):
                if not user_tasks.get(open_id, {}).get("running", True):
                    agent.abort()
                    card.fail("已停止")
                    break
                if time.time() - start > AGENT_TIMEOUT_SEC:
                    agent.abort()
                    card.fail("任务超时")
                    break
        except Exception as e:
            traceback.print_exc()
            card.fail(f"错误: {e}")
        finally:
            agent._turn_end_hooks.pop(hook_key, None)
            user_tasks.pop(open_id, None)

    threading.Thread(target=run_agent, daemon=True).start()


CMD_HELP_TEXT = """命令列表:
/stop - 停止当前任务
/status - 查看状态
/llm - 查看当前模型列表
/llm [n] - 切换到第 n 个模型
/restore - 恢复上次对话历史
/continue - 列出可恢复会话
/continue [n] - 恢复第 n 个会话
/new - 开启新对话并清空当前上下文
/remind - 定时提醒（add/list/del）
/inspired - 查看灵感板
/task <type> <json> - 发布MQTT任务
/todo - 待办管理（add/done/del）
/hitl - 审批管理（list/approve/reject）
/dream - Agent梦境（记忆回放+跨域联想）
/help - 显示帮助"""


def _cmd_stop(agent, user_tasks, open_id, chat_id):
    """处理 /stop 命令"""
    if open_id in user_tasks:
        user_tasks[open_id]["running"] = False
    agent.abort()
    if chat_id:
        send_message(chat_id, "正在停止...", receive_id_type="chat_id")
    else:
        send_message(open_id, "正在停止...")


def handle_command(open_id, cmd, chat_id=None):
    def _send_cmd_response(content):
        if chat_id:
            send_message(chat_id, content, receive_id_type="chat_id")
        else:
            send_message(open_id, content)
    parts = (cmd or "").split()
    op = (parts[0] if parts else "").lower()
    if op == "/stop":
        _cmd_stop(agent, user_tasks, open_id, chat_id)
        if open_id in user_tasks:
            user_tasks[open_id]["running"] = False
        agent.abort()
        _send_cmd_response("正在停止...")
    elif op == "/new":
        _send_cmd_response(reset_conversation(agent))
    elif op == "/help":
        _send_cmd_response(CMD_HELP_TEXT)
    elif op == "/status":
        llm = agent.get_llm_name() if agent.llmclient else "未配置"
        _send_cmd_response(f"状态: {'运行中' if agent.is_running else '空闲'}\nLLM: [{agent.llm_no}] {llm}")
    elif op == "/llm":
        if not agent.llmclient:
            return _send_cmd_response("当前没有可用的 LLM 配置")
        if len(parts) > 1:
            try:
                agent.next_llm(int(parts[1]))
                return _send_cmd_response(f"已切换到 [{agent.llm_no}] {agent.get_llm_name()}")
            except Exception:
                return _send_cmd_response(f"用法: /llm <0-{len(agent.list_llms()) - 1}>")
        lines = [f"{'->' if cur else '  '} [{i}] {name}" for i, name, cur in agent.list_llms()]
        _send_cmd_response("LLMs:\n" + "\n".join(lines))
    elif op == "/restore":
        try:
            restored_info, err = format_restore()
            if err:
                return _send_cmd_response(err.replace("", ""))
            restored, fname, count = restored_info
            agent.history.extend(restored)
            agent.abort()
            _send_cmd_response(f"已恢复 {count} 轮对话\n来源: {fname}\n(仅恢复上下文，请输入新问题继续)")
        except Exception as e:
            _send_cmd_response(f"恢复失败: {e}")
    elif op == "/continue" or cmd.startswith("/continue"):
        _send_cmd_response(handle_continue_frontend(agent, cmd))
    elif op == "/remind":
        sub = parts[1] if len(parts) > 1 else ""
        if sub == "add" and len(parts) >= 4:
            raw = " ".join(parts[2:])
            r = _reminder.add(raw, open_id=open_id)
            if r:
                rtype = "每日" if r["type"] == "daily" else "一次性"
                _send_cmd_response(f"\u2705 已添加{rtype}提醒: [{r['id']}] {r['text']} ({r['hour']:02d}:{r['minute']:02d})")
            else:
                _send_cmd_response("\u274c 格式错误，示例:\n/remind add 每天9:00 喝杯水\n/remind add 14:30 开会提醒")
        elif sub == "list":
            lst = _reminder.list(open_id=open_id)
            _send_cmd_response(format_reminder_list(lst))
        elif sub == "del" and len(parts) >= 3:
            try:
                rid = int(parts[2])
                if _reminder.remove(rid, open_id=open_id):
                    _send_cmd_response(f"\u2705 已删除提醒 [{rid}]")
                else:
                    _send_cmd_response(f"\u274c 提醒 [{rid}] 不存在或不属于你")
            except ValueError:
                _send_cmd_response("用法: /remind del <id>")
        else:
            _send_cmd_response(REMIND_HELP)
    elif op == "/inspired":
        _board = _get_inspiration_board()
        if len(parts) >= 3 and parts[1] == "add":
            _title = " ".join(parts[2:])
            _idea_id = _board.add_idea(_title.strip())
            _send_cmd_response(f"已添加灵感 #{_idea_id}: {_title.strip()}" if _idea_id else "添加灵感失败")
        else:
            _ideas = _board.load_all()
            if not _ideas:
                _send_cmd_response("灵感板为空")
            else:
                _lines = [f"灵感板 ({len(_ideas)}/20 条活跃)"]
                for _idea in _ideas:
                    _icon = {"new": "", "thinking": "", "in_progress": "", "implemented": ""}.get(_idea["status"], "")
                    _src = "" if _idea.get("source") == "user" else ""
                    _tag = f" [{', '.join(_idea.get('tags', []))}]" if _idea.get("tags") else ""
                    _lines.append(f"{_icon} #{_idea['id']} {_src} {_idea['title']}{_tag}")
                    if _idea.get("detail"):
                        _lines.append(f"   {_idea['detail'][:80]}")
                _send_cmd_response("\n".join(_lines)[:1500])
    elif op == "/task":
        board = _get_board()
        if not board:
            _send_cmd_response("MQTT BBS 未连接")
        elif len(parts) < 3:
            _send_cmd_response("用法: /task <type> <input_json>")
        else:
            try:
                task_type = parts[1]
                task_input = json.loads(" ".join(parts[2:]))
                tid = board.post_task(task_type, task_input)
                _send_cmd_response(f"任务已发布:\n  ID: {tid}\n  类型: {task_type}")
                threading.Thread(target=_wait_and_notify, args=(tid, chat_id, open_id), daemon=True).start()
            except Exception as e:
                _send_cmd_response(f"任务发布失败: {e}")
    elif op == "/hitl":
        global _todo_mgr
        if len(parts) >= 3 and parts[1] == "approve":
            result = approve(parts[2])
            _send_cmd_response(f"✅ 审批通过: {parts[2]}" if result else f"❌ 审批失败: {parts[2]}")
        elif len(parts) >= 3 and parts[1] == "reject":
            result = reject(parts[2])
            _send_cmd_response(f"✅ 已拒绝: {parts[2]}" if result else f"❌ 操作失败: {parts[2]}")
        else:
            pending = get_pending_list()
            if not pending:
                _send_cmd_response("📋 无待审批项")
            else:
                lines = [f"🤖 待审批 ({len(pending)}项):"]
                for p in pending:
                    lines.append(f"  #{p['id']} [{p['task_type']}] conf={p['confidence']:.2f} {p['reason'][:40]}")
                _send_cmd_response("\n".join(lines))
    elif op == "/todo":
        global _todo_mgr
        if len(parts) >= 3 and parts[1] == "add":
            content = " ".join(parts[2:])
            t = _todo_mgr.add(content, open_id=open_id)
            _send_cmd_response(f"✅ 已添加待办 #{t['id']}: {content}")
        elif len(parts) >= 3 and parts[1] == "done":
            try:
                tid_d = int(parts[2])
                if _todo_mgr.done(tid_d):
                    _send_cmd_response(f"✅ 待办 #{tid_d} 已完成")
                else:
                    _send_cmd_response(f"❌ 待办 #{tid_d} 不存在")
            except ValueError:
                _send_cmd_response("用法: /todo done <id>")
        elif len(parts) >= 3 and parts[1] == "del":
            try:
                tid_d = int(parts[2])
                if _todo_mgr.remove(tid_d):
                    _send_cmd_response(f"🗑️ 已删除待办 #{tid_d}")
                else:
                    _send_cmd_response(f"❌ 待办 #{tid_d} 不存在")
            except ValueError:
                _send_cmd_response("用法: /todo del <id>")
        else:
            _send_cmd_response(_todo_mgr.format_list())
    elif op == "/dream":
        from tools.dream_engine import replay_memories, associate_random
        import pymysql as _pm
        _db_pwd = os.environ.get('DB_PASSWORD', 'mariadb')
        _conn = _pm.connect(host='127.0.0.1', port=3306, user='root', password=_db_pwd, database='mqtt_bbs')
        _cur = _conn.cursor()
        _cur.execute("SELECT COUNT(*) FROM dream_memories")
        _cnt = _cur.fetchone()[0]
        _conn.close()
        _ins = replay_memories(k=3)
        _assocs = associate_random(k=2)
        _ib = _get_inspiration_board()
        _new_ideas = 0
        _lines = [f"💭 Agent Dreaming (dream_memories: {_cnt} 条)"]
        if _ins:
            for _i in _ins:
                _icon = {"conflict": "⚡", "gap": "🔍", "repeat": "🔄", "opportunity": "💡"}.get(_i['type'], "💭")
                _desc = _i['desc'][:80]
                _lines.append(f"{_icon} [{_i['type']}] {_desc}")
                _ib.add_idea(f"[Dream] {_desc}", _desc, tags=["dream", _i['type']], source="agent")
                _new_ideas += 1
        if _assocs:
            for _a in _assocs:
                _title = f"{_a['domain_a'][:20]} × {_a['domain_b'][:20]}"
                _desc = f"score={_a.get('score',0):.2f}: {_a.get('desc','')[:100]}"
                _lines.append(f"🔗 跨域: {_title} ({_a.get('score',0):.2f})")
                _ib.add_idea(f"[Dream] {_title}", _desc, tags=["dream", "associate"], source="agent")
                _new_ideas += 1
        if not _ins and not _assocs:
            _lines.append("  暂无洞察（继续积累对话记忆）")
        if _new_ideas:
            _lines.append("─" * 30)
            _lines.append(f"📌 已写入灵感板 {_new_ideas} 条（/inspired 查看）")
        _send_cmd_response("\n".join(_lines))

        # BBS 广播：将梦境结果广播到 agent-dream board
        if _new_ideas:
            try:
                from Mqtt_bbs_client.board_client import BoardClient as _BC
                with _BC("feishu_bot_dream", board="agent-dream") as _bbs_d:
                    _reg = _bbs_d.register("飞书Bot", timeout=5)
                    if _reg and _reg.get("token"):
                        _bbs_d.post(
                            f"[Dream广播] {_new_ideas} 条新梦境洞察\n"
                            + "\n".join(_lines[-_new_ideas-1:]),
                            _reg["token"], timeout=5
                        )
                        print("  📡 Dream 已广播到 agent-dream board")
            except Exception as _e:
                print(f"  ⚠️ Dream BBS 广播失败: {_e}")
    elif op == "/bbs":
        # 飞书↔BBS 桥接
        board = _get_board()
        if not board:
            _send_cmd_response("❌ MQTT BBS 未连接")
        elif len(parts) < 3:
            _send_cmd_response("用法:\n/bbs post <content> - 发帖到 BBS\n/bbs subscribe - 订阅 BBS 新帖推送到本群\n/bbs unsubscribe - 取消订阅")
        elif parts[1] == "post":
            content = " ".join(parts[2:])
            try:
                from Mqtt_bbs_client.board_client import BoardClient as _BC
                with _BC("feishu_bot_bridge", board="agent-bridge") as _bbs:
                    reg = _bbs.register("飞书Bot", timeout=5)
                    if reg and reg.get("token"):
                        result = _bbs.post(content, reg["token"], timeout=5)
                        if result and "error" not in result:
                            _send_cmd_response(f"✅ 已发帖到 BBS (agent-bridge): {content[:100]}")
                        else:
                            _send_cmd_response(f"❌ 发帖失败: {result}")
                    else:
                        _send_cmd_response("❌ BBS 注册失败")
            except Exception as _e:
                _send_cmd_response(f"❌ BBS 操作失败: {_e}")
        elif parts[1] == "subscribe":
            if chat_id:
                _bbs_push_chats.add(chat_id)
                _send_cmd_response("✅ 已订阅 BBS 新帖推送（新帖将自动推送到此群）")
            else:
                _send_cmd_response("❌ 订阅仅支持群聊")
        elif parts[1] == "unsubscribe":
            if chat_id:
                _bbs_push_chats.discard(chat_id)
                _send_cmd_response("✅ 已取消 BBS 推送订阅")
            else:
                _send_cmd_response("❌ 取消订阅仅支持群聊")
        else:
            _send_cmd_response("未知 BBS 操作，支持: post / subscribe / unsubscribe")
    else:
        _send_cmd_response(f"未知命令: {cmd}")


def _wait_and_notify(tid, chat_id, open_id):
    try:
        import time
        for _ in range(30):
            time.sleep(0.5)
            rows = _query_db_output(tid)
            if rows: break
        if not rows:
            try: result = board.wait_task(tid, timeout=5)
            except: result = None
        else:
            result = json.loads(rows[0][0]) if rows else None
        msg = f"任务完成 ({tid}): {json.dumps(result, ensure_ascii=False)[:300]}" if result else f"任务 {tid} 超时"
        if chat_id: send_message(chat_id, msg, receive_id_type="chat_id")
        else: send_message(open_id, msg)
    except Exception as e:
        err_msg = f"任务 {tid} 异常: {e}"
        if chat_id: send_message(chat_id, err_msg, receive_id_type="chat_id")
        else: send_message(open_id, err_msg)


def main():
    global client
    if not APP_ID or not APP_SECRET:
        print("错误: 请在 mykey.py 或 mykey.json 中配置 fs_app_id 和 fs_app_secret")
        sys.exit(1)
    client = create_client()
    handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(handle_message) \
        .register_p2_card_action_trigger(_on_nexus_card_action) \
        .build()
    # 启动定时提醒检查（每30秒检查一次）
    start_reminder_checker(_reminder, _reminder_send, interval=30)
    # 启动 BBS 桥接推送
    _init_bbs_push()
    print("=" * 50 + "\n飞书 Agent 正在连接...\n" + f"App ID: {APP_ID}\n" + "=" * 50)
    retry_delay = 1
    first_connect = True
    while True:
        try:
            cli = lark.ws.Client(APP_ID, APP_SECRET, event_handler=handler, log_level=lark.LogLevel.INFO)
            if first_connect:
                print("[OK] 飞书 Bot 已就绪（WebSocket 连接建立中...）")
                first_connect = False
            cli.start()
        except Exception as e:
            print(f"[WARN] 飞书长连接断开或启动失败: {e}")
        print(f"[INFO] {retry_delay}s 后重连...")
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 120)
        # 重连时刷新 client
        try:
            client = create_client()
        except Exception:
            pass


if __name__ == "__main__":
    main()
