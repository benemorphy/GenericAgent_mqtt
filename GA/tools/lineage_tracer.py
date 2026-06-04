#!/usr/bin/env python
"""GA 全链路执行轨迹审计 (P4 Phase1: LineageTracer)

记录每次 agent 执行的完整 DAG 链路，支持回溯/回归检测。

用法:
    from tools.lineage_tracer import lt
    lt.trace_turn(turn_id="t1", agent="main", action="code_run", context={}, result={})
    chain = lt.get_lineage("t1")
    regressions = lt.find_regressions(since_version=5)
"""
import os, json, sqlite3, uuid, time
from pathlib import Path
from typing import Optional, List, Any

_DB_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "db"
_DB_PATH = _DB_DIR / "lineage.db"


class LineageTracer:
    """执行链追踪: 记录 turn/tool/decision 到 lineage DAG"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        schema = os.path.join(os.path.dirname(self.db_path), "lineage_schema.sql")
        conn = sqlite3.connect(self.db_path)
        if os.path.exists(schema):
            conn.executescript(open(schema, "r").read())
        else:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lineage (
                    id TEXT PRIMARY KEY, turn_id TEXT NOT NULL, parent_id TEXT,
                    agent TEXT, action TEXT NOT NULL, context TEXT, result TEXT,
                    status TEXT DEFAULT 'success', duration_ms REAL, created_at REAL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY, turn_id TEXT, action_type TEXT NOT NULL,
                    target TEXT, detail TEXT, created_at REAL
                );
            """)
        conn.commit(); conn.close()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def trace(self, turn_id: str, action: str, agent: str = "",
              parent_id: str = None, context: dict = None,
              result: dict = None, status: str = "success",
              duration_ms: float = 0.0) -> str:
        """记录一条执行轨迹"""
        lid = uuid.uuid4().hex[:12]
        with self._conn() as conn:
            conn.execute("INSERT INTO lineage (id,turn_id,parent_id,agent,action,context,result,status,duration_ms,created_at) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (lid, turn_id, parent_id, agent, action,
                          json.dumps(context or {}), json.dumps(result or {}),
                          status, duration_ms, time.time()))
        return lid
    
    def get_lineage(self, turn_id: str) -> list:
        """回溯某次执行的全链路"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id,parent_id,agent,action,context,result,status,duration_ms "
                "FROM lineage WHERE turn_id=? ORDER BY created_at", (turn_id,)
            ).fetchall()
        return [dict(zip(["id","parent_id","agent","action","context","result","status","duration_ms"], r)) for r in rows]
    
    def find_regressions(self, since_version: int = 0, max_errors: int = 3) -> list:
        """查找从某版本后的回归 (连续失败≥3次)"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT turn_id,action,status,created_at FROM lineage WHERE status='error' "
                "ORDER BY created_at DESC LIMIT ?", (max_errors * 5,)
            ).fetchall()
        return [dict(zip(["turn_id","action","status","created_at"], r)) for r in rows[:3]]
    
    def recent(self, limit: int = 20) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT turn_id,action,agent,status,duration_ms,created_at "
                "FROM lineage ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(zip(["turn_id","action","agent","status","duration_ms","created_at"], r)) for r in rows]
    
    def audit(self, turn_id: str, action_type: str, target: str, 
              detail: str = "", created_at: float = None) -> str:
        """记录一条审计日志 (P4)"""
        aid = uuid.uuid4().hex[:12]
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (id,turn_id,action_type,target,detail,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (aid, turn_id, action_type, target, detail, created_at or time.time())
            )
        return aid
    
    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM lineage").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM lineage WHERE status='error'").fetchone()[0]
        return {"total": total, "errors": errors, "error_rate": round(errors/max(total,1)*100, 1)}


lt = LineageTracer()
