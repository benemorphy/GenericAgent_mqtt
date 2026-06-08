#!/usr/bin/env python3
"""
Dream Engine — Agent Dreaming记忆消化与回放引擎

基于 Deep Research + Sophub DeepResearch SOP:
1. Digest: 对话结束时压缩为记忆块存入 MariaDB dream_memories
2. Replay: 空闲时随机抽取+冲突检测+缺口标记
3. Associate: 跨域联想→灵感板
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pymysql
    _DB_CFG = {'host': '127.0.0.1', 'port': 3306,
               'user': 'root', 'password': 'mariadb',
               'database': 'Mqtt_bbs', 'connect_timeout': 3}
    _HAS_DB = True
except ImportError:
    _HAS_DB = False


def _ensure_table():
    if not _HAS_DB:
        return False
    conn = pymysql.connect(**_DB_CFG)
    conn.cursor().execute("""
        CREATE TABLE IF NOT EXISTS dream_memories (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            session_id  VARCHAR(64) NOT NULL,
            domain      VARCHAR(64) DEFAULT 'general',
            timestamp   DATETIME(3) DEFAULT NOW(3),
            context     VARCHAR(200),
            problem     TEXT,
            solution    TEXT,
            confidence  FLOAT DEFAULT 0.0,
            status      VARCHAR(16) DEFAULT 'active',
            INDEX(session_id), INDEX(domain), INDEX(status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    conn.close()
    return True


def digest_conversation(session_id, turns, domain='general'):
    """
    Digest: 将一段对话压缩为记忆块
    
    Args:
        session_id: 会话ID (如每天一个)
        turns: 对话轮次列表 [(user_msg, agent_msg, artifacts, confidence), ...]
        domain: 领域标签
    
    Returns:
        写入的记忆块数量
    """
    if not _ensure_table():
        return 0
    
    memories = []
    for i, (user_msg, agent_msg, artifacts, conf) in enumerate(turns):
        # 只保留关键决策点（conf>0.5或有产出文件）
        if conf < 0.5 and not artifacts:
            continue
        
        problem = user_msg[:200] if user_msg else ''
        solution = agent_msg[:500] if agent_msg else ''
        
        memories.append((
            session_id, domain, '',  # context=空字符串
            problem, solution, conf
        ))
    
    if not memories:
        return 0
    
    conn = pymysql.connect(**_DB_CFG)
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO dream_memories 
           (session_id, domain, context, problem, solution, confidence)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        memories
    )
    conn.commit()
    conn.close()
    return len(memories)


def replay_memories(domain=None, k=3):
    """
    Replay: 随机抽取记忆块，返回冲突和缺口
    
    Args:
        domain: 可选领域筛选
        k: 抽取对数
    
    Returns:
        insights: [{"type":"conflict"/"gap", "desc":"...", ...}]
    """
    if not _ensure_table():
        return []
    
    conn = pymysql.connect(**_DB_CFG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    if domain:
        cur.execute("SELECT * FROM dream_memories WHERE domain=%s AND status='active' ORDER BY RAND() LIMIT %s",
                   (domain, k * 2))
    else:
        cur.execute("SELECT * FROM dream_memories WHERE status='active' ORDER BY RAND() LIMIT %s", (k * 2,))
    
    rows = cur.fetchall()
    conn.close()
    
    insights = []
    for i in range(0, len(rows) - 1, 2):
        a, b = rows[i], rows[i + 1]
        
        # 冲突: 类似问题用了不同方案
        if a['problem'][:30] == b['problem'][:30] and a['solution'] != b['solution']:
            insights.append({
                "type": "conflict",
                "desc": f"类似问题'{a['problem'][:30]}有两种不同方案",
                "a": a['solution'][:100],
                "b": b['solution'][:100],
                "recommend": "需要统一策略或评估哪种更优"
            })
        
        # 缺口: 低置信度 → 自动触发技能学习
        if a['confidence'] < 0.5:
            insights.append({
                "type": "gap",
                "desc": f"低置信度问题: {a['problem'][:50]}",
                "confidence": a['confidence'],
                "recommend": "启动Deep Research"
            })
            # 自动触发技能学习
            topic = a['problem'].strip()[:40]
            if len(topic) > 5:
                try:
                    import subprocess as _sp
                    ga_root = str(Path(__file__).resolve().parents[1])
                    print(f"  📚 自动学习: {topic}")
                    proc = _sp.Popen([
                        'python', '-m', 'tools.skill_learn_from_cases_full', topic, '--force',
                        '--from-url', 'https://www.google.com/search?q=' + topic.replace(' ', '+')
                    ], cwd=ga_root, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                    insights[-1]["learn_pid"] = proc.pid
                except Exception as e:
                    print(f"  ⚠️ 自动学习启动失败: {e}")
    
    return insights


def associate_random(k=2):
    """
    Associate: 跨域联想——随机组合不同领域的记忆块
    
    Returns:
        combinations: 跨域联想结果
    """
    if not _ensure_table():
        return []
    
    conn = pymysql.connect(**_DB_CFG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT DISTINCT domain FROM dream_memories WHERE status='active'")
    domains = [r['domain'] for r in cur.fetchall()]
    
    if len(domains) < 2:
        conn.close()
        return []
    
    import random
    combos = []
    for _ in range(k):
        d1, d2 = random.sample(domains, 2)
        cur.execute("SELECT * FROM dream_memories WHERE domain=%s AND status='active' ORDER BY RAND() LIMIT 1", (d1,))
        a = cur.fetchone()
        cur.execute("SELECT * FROM dream_memories WHERE domain=%s AND status='active' ORDER BY RAND() LIMIT 1", (d2,))
        b = cur.fetchone()
        if a and b:
            combos.append({
                "domain_a": d1,
                "domain_b": d2,
                "problem_a": a['problem'][:80],
                "problem_b": b['problem'][:80],
                "solution_a": a['solution'][:80],
                "solution_b": b['solution'][:80]
            })
    
    conn.close()
    return combos


# ── 灵感#8: 可行性评分 (核心×dream_engineer) ──────────
_FEASIBILITY_WEIGHTS = {
    "has_existing_tool": 0.3,     # 已有工具可直接用
    "has_reference": 0.25,        # 有类似实现参考
    "domain_familiarity": 0.2,    # 领域熟悉度
    "resource_available": 0.15,   # 所需资源可用
    "scope_small": 0.1,           # 范围小/可快速验证
}


def score_feasibility(domain_a: str, domain_b: str, detail: str = "") -> dict:
    """
    对跨域联想进行可行性评分。

    返回:
        {"score": 0.0~1.0, "factors": {...}, "difficulty": "easy"/"medium"/"hard"}
    """
    score = 0.0
    factors = {}

    # 1. 已有工具可用的加分
    from tools.file_search import search_files
    tools_dir = Path(__file__).resolve().parent
    existing_tools = [f.stem for f in search_files("*.py", root=tools_dir)]
    domain_keywords = (domain_a + " " + domain_b).lower().split()
    overlap = sum(1 for kw in domain_keywords if any(kw in t for t in existing_tools))
    factors["has_existing_tool"] = min(overlap * 0.15, 0.3)
    score += factors["has_existing_tool"]

    # 2. 领域熟悉度 (基于内存中的SOP数量)
    memory_dir = tools_dir.parent / "memory"
    sop_files = search_files("*sop*", root=memory_dir) + search_files("*SOP*", root=memory_dir)
    sop_names = " ".join(f.stem.lower() for f in sop_files)
    fam_score = sum(0.05 for kw in domain_keywords if kw in sop_names)
    factors["domain_familiarity"] = min(fam_score, 0.2)
    score += factors["domain_familiarity"]

    # 3. 范围评估 (detail中有具体描述则加分)
    has_detail = len(detail.strip()) > 10
    factors["scope_small"] = 0.1 if has_detail else 0.0
    score += factors["scope_small"]

    # 4. 资源可用性 (不依赖外部API的加分)
    needs_external = any(kw in detail.lower() for kw in ["api", "cloud", "付费", "external"])
    factors["resource_available"] = 0.0 if needs_external else 0.15
    score += factors["resource_available"]

    # 综合评估
    score = min(round(score, 2), 1.0)
    if score >= 0.6:
        difficulty = "easy"
    elif score >= 0.3:
        difficulty = "medium"
    else:
        difficulty = "hard"

    return {
        "score": score,
        "factors": factors,
        "difficulty": difficulty,
    }


def morph_to_idea(combo: dict, board=None) -> int:
    """
    Morph: 将跨域联想变形为灵感板条目，附带可行性评分。

    灵感#8 实现: dream_engine输出结构增强，加入执行难度/预期收益评估
    """
    try:
        if board is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from inspiration_board import Board
            board = Board(bbs_backend=False)
    except ImportError:
        return -1

    domain_a = combo.get("domain_a", "未知")
    domain_b = combo.get("domain_b", "未知")
    detail = combo.get("detail", "")

    # 可行性评分
    feas = score_feasibility(domain_a, domain_b, detail)

    title = f"[Dream] {domain_a} × {domain_b}"
    detail_str = f"score={feas['score']:.2f} ({feas['difficulty']}): {detail}" if detail else f"score={feas['score']:.2f} ({feas['difficulty']})"

    idea_id = board.add_idea(
        title=title,
        detail=detail_str,
        tags=["dream", "associate"],
        source="agent"
    )

    if idea_id > 0:
        # 自动思考评分
        board.think(idea_id,
                    f"可行性评分={feas['score']}，难度={feas['difficulty']}，"
                    f"因子={feas['factors']}")

    print(f"  🧠 Morph: #{idea_id} {title} ({detail_str[:50]})")
    return idea_id


if __name__ == "__main__":
    _ensure_table()
    print("✅ dream_memories 表就绪")
    
    # 测试写入
    n = digest_conversation("test_session", [
        ("如何检测环形资金流？", "使用NetworkX simple_cycles", [], 0.9),
        ("怎么配置Oxigraph？", "cargo install oxigraph-cli", [], 0.4),
    ], domain="风控")
    print(f"📝 写入 {n} 条记忆")
    
    # 测试回放
    ins = replay_memories(k=2)
    print(f"\n💡 洞察: {len(ins)} 条")
    for i in ins:
        print(f"  [{i['type']}] {i['desc']}")
    
    # 统计
    conn = pymysql.connect(**_DB_CFG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM dream_memories")
    print(f"\n📊 总记忆数: {cur.fetchone()[0]}")
    conn.close()
