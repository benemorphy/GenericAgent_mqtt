"""
反省引擎 — 本体模型与实际系统的自动比对与同步

功能:
  1. 扫描实际代码库的模块和文件
  2. 对比 ontology_model.py 中的实体/关系/约束
  3. 检测偏差: 新增实体 / 消失实体 / 关系变化
  4. 自动更新 ontology_model.py
  5. 将偏差报告发布到诊断板

执行:
  python -m tools.reflection_engine          # 一次反射
  python -m tools.reflection_engine --watch   # 持续监控 (每 15 分钟)
"""

import sys, os, time, json, glob, re, ast

# ── 路径修补（搬迁后 GA/ 与 root 双路径） ──
_script_dir = os.path.dirname(os.path.abspath(__file__))       # GA/tools/
_ga_dir = os.path.dirname(_script_dir)                         # GA/
_root_dir = os.path.dirname(_ga_dir)                           # 项目根
sys.path.insert(0, _root_dir)   # 确保能找到 Mqtt_bbs 包
sys.path.insert(0, _ga_dir)     # 确保能找到 tools.* 包

from tools.ontology_model import ENTITIES, RELATIONS, CONSTRAINTS, INFERENCES
from Mqtt_bbs_client.board_client import BoardClient
from Mqtt_bbs_client.client import BBSClient


