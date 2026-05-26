#!/usr/bin/env python3
"""
飞书Bot定时提醒模块 — Feishu Reminder

独立模块，可被 fsapp.py 导入使用。

用法:
    from feishu_reminder import ReminderManager, start_reminder_checker

    # fsapp.py 中初始化
    reminder = ReminderManager("path/to/reminders.json")
    start_reminder_checker(reminder, send_func)

    # 处理 /remind 命令
    reminder.add("每天9:00 喝杯水", open_id="user_xxx")
    reminders = reminder.list(open_id="user_xxx")
    reminder.remove(rid, open_id="user_xxx")
"""

import json, os, threading, time, re, logging
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger("feishu_reminder")

# ── 存储 ──────────────────────────────────────────

class ReminderManager:
    """提醒管理器 — JSON 持久化"""

    def __init__(self, data_path: str = None):
        if data_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base, "temp", "reminders.json")
        self._path = data_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"seq": 0, "reminders": []}
        # Ensure seq is int
        if isinstance(self._data.get("seq"), str):
            self._data["seq"] = int(self._data["seq"])

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _next_id(self):
        self._data["seq"] += 1
        return self._data["seq"]

    # ── 解析时间 ──

    _TIME_PATTERNS = [
        # 每天HH:MM 文本
        (re.compile(r"每天(\d{1,2}):(\d{2})\s*(.*)"), lambda m: {
            "type": "daily", "hour": int(m.group(1)), "minute": int(m.group(2)),
            "text": m.group(3).strip()
        }),
        # HH:MM 文本（一次性）
        (re.compile(r"(\d{1,2}):(\d{2})\s*(.*)"), lambda m: {
            "type": "once", "hour": int(m.group(1)), "minute": int(m.group(2)),
            "text": m.group(3).strip()
        }),
    ]

    def parse_time(self, raw: str) -> Optional[dict]:
        """解析用户输入 → 提醒配置"""
        for pat, fn in self._TIME_PATTERNS:
            m = pat.match(raw.strip())
            if m:
                conf = fn(m)
                if conf and conf.get("text"):
                    return conf
        return None

    # ── CRUD ──

    def add(self, raw_input: str, open_id: str = "") -> Optional[dict]:
        """添加提醒。返回提醒dict或None"""
        conf = self.parse_time(raw_input)
        if not conf:
            return None
        reminder = {
            "id": self._next_id(),
            "open_id": open_id,
            "type": conf["type"],
            "hour": conf["hour"],
            "minute": conf["minute"],
            "text": conf["text"],
            "enabled": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_fired": None,
        }
        with self._lock:
            self._data["reminders"].append(reminder)
            self._save()
        return reminder

    def list(self, open_id: str = "") -> list:
        """列出提醒。open_id="" 返回全部"""
        with self._lock:
            all_r = self._data["reminders"]
        if open_id:
            return [r for r in all_r if r.get("open_id") == open_id and r.get("enabled", True)]
        return [r for r in all_r if r.get("enabled", True)]

    def remove(self, rid: int, open_id: str = "") -> bool:
        """删除提醒"""
        with self._lock:
            for r in self._data["reminders"]:
                if r["id"] == rid:
                    if open_id and r.get("open_id") != open_id:
                        return False
                    self._data["reminders"].remove(r)
                    self._save()
                    return True
        return False

    def get_due(self) -> list:
        """获取当前到期的提醒"""
        now = datetime.now()
        due = []
        with self._lock:
            for r in self._data["reminders"]:
                if not r.get("enabled", True):
                    continue
                # 检查是否到期
                if r["type"] == "daily":
                    if r["hour"] == now.hour and r["minute"] == now.minute:
                        # 避免重复触发（同分钟）
                        last = r.get("last_fired")
                        if last:
                            lt = datetime.strptime(last, "%Y-%m-%d %H:%M")
                            if lt.hour == now.hour and lt.minute == now.minute:
                                continue
                        r["last_fired"] = now.strftime("%Y-%m-%d %H:%M")
                        due.append(r.copy())
                elif r["type"] == "once":
                    if r["hour"] == now.hour and r["minute"] == now.minute:
                        last = r.get("last_fired")
                        if not last:
                            r["last_fired"] = now.strftime("%Y-%m-%d %H:%M")
                            r["enabled"] = False  # 一次性触发后禁用
                            due.append(r.copy())
            if due:
                self._save()
        return due


# ── 后台检查线程 ──

def start_reminder_checker(manager: ReminderManager, send_func: Callable,
                           interval: int = 30, daemon: bool = True):
    """
    启动后台提醒检查线程。

    参数:
        manager: ReminderManager 实例
        send_func: 发送函数 (open_id, text) → None
        interval: 检查间隔（秒）
        daemon: 是否daemon线程
    """
    stop_event = threading.Event()

    def _check():
        while not stop_event.is_set():
            try:
                due = manager.get_due()
                for r in due:
                    msg = f"⏰ 提醒: {r['text']}"
                    if r.get("open_id"):
                        send_func(r["open_id"], msg)
                    logger.info(f"发送提醒 #{r['id']}: {r['text']}")
            except Exception as e:
                logger.error(f"提醒检查失败: {e}")
            stop_event.wait(interval)

    t = threading.Thread(target=_check, daemon=daemon)
    t.start()
    logger.info(f"提醒检查线程已启动（间隔{interval}s）")
    return stop_event


# ── 格式化输出 ──

def format_reminder_list(reminders: list) -> str:
    """格式化提醒列表为文本"""
    if not reminders:
        return "暂无提醒"
    lines = ["📋 你的提醒列表:\n"]
    for r in reminders:
        time_str = f"每天 {r['hour']:02d}:{r['minute']:02d}" if r['type'] == 'daily' else f"{r['hour']:02d}:{r['minute']:02d}(一次性)"
        lines.append(f"  [{r['id']}] {time_str} — {r['text']}")
    return "\n".join(lines)


# ── 命令帮助 ──

REMIND_HELP = """📌 提醒命令:

/remind add 每天9:00 喝杯水    — 添加每日提醒
/remind add 14:30 开会提醒    — 添加一次性提醒
/remind list                   — 查看提醒列表
/remind del <id>               — 删除提醒
/remind help                   — 显示帮助"""


if __name__ == "__main__":
    # 简单自测
    logging.basicConfig(level=logging.INFO)
    rm = ReminderManager()
    
    # 测试解析
    tests = [
        "每天9:00 喝杯水",
        "14:30 开会提醒",
    ]
    for t in tests:
        conf = rm.parse_time(t)
        print(f"  parse('{t}') → {conf}")
    
    # 测试CRUD
    r = rm.add("每天8:00 早安提醒", open_id="test_user")
    print(f"\n  add → #{r['id']}")
    r2 = rm.add("18:00 下班打卡", open_id="test_user")
    print(f"  add → #{r2['id']}")
    
    lst = rm.list(open_id="test_user")
    print(f"  list → {len(lst)}条")
    for l in lst:
        print(f"    [{l['id']}] {l['text']}")
    
    rm.remove(r['id'], open_id="test_user")
    print(f"  remove #{r['id']} → list={len(rm.list(open_id='test_user'))}条")
    
    print("\n✅ 提醒模块自测通过")
