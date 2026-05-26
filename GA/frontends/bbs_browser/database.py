"""BBS Board Browser — 数据库层"""

import pymysql
from pymysql.cursors import DictCursor
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def get_db():
    """获取数据库连接"""
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=5,
    )
def init_db():
    """初始化表结构（幂等）"""
    db = get_db()
    cur = db.cursor()
    # ── web_users ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            username    VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            display_name VARCHAR(128) NOT NULL DEFAULT '',
            role        VARCHAR(16) NOT NULL DEFAULT 'viewer',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login  DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # ── boards ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id          VARCHAR(32) PRIMARY KEY,
            name        VARCHAR(64) NOT NULL,
            description TEXT,
            icon        VARCHAR(16) DEFAULT '📋',
            source_type VARCHAR(32) NOT NULL DEFAULT 'table',
            source_table VARCHAR(64),
            source_filter VARCHAR(256) DEFAULT '',
            sort_field  VARCHAR(32) DEFAULT 'id',
            sort_dir    VARCHAR(4) DEFAULT 'DESC',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    db.commit()
    db.close()


def seed_boards():
    """插入默认板块（幂等）"""
    boards = [
        ('inspiration', '灵感板', '智能体灵感与创造性想法', '💡', 'table', 'bbs_posts', "board='agent-inspiration'", 'id', 'DESC'),
        ('brainstorm', '脑暴', '跨域联想与多视角分析', '🧠', 'table', 'brainstorm_sessions', '', 'id', 'DESC'),
        ('bbs', 'BBS 帖子', 'Agent 通信记录', '💬', 'table', 'bbs_posts', "board='agent-bbs-test'", 'id', 'DESC'),
        ('tasks', '任务', '智能体任务状态', '⚡', 'table', 'agent_sessions', '', 'id', 'DESC'),
        ('dreams', '梦境记忆', 'DREAM 引擎产出', '🌙', 'table', 'dream_memories', '', 'id', 'DESC'),
        ('research', 'Deep Research', '深度研究结果（预留）', '🔬', 'table', 'bbs_posts', "board='agent-research'", 'id', 'DESC'),
    ]
    db = get_db()
    cur = db.cursor()
    for b in boards:
        cur.execute("""
            INSERT IGNORE INTO boards (id, name, description, icon, source_type, source_table, source_filter, sort_field, sort_dir)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, b)
    db.commit()
    db.close()
    print(f"  [seed] {len(boards)} boards seeded")


def get_boards():
    """获取所有板块"""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM boards ORDER BY id")
    boards = cur.fetchall()
    db.close()
    
    # 填充每个板块的帖子数
    for b in boards:
        try:
            db2 = get_db()
            c2 = db2.cursor()
            if b['source_filter']:
                c2.execute(f"SELECT COUNT(*) as cnt FROM {b['source_table']} WHERE {b['source_filter']}")
            else:
                c2.execute(f"SELECT COUNT(*) as cnt FROM {b['source_table']}")
            b['post_count'] = c2.fetchone()['cnt']
            db2.close()
        except Exception:
            b['post_count'] = 0
    return boards


def get_board(board_id: str):
    """获取单个板块"""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM boards WHERE id=%s", (board_id,))
    board = cur.fetchone()
    db.close()
    return board


def query_posts(board, page: int = 1, q: str = "", limit: int = 50):
    """查询板块帖子（带分页 + 搜索）"""
    offset = (page - 1) * limit
    table = board['source_table']
    where_clauses = []
    params = []
    
    if board.get('source_filter'):
        where_clauses.append(board['source_filter'])
    if q:
        # 不同表的全文搜索字段不同
        search_fields = {
            'bbs_posts': 'content',
            'brainstorm_sessions': 'CONCAT(topic, idea, perspective)',
            'agent_sessions': 'CONCAT(agent_id, status)',
            'dream_memories': 'CONCAT(domain, context, problem, solution)',
        }
        field = search_fields.get(table, 'content')
        where_clauses.append(f"{field} LIKE %s")
        params.append(f"%{q}%")
    
    where = ""
    if where_clauses:
        where = " WHERE " + " AND ".join(where_clauses)
    
    sort = f" ORDER BY {board['sort_field']} {board['sort_dir']}"
    
    db = get_db()
    cur = db.cursor()
    
    # 总数
    cur.execute(f"SELECT COUNT(*) as total FROM {table}{where}", params)
    total = cur.fetchone()['total']
    
    # 数据
    cur.execute(f"SELECT * FROM {table}{where}{sort} LIMIT {limit} OFFSET {offset}", params)
    posts = cur.fetchall()
    db.close()
    
    return posts, total


def query_all_posts(q: str, limit: int = 20):
    """跨板块搜索"""
    results = []
    boards = get_boards()
    for board in boards:
        try:
            posts, _ = query_posts(board, page=1, q=q, limit=limit)
            for p in posts:
                results.append({**p, '_board_id': board['id'], '_board_name': board['name']})
        except Exception:
            pass
    return sorted(results, key=lambda x: x.get('created_at', 0) or x.get('id', 0), reverse=True)[:limit]
