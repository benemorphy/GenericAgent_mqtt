#!/usr/bin/env python
"""GA 执行轨迹记录器 (P2 Phase1: TurnTracer)

记录每次 agent 执行的完整轨迹到 SQLite，支持回放和搜索。

用法:
    from tools.tracer import tracer
    tracer.record(turn_id="xxx", prompt="...", tool_calls=[...], results=[...], reward=0.8)
    turn = tracer.replay("xxx")
    results = tracer.search("file_read 失败")
"""
import os
import json
import sqlite3
import threading
import time
from typing import Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

_TRACE_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "trace.db")


@dataclass
class TurnRecord:
    """单次 agent 执行的完整记录"""
    turn_id: str
    timestamp: float = 0.0
    prompt: str = ""
    tool_calls: list = field(default_factory=list)
    results: list = field(default_factory=list)
    reward: float = 0.0
    error: Optional[str] = None
    duration_ms: float = 0.0
    model: str = ""
    metadata: dict = field(default_factory=dict)


class TurnTracer:
    """轨迹记录器 (SQLite持久化)"""
    
    def __init__(self, db_path: str = _TRACE_DB):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_db()
    
    def init_db(self):
        """手动初始化/重建数据库 (公开接口)"""
        self._ensure_db()
    
    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    turn_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    prompt TEXT,
                    tool_calls TEXT,
                    results TEXT,
                    reward REAL,
                    error TEXT,
                    duration_ms REAL,
                    model TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_reward ON traces(reward)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_ts ON traces(timestamp)")
            conn.commit()
            conn.close()
    
    def record(self, turn_id: str, prompt: str = "", tool_calls: list = None,
               results: list = None, reward: float = 0.0, error: str = None,
               duration_ms: float = 0.0, model: str = "", metadata: dict = None):
        """记录一次执行轨迹"""
        record = TurnRecord(
            turn_id=turn_id,
            timestamp=time.time(),
            prompt=prompt[:5000],  # 截断长文本
            tool_calls=tool_calls or [],
            results=results or [],
            reward=reward,
            error=error,
            duration_ms=duration_ms,
            model=model,
            metadata=metadata or {}
        )
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "REPLACE INTO traces VALUES (?,?,?,?,?,?,?,?,?,?)",
                (record.turn_id, record.timestamp, record.prompt,
                 json.dumps(record.tool_calls, ensure_ascii=False),
                 json.dumps(record.results, ensure_ascii=False),
                 record.reward, record.error, record.duration_ms,
                 record.model, json.dumps(record.metadata, ensure_ascii=False))
            )
            conn.commit()
            conn.close()
        return record
    
    def replay(self, turn_id: str) -> Optional[TurnRecord]:
        """回放指定 turn 的完整记录"""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT * FROM traces WHERE turn_id=?", (turn_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return TurnRecord(
            turn_id=row[0], timestamp=row[1], prompt=row[2],
            tool_calls=json.loads(row[3] or "[]"),
            results=json.loads(row[4] or "[]"),
            reward=row[5], error=row[6], duration_ms=row[7],
            model=row[8], metadata=json.loads(row[9] or "{}")
        )
    
    def search(self, query: str, limit: int = 20) -> list[TurnRecord]:
        """搜索轨迹 (基于 prompt 和 error 的LIKE匹配)"""
        pattern = f"%{query}%"
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT * FROM traces WHERE prompt LIKE ? OR error LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (pattern, pattern, limit)
        ).fetchall()
        conn.close()
        return [TurnRecord(
            turn_id=r[0], timestamp=r[1], prompt=r[2],
            tool_calls=json.loads(r[3] or "[]"),
            results=json.loads(r[4] or "[]"),
            reward=r[5], error=r[6], duration_ms=r[7],
            model=r[8], metadata=json.loads(r[9] or "{}")
        ) for r in rows]
    
    def recent(self, limit: int = 10) -> list[TurnRecord]:
        """最近 N 条轨迹"""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT * FROM traces ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [TurnRecord(
            turn_id=r[0], timestamp=r[1], prompt=r[2],
            tool_calls=json.loads(r[3] or "[]"),
            results=json.loads(r[4] or "[]"),
            reward=r[5], error=r[6], duration_ms=r[7],
            model=r[8], metadata=json.loads(r[9] or "{}")
        ) for r in rows]
    
    def stats(self) -> dict:
        """轨迹统计"""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        avg_reward = conn.execute("SELECT AVG(reward) FROM traces").fetchone()[0] or 0
        err_count = conn.execute("SELECT COUNT(*) FROM traces WHERE error IS NOT NULL").fetchone()[0]
        conn.close()
        return {"total": total, "avg_reward": round(avg_reward, 3), "error_rate": round(err_count/total, 3) if total else 0}

    def codegraph_audit_tool(self, tool_name: str, tool_args: dict = None, metadata: dict = None) -> dict:
        """对工具调用执行 CodeGraph 审计 (P2: 仅修改代码类工具触发)"""
        _MODIFY_TOOLS = {"code_run", "file_patch", "file_write"}
        if tool_name not in _MODIFY_TOOLS:
            return {}
        
        try:
            from tools.codegraph_db import db_available, analyze_complexity, find_dead_imports
        except ImportError:
            return {}
        
        if not db_available():
            return {}
        
        result = {}
        if tool_name == "code_run":
            try:
                complex = analyze_complexity(5)
                result["complexity_hot"] = [{"file": c["file_path"], "func": c["name"], "lines": c["line_count"]} for c in complex]
            except Exception:
                pass
        if tool_name in ("file_patch", "file_write"):
            try:
                dead = find_dead_imports(5)
                result["dead_imports"] = len(dead)
            except Exception:
                pass
        if result:
            print(f"  [CodeGraph] 审计完成: {list(result.keys())}")
        return result


# 全局单例
tracer = TurnTracer()


if __name__ == "__main__":
    # 测试
    t = tracer.record("test_001", prompt="分析代码", tool_calls=[{"name":"code_run"}],
                      results=["success"], reward=1.0, model="deepseek-v4")
    print(f"记录完成: {t.turn_id}")
    r = tracer.replay("test_001")
    print(f"回放: {r.turn_id} reward={r.reward}")
    print(f"统计: {tracer.stats()}")
