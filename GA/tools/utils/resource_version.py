#!/usr/bin/env python
"""GA 资源版本管理 (P4 Phase2: ResourceVersionManager)

版本化 Prompt/Tool/Agent 资源，支持快照/对比/回滚/提升。

用法:
    from tools.utils.resource_version import rvm
    v = rvm.snapshot("tool", "code_run", snapshot={"code": "..."})
    diff = rvm.compare("tool", "code_run", v1=1, v2=2)
    rvm.rollback("tool", "code_run", target_version=1)
    rvm.promote("tool", "code_run", version=2, stage="production")
"""
import os, json, sqlite3, uuid, hashlib, time
from pathlib import Path
from typing import Optional, List, Any, Dict

_DB_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "db" / "lineage.db"


def _checksum(data: dict) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


class ResourceVersionManager:
    """资源版本管理器: snapshot/compare/rollback/promote"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resource_versions (
                id TEXT PRIMARY KEY, resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL, version INT NOT NULL,
                stage TEXT DEFAULT 'dev', snapshot TEXT NOT NULL,
                checksum TEXT, parent_version INT, created_by TEXT,
                created_at REAL,
                UNIQUE(resource_type, resource_id, version)
            );
        """)
        conn.commit(); conn.close()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def snapshot(self, resource_type: str, resource_id: str,
                 snapshot: dict, created_by: str = "") -> dict:
        """创建资源快照, 自动递增版本号"""
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT MAX(version) FROM resource_versions WHERE resource_type=? AND resource_id=?",
                (resource_type, resource_id)
            )
            max_v = cur.fetchone()[0] or 0
            new_v = max_v + 1
            vid = uuid.uuid4().hex[:12]
            cs = _checksum(snapshot)
            conn.execute(
                "INSERT INTO resource_versions (id,resource_type,resource_id,version,stage,snapshot,checksum,parent_version,created_by,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (vid, resource_type, resource_id, new_v, "dev",
                 json.dumps(snapshot), cs, max_v if max_v > 0 else None,
                 created_by, time.time())
            )
        return {"id": vid, "type": resource_type, "resource_id": resource_id,
                "version": new_v, "checksum": cs}
    
    def get(self, resource_type: str, resource_id: str,
            version: int = None, stage: str = None) -> Optional[dict]:
        """获取指定资源版本的快照"""
        with self._conn() as conn:
            if version:
                row = conn.execute(
                    "SELECT version,stage,snapshot,checksum,created_at "
                    "FROM resource_versions WHERE resource_type=? AND resource_id=? AND version=?",
                    (resource_type, resource_id, version)
                ).fetchone()
            elif stage:
                row = conn.execute(
                    "SELECT version,stage,snapshot,checksum,created_at "
                    "FROM resource_versions WHERE resource_type=? AND resource_id=? AND stage=? "
                    "ORDER BY version DESC LIMIT 1",
                    (resource_type, resource_id, stage)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT version,stage,snapshot,checksum,created_at "
                    "FROM resource_versions WHERE resource_type=? AND resource_id=? "
                    "ORDER BY version DESC LIMIT 1",
                    (resource_type, resource_id)
                ).fetchone()
        if not row: return None
        return {"version": row[0], "stage": row[1],
                "snapshot": json.loads(row[2]), "checksum": row[3], "created_at": row[4]}
    
    def compare(self, resource_type: str, resource_id: str,
                v1: int, v2: int) -> dict:
        """对比两个版本的差异"""
        s1 = self.get(resource_type, resource_id, version=v1)
        s2 = self.get(resource_type, resource_id, version=v2)
        if not s1 or not s2:
            return {"error": "版本不存在", "v1_found": s1 is not None, "v2_found": s2 is not None}
        snap1, snap2 = s1["snapshot"], s2["snapshot"]
        all_keys = set(snap1) | set(snap2)
        added = {k: snap2[k] for k in all_keys if k not in snap1}
        removed = {k: snap1[k] for k in all_keys if k not in snap2}
        changed = {k: {"from": snap1[k], "to": snap2[k]} for k in all_keys 
                   if k in snap1 and k in snap2 and snap1[k] != snap2[k]}
        return {"v1": v1, "v2": v2, "added": added, "removed": removed,
                "changed": changed, "same_checksum": s1["checksum"] == s2["checksum"]}
    
    def rollback(self, resource_type: str, resource_id: str,
                 target_version: int) -> Optional[dict]:
        """回滚到指定版本 (通过创建新快照)"""
        target = self.get(resource_type, resource_id, version=target_version)
        if not target: return None
        return self.snapshot(resource_type, resource_id, target["snapshot"],
                             created_by=f"rollback_v{target_version}")
    
    def promote(self, resource_type: str, resource_id: str,
                version: int, stage: str = "production") -> bool:
        """提升版本阶段: dev → staging → production"""
        if stage not in ("dev", "staging", "production"):
            return False
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE resource_versions SET stage=? WHERE resource_type=? AND resource_id=? AND version=?",
                (stage, resource_type, resource_id, version)
            )
            return cur.rowcount > 0
    
    def history(self, resource_type: str, resource_id: str, limit: int = 10) -> list:
        """获取资源的版本历史"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT version,stage,checksum,created_by,created_at "
                "FROM resource_versions WHERE resource_type=? AND resource_id=? "
                "ORDER BY version DESC LIMIT ?",
                (resource_type, resource_id, limit)
            ).fetchall()
        return [dict(zip(["version","stage","checksum","created_by","created_at"], r)) for r in rows]


rvm = ResourceVersionManager()
