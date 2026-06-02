# reflect/autonomous.py
# 当用户长时间离开时触发。仅在有实际待办任务时才返回提示，避免无意义循环。
INTERVAL = 1800
ONCE = False

def check():
    import os, json
    todo_path = os.path.join(os.path.dirname(__file__), '..', 'temp', 'TODO.txt')
    if not os.path.exists(todo_path):
        return None
    with open(todo_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 检查是否有未完成的 [ ] 条目
    pending = [line.strip() for line in content.split('\n') if line.strip().startswith('[ ]')]
    pending = [p for p in pending if '##' not in p and '->' not in p]  # 排除标题和注释行
    if pending:
        return f"[AUTO] 用户离开>30分钟, 有待办 {len(pending)} 项: {pending[0][:60]}... 请阅读自动化sop执行自动任务。"
    return None  # 无待办则不触发