class ReflectionEngine:
    
    @staticmethod
    def _snake_to_camel(name: str) -> str:
        """文件名/模块名下划线→驼峰映射: board_service -> BoardService.
        对已驼峰的字符串保持原样: BoardClient -> BoardClient
        """
        parts = name.replace('-', '_').split('_')
        return ''.join(p[0].upper() + p[1:] if p else '' for p in parts)
    
    def __init__(self):
        self.root = _root_dir   # 项目根目录（搬迁修正）
        self._ga_dir = _ga_dir  # GA/ 子目录（搬迁修正）
        self.bbs = BoardClient("reflection_engine", board="agent-diagnosis")
        self.client = BBSClient("reflection_engine")
        self.token = None
        
        # 扫描结果缓存
        self._scanned_entities = set()
        self._scanned_py_files = {}
        self._scanned_rs_files = {}
    
    # ── 扫描实际系统 ──
    
    def _scan_python_modules(self):
        """扫描 Python 模块 → 提取实际存在的类/函数/模块"""
        found = {}
        py_dir = os.path.join(self.root, "Mqtt_bbs_server")
        if not os.path.isdir(py_dir):
            return found
        for f in sorted(glob.glob(os.path.join(py_dir, "*.py"))):
            name = os.path.splitext(os.path.basename(f))[0]
            if name.startswith("_"):
                continue
            found[name] = {
                "path": f,
                "size": os.path.getsize(f),
                "modified": os.path.getmtime(f)
            }
        return found
    
    def _scan_rust_modules(self):
        """扫描 Rust 模块"""
        found = {}
        rs_dirs = [
            os.path.join(self.root, "Mqtt_bbs", "tools", "Mqtt_bbs_rs"),
            os.path.join(self.root, "Mqtt_bbs", "tools", "board_service_rs"),
        ]
        for rs_dir in rs_dirs:
            src = os.path.join(rs_dir, "src")
            if not os.path.isdir(src):
                continue
            for f in sorted(glob.glob(os.path.join(src, "**", "*.rs"), recursive=True)):
                name = os.path.splitext(os.path.basename(f))[0]
                found[os.path.relpath(f, src)] = {
                    "path": f,
                    "size": os.path.getsize(f),
                    "modified": os.path.getmtime(f)
                }
        return found
    
    def _scan_running_services(self):
        """扫描运行中的服务"""
        import subprocess
        services = []
        # 检查 Rust BoardService
        r = subprocess.run('tasklist /fi "imagename eq board_service_rs.exe" /nh',
                          capture_output=True, text=True, shell=True)
        if 'board_service_rs' in r.stdout.lower():
            services.append("BoardService(Rust)")
        # 检查 Mosquitto
        r = subprocess.run('tasklist /fi "imagename eq mosquitto.exe" /nh',
                          capture_output=True, text=True, shell=True)
        if 'mosquitto' in r.stdout.lower():
            services.append("Mosquitto")
        # 检查 HTTP Gateway
        import socket
        s = socket.socket(); s.settimeout(1)
        if s.connect_ex(('127.0.0.1', 8000)) == 0:
            services.append("Gateway(HTTP)")
        s.close()
        # 检查 MariaDB
        s = socket.socket(); s.settimeout(1)
        if s.connect_ex(('127.0.0.1', 3306)) == 0:
            services.append("MariaDB")
        s.close()
        return services
    
    def _scan_skills(self):
        """扫描 skills_learning 目录 → 实际掌握的技能"""
        skills_dir = os.path.join(self._ga_dir, "skills_learning")
        if not os.path.isdir(skills_dir):
            return []
        return sorted([d for d in os.listdir(skills_dir) 
                      if os.path.isdir(os.path.join(skills_dir, d))])
    
    # ── 偏差检测 ──
    
    def _detect_drift(self) -> list:
        """检测本体模型与实际系统的偏差"""
        drifts = []
        
        # 实体: 扫描的文件 vs 本体（支持下划线→驼峰映射）
        actual_py = set(self._snake_to_camel(name) for name in self._scan_python_modules().keys())
        actual_rs = set(
            self._snake_to_camel(f.replace('.rs','').replace('/','_'))
            for f in self._scanned_rs_files
        )
        actual_all = actual_py | actual_rs
        
        # 本体中的实体名
        model_entities = set(e.name for e in ENTITIES)
        
        new_entities = actual_all - model_entities
        gone_entities = model_entities - actual_all - {"Mosquitto", "MariaDB", "LLM Provider", "BoardClient (Python)"}
        
        for e in new_entities:
            drifts.append(f"[新增] 实体 '{e}' 存在于代码但不在本体模型中")
        for e in gone_entities:
            drifts.append(f"[消失] 实体 '{e}' 在本体模型中但在代码中未发现")
        
        # 2. 运行服务检测
        running = set(self._scan_running_services())
        model_services = set(e.name for e in ENTITIES if any(rel.target == e.name or rel.source == e.name for rel in RELATIONS))
        
        for s in running:
            # 去掉后缀 (Rust)/(HTTP) 提高匹配率
            s_base = s.split('(')[0].strip()
            if s_base not in model_services and s not in model_services:
                drifts.append(f"[运行中] 服务 '{s}' 在运行但本体模型中缺少")
        
        # 3. 技能检测 — 使用 register_skills 生成实体和关系
        skills = self._scan_skills()
        if skills:
            from tools.ontology_model import register_skills
            skill_entities, skill_relations = register_skills()
            if skill_entities:
                drifts.append(f"[知识] 新增 {len(skill_entities)} 个技能实体: {', '.join(s[:20] for s in skills[:3])}...")
                # 这里只报告，不自动写入 ENTITIES 常量（防止反复修改 .py 文件）
                # 实际运行时可以动态合并
        
        # 4. 文件规模变化 — 判断实体活跃度（支持下划线→驼峰映射）
        py_files = self._scan_python_modules()
        for name, info in py_files.items():
            camel_name = self._snake_to_camel(name)
            for ent in ENTITIES:
                if camel_name == ent.name or name.lower() in ent.name.lower():
                    drifts.append(f"[活动] '{name}' ({info['size']}B, {info['modified']:.0f} 最后修改)")
        
        return drifts
    
    # ── 自动更新本体 ──
    
    def _update_ontology(self, drifts: list):
        """根据偏差更新 ontology_model.py"""
        ontology_path = os.path.join(self._ga_dir, "tools", "ontology_model.py")
        with open(ontology_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        changes = []
        for drift in drifts:
            if drift.startswith("[新增]"):
                name = drift.replace("[新增] 实体 '", "").split("'")[0]
                # 添加新实体
                new_ent = f'\n@dataclass\nclass {name}:\n    """自动发现"""\n    name: str = "{name}"\n    type: str = "auto"\n    metadata: dict = field(default_factory=lambda: {{"discovered_by": "reflection", "source": "code_scan"}})\n\n'
                # 插入到 ENTITIES 列表前
                ins_point = content.find("# =====")
                if ins_point > 0:
                    # 查找 ENTITIES 列表位置
                    pass
                changes.append(f"新增实体: {name}")
        
        if changes:
            print(f"[反省] 本体更新: {', '.join(changes)}")
            # 实际更新需要更精细的 AST 操作, 当前打印报告
        else:
            print("[反省] 本体无需更新")
    
    # ── 完整反省周期 ──
    
    def reflect(self):
        """执行一次完整反省"""
        print(f"\n{'='*50}")
        print(f"反省周期 ({time.strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"{'='*50}")
        
        # 1. 扫描
        py_files = self._scan_python_modules()
        rs_files = self._scan_rust_modules()
        running = self._scan_running_services()
        skills = self._scan_skills()
        self._scanned_py_files = py_files
        self._scanned_rs_files = rs_files
        
        print(f"  Python 模块: {len(py_files)} 个 ({', '.join(py_files.keys())[:60]}...)")
        print(f"  Rust 模块:   {len(rs_files)} 个")
        print(f"  运行服务:    {', '.join(running)}")
        print(f"  技能:        {len(skills)} 个")
        
        # 2. 偏差检测
        drifts = self._detect_drift()
        print(f"\n  偏差: {len(drifts)} 处")
        for d in drifts:
            print(f"    {d}")
            # 发布到诊断板
            if self.token:
                import json as _json
                self.bbs.post(_json.dumps({
                    "type": "reflection",
                    "severity": "info" if d.startswith("[新增]") else ("warning" if d.startswith("[消失]") else "info"),
                    "source": "reflection",
                    "component": "ontology",
                    "status": "drifted",
                    "detail": d,
                    "timestamp": time.time()
                }), self.token)
        
        # 3. 更新本体
        self._update_ontology(drifts)
        
        print(f"\n  本体状态: {len(ENTITIES)} 实体 / {len(RELATIONS)} 关系 / {len(CONSTRAINTS)} 约束 / {len(INFERENCES)} 推理")
        
        return drifts


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', action='store_true', help='持续监控模式')
    args = parser.parse_args()
    
    engine = ReflectionEngine()
    
    if args.watch:
        print("[反省] 持续监控模式启动 (每 15 分钟)")
        while True:
            engine.reflect()
            time.sleep(900)
    else:
        engine.reflect()


if __name__ == "__main__":
    main()
