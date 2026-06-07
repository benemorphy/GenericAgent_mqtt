"""探索 CodeGraph SQLite 数据库结构"""
import sqlite3, pathlib

cg_db = pathlib.Path("D:/open_claw_agent/Beneh/GA/.codegraph/codegraph.db")
if not cg_db.exists():
    print("CG DB 未找到")
    exit()

conn = sqlite3.connect(str(cg_db))
cursor = conn.cursor()

# 查所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"表: {tables}")

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = cursor.fetchall()
    print(f"\n=== {table} ===")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    cnt = cursor.fetchone()[0]
    print(f"  -> {cnt} 行")

# 查 import 关系表
if 'imports' in tables:
    cursor.execute("SELECT * FROM imports LIMIT 3")
    rows = cursor.fetchall()
    if rows:
        print(f"\nimports 示例: {rows}")

conn.close()
