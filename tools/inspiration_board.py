#!/usr/bin/env python3
"""
灵感沟通交流板 - Inspiration Board

用户与 Agent 之间的灵感协作板。
- 用户：随时推送灵感
- Agent：自主空闲时思考灵感、添加新灵感
- 上限20条活跃，超量自动归档

使用 MQTT BBS 机制进行通知和同步。

用法:
    # 用户添加灵感
    python -c "from inspiration_board import Board; Board.add('用adb自动化手机测试')"

    # Agent 添加灵感（自主行动时用）
    board = Board()
    board.add_idea("实现web端图片批量下载工具")
    board.think(idea_id=1)

    # 查看所有灵感
    python -c "from inspiration_board import Board; Board.list_all()"
"""
import os
import json
import time
import datetime
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# ── 目录 ──────────────────────────────────────────
MODULE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = MODULE_DIR / "memory" / "inspirations"
ACTIVE_FILE = MEMORY_DIR / "active.json"
ARCHIVE_DIR = MEMORY_DIR / "archive"

# ── 常量 ──────────────────────────────────────────
MAX_ACTIVE = 20
STATUS_NEW = "new"
STATUS_THINKING = "thinking"
STATUS_IN_PROGRESS = "in_progress"
STATUS_ARCHIVED = "archived"
STATUS_IMPLEMENTED = "implemented"


# ══════════════════════════════════════════════════
# 核心类
# ══════════════════════════════════════════════════

