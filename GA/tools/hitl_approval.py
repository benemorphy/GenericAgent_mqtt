#!/usr/bin/env python3
"""
HITL Approval — 人在回路审批管理器

流程:
  1. Agent 低置信度 → publish to ontology/human/decision/pending
  2. 飞书Bot 订阅 → 发送审批卡片
  3. 人类点击 approve/reject → MQTT 回调
  4. 结果回写 MariaDB hitl_audit_log
"""

import sys, json, time, threading, uuid, os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pymysql
    _HAS_DB = True
except ImportError:
    _HAS_DB = False

DECISION_TOPIC = "ontology/human/decision"
RESPONSE_TOPIC = "ontology/human/response"

# ── 审核日志 ──

def _ensure_table():
    if not _HAS_DB:
        return False
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb',
                                database='mqtt_bbs', autocommit=True, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hitl_audit_log (
                id VARCHAR(36) PRIMARY KEY,
                order_id VARCHAR(64),
                agent_id VARCHAR(64),
                task_type VARCHAR(64),
                confidence FLOAT,
                reason TEXT,
                evidence JSON,
                status VARCHAR(32) DEFAULT 'pending',
                decided_by VARCHAR(128),
                decided_at DATETIME(3) NULL,
                created_at DATETIME(3) DEFAULT NOW(3)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.close()
        return True
    except:
        return False

def submit_decision(order_id, agent_id, task_type, confidence, reason, evidence=None):
    """提交审核请求 → MariaDB"""
    audit_id = str(uuid.uuid4())[:8]
    if not _ensure_table():
        return audit_id
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb',
                                database='mqtt_bbs', autocommit=True, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO hitl_audit_log (id, order_id, agent_id, task_type, confidence, reason, evidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (audit_id, order_id, agent_id, task_type, confidence, reason, json.dumps(evidence or {})))
        conn.close()
    except:
        pass
    return audit_id

def approve(audit_id, decided_by="feishu_bot"):
    """审批通过"""
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb',
                                database='mqtt_bbs', autocommit=True, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("UPDATE hitl_audit_log SET status='approved', decided_by=%s, decided_at=NOW(3) WHERE id=%s",
                    (decided_by, audit_id))
        conn.close()
        return True
    except:
        return False

def reject(audit_id, decided_by="feishu_bot"):
    """审批拒绝"""
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb',
                                database='mqtt_bbs', autocommit=True, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("UPDATE hitl_audit_log SET status='rejected', decided_by=%s, decided_at=NOW(3) WHERE id=%s",
                    (decided_by, audit_id))
        conn.close()
        return True
    except:
        return False

def get_pending_list(limit=10):
    """获取待审批列表"""
    if not _ensure_table():
        return []
    try:
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb',
                                database='mqtt_bbs', autocommit=True, connect_timeout=3)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT * FROM hitl_audit_log WHERE status='pending' ORDER BY created_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except:
        return []

_HITL_HELP = """🤖 人在回路 HITL 审批:
/hitl list  - 查看待审批列表
/hitl approve <id> - 审批通过
/hitl reject <id>  - 审批拒绝
"""
