# reflect/goal_prism.py — Goal Prism: 多视角并行探索 + 交叉验证
# 同一目标从多个视角(boards)并行分析，最后聚合综合
#
# 用法 (reflect 模式):
#   python agentmain.py --reflect reflect/goal_prism.py
#
# 配置: 环境变量 GOAL_PRISM_CONFIG 指向 prism_config.json
#   prism_config.json 格式:
#   {
#     "objective": "审查项目安全性",
#     "perspectives": [
#       {"name": "代码安全", "board": "prism_code_security", "focus": "SQL注入/XSS/CSRF"},
#       {"name": "依赖安全", "board": "prism_dep_security", "focus": "第三方库漏洞"},
#       {"name": "配置安全", "board": "prism_config_security", "focus": "密钥/环境变量"}
#     ],
#     "budget_per_worker": 600,
#     "max_workers": 3
#   }

import os, json, time, sys, subprocess, threading

_dir = os.path.dirname(os.path.abspath(__file__))
INTERVAL = 5
ONCE = False

_prism = None  # Prism state

def init(args):
    global _prism
    config_path = os.environ.get('GOAL_PRISM_CONFIG') or os.path.join(_dir, '..', 'temp', 'prism_config.json')
    
    if not os.path.exists(config_path):
        # 创建默认配置
        default_config = {
            "objective": "多视角分析示例",
            "perspectives": [
                {"name": "视角1", "board": "prism_view_1", "focus": "分析点A"},
                {"name": "视角2", "board": "prism_view_2", "focus": "分析点B"},
            ],
            "budget_per_worker": 300,
            "max_workers": 2
        }
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print(f"[Prism] 创建默认配置: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        _prism = json.load(f)
    
    _prism['_workers'] = {}  # name -> {proc, board, status, findings}
    _prism['_start_time'] = time.time()
    
    print(f"[Prism] 初始化: {_prism.get('objective', '')[:60]}...")
    print(f"[Prism] 视角: {len(_prism.get('perspectives', []))} 个")

# REMOVED: check (lines 57-138) - archived in _archives/

def on_done(result):
    pass

def _generate_report():
    """生成 Prism 综合报告"""
    report_path = os.path.join(_dir, '..', 'temp', 'prism_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Prism 综合报告\n\n")
        f.write(f"**目标**: {_prism.get('objective', '')}  \n")
        f.write(f"**视角数**: {len(_prism.get('perspectives', []))}  \n")
        f.write(f"**耗时**: {time.time() - _prism['_start_time']:.0f}s\n\n")
        
        for name, w in _prism['_workers'].items():
            f.write(f"## [{name}] {w['board']}\n")
            f.write(f"- 状态: {w['status']}\n")
            f.write(f"- 轮次: {w['findings']}\n\n")
        
        f.write("---\n*由 Goal Prism 自动生成*\n")
    
    print(f"[Prism] 综合报告: {report_path}")