class Board:
    """灵感板 - 管理灵感的增删改查与归档

    BBS 后端模式 (bbs_backend=True):
        - 灵感存储在 MQTT BBS 的专用 board (默认 agent-inspiration) 中
        - 每个灵感变更 = 一条 BBS 帖子 (JSON content)
        - 任何 Agent 可订阅该 board 实时感知灵感变化
        - 本地 JSON 文件降级为只读缓存
    """

    def __init__(self, bbs_backend=True, bbs_board="agent-inspiration"):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        self.bbs_backend = bbs_backend
        self.bbs_board = bbs_board
        self._bbs = None  # BoardClient instance
        self._bbs_token = None  # cached token
        self._bbs_reg_name = "灵感板"  # 注册名称
        self._subscribers = []  # [(callback, filter_fn)]

    # ── BBS 连接管理 ─────────────────────────────

    def _connect_bbs(self):
        """连接 BBS 并注册，返回 BoardClient 实例"""
        if self._bbs is not None and self._bbs.is_connected:
            return self._bbs
        from mqtt_bbs.board_client import BoardClient
        self._bbs = BoardClient("inspiration_board", board=self.bbs_board)
        self._bbs.connect()
        reg = self._bbs.register(self._bbs_reg_name, timeout=5)
        if reg and reg.get("token"):
            self._bbs_token = reg["token"]
        else:
            logger.warning(f"[Board] BBS 注册失败: {reg}")
        return self._bbs

    def _disconnect_bbs(self):
        if self._bbs:
            try:
                self._bbs.disconnect()
            except Exception:
                pass
            self._bbs = None
            self._bbs_token = None

    def subscribe(self, callback, status_filter=None):
        """
        订阅灵感变更通知。

        参数:
            callback: callable(idea_dict) — 灵感变更时回调
            status_filter: list[str] — 可选，只关注某些状态变更
        """
        self._subscribers.append((callback, status_filter))

    def _notify_subscribers(self, idea: dict):
        """通知所有订阅者"""
        for cb, status_filter in self._subscribers:
            if status_filter and idea.get("status") not in status_filter:
                continue
            try:
                cb(idea)
            except Exception as e:
                logger.warning(f"[Board] 订阅者回调异常: {e}")

    def _bbs_post_idea(self, idea: dict) -> bool:
        """将灵感作为 BBS 帖子发布，同时通知本地订阅者"""
        # 通知本地订阅者
        self._notify_subscribers(idea)
        try:
            bbs = self._connect_bbs()
            if not self._bbs_token:
                return False
            content = json.dumps(idea, ensure_ascii=False)
            result = bbs.post(content, self._bbs_token, timeout=5)
            if result and "error" not in result:
                logger.info(f"[Board] 📤 BBS 已存储灵感 #{idea['id']} [{idea['status']}]")
                return True
            logger.warning(f"[Board] BBS 发帖失败: {result}")
            return False
        except Exception as e:
            logger.warning(f"[Board] BBS 发帖异常: {e}")
            return False

    def _bbs_load_all(self) -> List[Dict]:
        """从 BBS 加载所有灵感（按 idea_id 去重取最新版本）"""
        try:
            bbs = self._connect_bbs()
            # 拉取所有帖子 (limit=0 表示尽可能多)
            posts = bbs.query_posts(author=self._bbs_reg_name, limit=200, timeout=10)
            if not posts:
                return []
            # 按 idea_id 去重，保留最新的 (post_id 大的)
            latest = {}
            for p in posts:
                try:
                    idea = json.loads(p["content"]) if isinstance(p["content"], str) else p["content"]
                    idea_id = idea.get("id")
                    if idea_id is not None:
                        # post_id 越大越新
                        existing = latest.get(idea_id)
                        if existing is None or p.get("id", 0) > existing.get("_post_id", 0):
                            idea["_post_id"] = p.get("id", 0)
                            latest[idea_id] = idea
                except (json.JSONDecodeError, KeyError):
                    continue
            result = list(latest.values())
            # 按 id 排序
            result.sort(key=lambda x: x.get("id", 0))
            logger.info(f"[Board] 📖 BBS 加载 {len(result)} 条灵感")
            return result
        except Exception as e:
            logger.warning(f"[Board] BBS 加载失败: {e}，降级到本地文件")
            return None  # 返回 None 表示降级

    # ── 读取 ─────────────────────────────────────

    def load_all(self) -> List[Dict]:
        """加载所有活跃灵感"""
        # BBS 模式：从 BBS 加载，失败降级到文件
        if self.bbs_backend:
            bbs_ideas = self._bbs_load_all()
            if bbs_ideas is not None:
                return bbs_ideas
            # BBS 失败，降级到文件
            logger.info("[Board] 降级到本地文件")
        # 文件模式
        if not ACTIVE_FILE.exists():
            return []
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_all(self, ideas: List[Dict]):
        """保存活跃灵感列表"""
        if self.bbs_backend:
            # BBS 模式下，save_all 只做本地缓存，不覆盖 BBS 数据
            self._cache_to_file(ideas)
            return
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(ideas, f, ensure_ascii=False, indent=2)

    def _cache_to_file(self, ideas: List[Dict]):
        """将灵感列表缓存到本地 JSON 文件（BBS 模式的辅助缓存）"""
        try:
            with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
                json.dump(ideas, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── 查找 ─────────────────────────────────────

    def find_by_id(self, idea_id: int) -> Optional[Dict]:
        ideas = self.load_all()
        for idea in ideas:
            if idea.get("id") == idea_id:
                return idea
        return None

    def find_by_status(self, status: str) -> List[Dict]:
        ideas = self.load_all()
        return [i for i in ideas if i.get("status") == status]

    # ── 添加 ─────────────────────────────────────

    def add_idea(self, title: str, detail: str = "", tags: list = None,
                 source: str = "user") -> int:
        """
        添加新灵感。

        参数:
            title: 灵感标题
            detail: 详细描述
            tags: 标签列表，如 ["ui", "automation"]
            source: "user" | "agent"

        返回: 灵感ID
        """
        ideas = self.load_all()
        next_id = max([i.get("id", 0) for i in ideas], default=0) + 1

        idea = {
            "id": next_id,
            "title": title,
            "detail": detail,
            "tags": tags or [],
            "source": source,
            "status": STATUS_NEW,
            "agent_notes": "",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        ideas.append(idea)

        # 超量归档
        if len(ideas) > MAX_ACTIVE:
            self._archive_overflow(ideas)

        self.save_all(ideas)

        # BBS 模式：直接发帖到 BBS
        if self.bbs_backend:
            self._bbs_post_idea(idea)
        else:
            # 传统模式：MQTT 通知
            self._notify_mqtt("NEW", idea)

        logger.info(f"[Board] ✨ 新灵感 #{next_id}: {title}")
        return next_id

    def _archive_overflow(self, ideas: List[Dict]):
        """超出20条时，归档最早的已完成/已归档灵感"""
        # 先归档已完成的
        done = [i for i in ideas if i["status"] in (STATUS_IMPLEMENTED, STATUS_ARCHIVED)]
        if done:
            # 归档最早的几条
            to_archive = sorted(done, key=lambda x: x["id"])[:len(ideas) - MAX_ACTIVE]
            for idea in to_archive:
                ideas.remove(idea)
            self._archive_items(to_archive)
            logger.info(f"[Board] 📦 归档 {len(to_archive)} 条已完成灵感")
            return

        # 如果没已完成的，归档最早的（按 id 排序）
        sorted_ideas = sorted(ideas, key=lambda x: x["id"])
        to_archive = sorted_ideas[:len(ideas) - MAX_ACTIVE]
        for idea in to_archive:
            ideas.remove(idea)
        self._archive_items(to_archive)
        logger.info(f"[Board] 📦 强制归档 {len(to_archive)} 条最早灵感")

    def _archive_items(self, items: List[Dict]):
        """写入归档文件"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        archive_file = ARCHIVE_DIR / f"archive_{today}.json"

        existing = []
        if archive_file.exists():
            with open(archive_file, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        # 标记为 archived
        for item in items:
            item["status"] = STATUS_ARCHIVED
            item["archived_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        existing.extend(items)

        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logger.info(f"[Board] 📦 归档 {len(items)} 条到 {archive_file.name}")

    # ── 思考与更新 ─────────────────────────────

    def think(self, idea_id: int, notes: str = ""):
        """Agent 对灵感进行思考，更新状态为 thinking"""
        ideas = self.load_all()
        for idea in ideas:
            if idea["id"] == idea_id:
                idea["status"] = STATUS_THINKING
                if notes:
                    idea["agent_notes"] = (idea.get("agent_notes", "")
                                           + f"\n[Agent思考 {datetime.datetime.now().strftime('%m-%d %H:%M')}]: {notes}")
                idea["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                self.save_all(ideas)
                # BBS 模式：同步状态变更到 BBS
                if self.bbs_backend:
                    self._bbs_post_idea(idea)
                else:
                    self._notify_mqtt("THINKING", idea)
                logger.info(f"[Board] 🤔 思考灵感 #{idea_id}")
                return True
        logger.warning(f"[Board] 未找到灵感 #{idea_id}")
        return False

    def implement(self, idea_id: int, notes: str = ""):
        """标记灵感为已实现"""
        ideas = self.load_all()
        for idea in ideas:
            if idea["id"] == idea_id:
                idea["status"] = STATUS_IMPLEMENTED
                if notes:
                    idea["agent_notes"] = (idea.get("agent_notes", "")
                                           + f"\n[实现 {datetime.datetime.now().strftime('%m-%d %H:%M')}]: {notes}")
                idea["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                self.save_all(ideas)
                # BBS 模式：同步状态变更到 BBS
                if self.bbs_backend:
                    self._bbs_post_idea(idea)
                else:
                    self._notify_mqtt("IMPLEMENTED", idea)
                logger.info(f"[Board] ✅ 实现灵感 #{idea_id}")
                return True
        return False

    def archive(self, idea_id: int, notes: str = ""):
        """手动归档某条灵感"""
        ideas = self.load_all()
        for idea in ideas:
            if idea["id"] == idea_id:
                self._archive_items([idea])
                ideas.remove(idea)
                self.save_all(ideas)
                # BBS 模式：归档也同步（让其他Agent感知）
                if self.bbs_backend:
                    idea["status"] = STATUS_ARCHIVED
                    self._bbs_post_idea(idea)
                logger.info(f"[Board] 📦 手动归档 #{idea_id}")
                return True
        return False

    # ── 列出 ─────────────────────────────────────

    def list_active(self, show_all: bool = False) -> List[Dict]:
        """列出活跃灵感"""
        return self.load_all()

    def list_archived(self, days: int = 7) -> List[Dict]:
        """列出近期归档"""
        items = []
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        for f in sorted(ARCHIVE_DIR.glob("archive_*.json"), reverse=True):
            # 检查文件名日期
            try:
                date_str = f.stem.split("_")[1]
                file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
                if file_date < cutoff:
                    continue
            except:
                pass
            with open(f, "r", encoding="utf-8") as fh:
                try:
                    items.extend(json.load(fh))
                except:
                    pass
        return items

    # ── MQTT BBS 通知 ────────────────────────────

    def _notify_mqtt(self, event: str, idea: dict):
        """通过 MQTT BBS 发布灵感通知（默认必选，失败告警）"""
        import sys as _sys
        _root = str(MODULE_DIR)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)

        # 方式一：BoardClient BBS 协议（主路径）
        bbs_ok = False
        try:
            from mqtt_bbs.board_client import BoardClient
            with BoardClient("inspiration_board", board="agent-bbs-test") as bbs:
                reg = bbs.register("灵感板", timeout=5)
                if reg.get("token"):
                    content = (
                        f"[灵感板·{event}] #{idea['id']} {idea['title']}\n"
                        f"状态: {idea['status']} | 来源: {idea['source']}"
                    )
                    post = bbs.post(content, reg["token"], timeout=5)
                    if post and "error" not in post:
                        bbs_ok = True
                        logger.info(f"[Board] 📤 BBS 已发帖 #{post.get('id')} [{event}] #{idea['id']}")
                    else:
                        logger.warning(f"[Board] BBS 发帖失败: {post}")
                else:
                    logger.warning(f"[Board] BBS 注册失败: {reg}")
        except Exception as e:
            logger.warning(f"[Board] BBS 通知异常: {e}")

        # 方式二：原始 MQTT 直发（降级/兼容，保留 open 主题）
        try:
            import paho.mqtt.client as mqtt
            from mqtt_bbs.config import BROKER_HOST, BROKER_PORT

            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.connect(BROKER_HOST, BROKER_PORT, 5)

            topic = f"agent/board/inspiration/{idea['id']}/signal"
            payload = json.dumps({
                "event": event,
                "idea_id": idea["id"],
                "title": idea["title"],
                "status": idea["status"],
                "source": idea["source"],
                "time": idea["created_at"],
            }, ensure_ascii=False)
            client.publish(topic, payload, qos=1, retain=True)

            # 同时发布到 open 主题（汇总列表）
            open_topic = "agent/board/inspiration/open"
            self._publish_open_list(client, open_topic)

            client.disconnect()
            logger.info(f"[Board] 📡 MQTT 直发完成 [{event}] #{idea['id']}")
        except Exception as e:
            logger.warning(f"[Board] MQTT 直发失败: {e}")

        if not bbs_ok:
            logger.warning(f"[Board] ⚠️ BBS 未送达（MQTT 直发已作为降级）")

    def _publish_open_list(self, client, topic: str):
        """发布活跃灵感汇总到 open 主题"""
        ideas = self.load_all()
        summary = [{"id": i["id"], "title": i["title"], "status": i["status"],
                     "source": i["source"], "tags": i["tags"]}
                   for i in ideas]
        client.publish(topic, json.dumps(summary, ensure_ascii=False), qos=1, retain=True)

    # ── Agent 自动分析 ──────────────────────────

    def get_suggestions_for_agent(self) -> list:
        """Agent 自主行动时调用：返回可思考的灵感列表"""
        ideas = self.load_all()
        # 按优先级排序：new > thinking > in_progress
        priority = {STATUS_NEW: 0, STATUS_THINKING: 1, STATUS_IN_PROGRESS: 2}
        sorted_ideas = sorted(ideas, key=lambda x: priority.get(x["status"], 99))
        # 返回 top 5 需要关注的
        return [{
            "id": i["id"],
            "title": i["title"],
            "status": i["status"],
            "tags": i.get("tags", []),
            "source": i.get("source", ""),
        } for i in sorted_ideas[:5]]

    def add_agent_idea(self, title: str, detail: str = "", tags: list = None):
        """Agent 自主添加灵感"""
        return self.add_idea(title, detail, tags or [], source="agent")


# ══════════════════════════════════════════════════
# 快捷函数（供命令行使用）
# ══════════════════════════════════════════════════

def add(title: str, detail: str = "", tags: list = None):
    return Board().add_idea(title, detail, tags)

def list_all():
    board = Board()
    ideas = board.load_all()
    if not ideas:
        print("📋 灵感板为空")
        return

    print(f"\n{'='*60}")
    print(f"  💡 灵感板 ({len(ideas)}/{MAX_ACTIVE} 条活跃)")
    print(f"{'='*60}")
    for idea in ideas:
        status_icon = {
            STATUS_NEW: "🆕",
            STATUS_THINKING: "🤔",
            STATUS_IN_PROGRESS: "🔨",
            STATUS_IMPLEMENTED: "✅",
            STATUS_ARCHIVED: "📦",
        }.get(idea["status"], "💡")
        tags_str = f" [{', '.join(idea['tags'])}]" if idea.get("tags") else ""
        src_str = "👤" if idea["source"] == "user" else "🤖"
        print(f"  {status_icon} #{idea['id']:2d} {src_str} {idea['title']}{tags_str}")
        if idea.get("detail"):
            print(f"       {idea['detail'][:80]}")
        if idea.get("agent_notes"):
            notes = idea["agent_notes"].replace("\n", "\n       ")
            print(f"       💬 {notes[:120]}")

    archived = len(board.list_archived(days=30))
    if archived:
        print(f"\n  📦 归档中还有 {archived} 条历史灵感")


# ── 命令行入口 ──────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(_sys.argv) < 2:
        list_all()
    elif _sys.argv[1] == "add":
        title = _sys.argv[2] if len(_sys.argv) > 2 else "未命名灵感"
        detail = _sys.argv[3] if len(_sys.argv) > 3 else ""
        add(title, detail)
        list_all()
    elif _sys.argv[1] == "think":
        board = Board()
        board.think(int(_sys.argv[2]), " ".join(_sys.argv[3:]))
        list_all()
    elif _sys.argv[1] == "done":
        board = Board()
        board.implement(int(_sys.argv[2]), " ".join(_sys.argv[3:]))
        list_all()
    else:
        print("用法: python inspiration_board.py [add|think|done|list] [参数]")
