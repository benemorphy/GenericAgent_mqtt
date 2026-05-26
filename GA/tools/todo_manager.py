#!/usr/bin/env python3
"""
TodoManager — 飞书群聊待办提取与持久化

用法:
    tm = TodoManager()
    tm.add("完成报告", open_id="ou_xxx", source="群聊A")
    lst = tm.list(open_id="ou_xxx")
    tm.done(todo_id)
"""

import json, time, os, threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "temp"
DATA_FILE = DATA_DIR / "todos.json"

_TODO_HELP = """📋 待办管理:
/todo        - 查看所有待办
/todo add <内容> - 添加待办
/todo done <id>  - 标记完成
/todo del <id>   - 删除待办"""

class TodoManager:
    def __init__(self, data_file=None):
        self._file = Path(data_file) if data_file else DATA_FILE
        self._lock = threading.Lock()
        self._todos = self._load()

    def _load(self):
        if self._file.exists():
            try:
                return json.loads(self._file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._todos, indent=2, ensure_ascii=False), encoding="utf-8")

    def add(self, content, open_id="", source="", chat_id=""):
        with self._lock:
            todo = {
                "id": int(time.time() * 1000) % 100000,
                "content": content,
                "open_id": open_id,
                "source": source,
                "chat_id": chat_id,
                "status": "todo",
                "created_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            self._todos.append(todo)
            self._save()
            return todo

    def list(self, open_id=None, status="todo"):
        with self._lock:
            items = self._todos
            if open_id:
                items = [t for t in items if t.get("open_id") == open_id]
            if status:
                items = [t for t in items if t.get("status") == status]
            return sorted(items, key=lambda x: x.get("id", 0), reverse=True)

    def done(self, todo_id):
        with self._lock:
            for t in self._todos:
                if t["id"] == todo_id:
                    t["status"] = "done"
                    self._save()
                    return t
            return None

    def remove(self, todo_id):
        with self._lock:
            for i, t in enumerate(self._todos):
                if t["id"] == todo_id:
                    self._todos.pop(i)
                    self._save()
                    return True
            return False

    def extract_todos(self, text):
        """从文本中简单检测待办项"""
        lines = text.strip().split("\n")
        todos = []
        for line in lines:
            line = line.strip()
            # 匹配常见待办格式: - [ ] / [ ] / - 待办 / 记得 / 需要 / 要...
            if line.startswith("- [ ]") or line.startswith("[ ]"):
                content = line.replace("- [ ]", "").replace("[ ]", "").strip()
                if content: todos.append(content)
            elif any(kw in line for kw in ["记得", "需要", "要", "应该", "务必", "别忘了"]):
                if len(line) > 4 and len(line) < 200:
                    todos.append(line)
        return todos

    def format_list(self, items=None):
        if items is None:
            items = self.list()
        if not items:
            return "📋 暂无待办"
        lines = [f"📋 待办 ({len([t for t in items if t['status']=='todo'])}项)"]
        for i, t in enumerate(items, 1):
            mark = "✅" if t["status"] == "done" else "⬜"
            src = f" [{t.get('source','')}]" if t.get("source") else ""
            lines.append(f"{mark} #{t['id']} {t['content']}{src}")
        return "\n".join(lines)


if __name__ == "__main__":
    tm = TodoManager()
    print(TODO_HELP)
