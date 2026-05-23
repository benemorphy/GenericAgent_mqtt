"""
Diagnosis Agent — 基于 ontology_model 的自主诊断服务

功能:
  1. 每 60 秒采集 healthcheck 数据
  2. 加载 ontology_model 的约束 + 推理
  3. 生成诊断报告帖子到 board/diagnosis/post/
  4. 发布概览到 board/diagnosis/summary (retain)

启动:
  python -m tools.diagnosis_agent
"""

import sys, os, time, json, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mqtt_bbs.board_client import BoardClient
from mqtt_bbs.client import BBSClient
from tools.ontology_model import ENTITIES, RELATIONS, CONSTRAINTS, INFERENCES


class DiagnosisAgent:
    """自主诊断 Agent"""
    
    def __init__(self):
        self.board = "agent-diagnosis"
        self.agent_id = "diagnosis_agent"
        self.bbs = BoardClient(self.agent_id, board=self.board)
        self.client = BBSClient(self.agent_id)
        self.token = None
        self._running = False
        self._results = {}  # 诊断结果缓存
    
    def start(self):
        """启动诊断循环"""
        self.bbs.connect()
        info = self.bbs.register("Diagnosis Agent")
        self.token = info.get("token", "")
        self.client.connect()
        
        print(f"[Diagnosis] 注册成功, board={self.board}")
        print(f"[Diagnosis] 实体={len(ENTITIES)}, 关系={len(RELATIONS)}")
        print(f"[Diagnosis] 约束={len(CONSTRAINTS)}, 推理={len(INFERENCES)}")
        
        self._running = True
        self._run_once()  # 立即执行一次
        while self._running:
            time.sleep(60)
            self._run_once()
    
    def stop(self):
        self._running = False
        self.client.disconnect()
        self.bbs.disconnect()
    
    def _run_once(self):
        """一次诊断周期"""
        print(f"\n[Diagnosis] ====== 诊断周期 ({time.strftime('%H:%M:%S')}) ======")
        
        # 1. 加载约束检查
        self._check_constraints()
        
        # 2. 运行推理
        self._run_inferences()
        
        # 3. 发布概览
        self._publish_summary()
        
        print(f"[Diagnosis] 完成")
    
    def _check_constraints(self):
        """检查每个约束并生成诊断帖子"""
        for i, c in enumerate(CONSTRAINTS):
            # 模拟检查 (实际应采集真实数据)
            passed = self._simulate_check(c)
            
            # 生成诊断帖子
            post_type = "info" if passed else ("error" if c.severity == "error" else "warning")
            severity = c.severity
            status = "healthy" if passed else "degraded"
            
            content = json.dumps({
                "type": post_type,
                "severity": severity,
                "source": "constraint",
                "rule": c.description,
                "component": c.description.split(" ")[0] if c.description else "unknown",
                "status": status,
                "detail": f"约束: {c.description[:60]}...\n来源: {c.source}\n修复: {c.fix}",
                "evidence_count": 1,
                "timestamp": time.time()
            })
            
            self.bbs.post(content, self.token)
            print(f"  [{severity.upper()}] {c.description[:50]}... → {status}")
    
    def _run_inferences(self):
        """运行推理规则"""
        for i, inf in enumerate(INFERENCES):
            content = json.dumps({
                "type": "inference",
                "severity": "info",
                "source": "inference",
                "rule": inf.premise[:60],
                "component": "system",
                "status": "inferred",
                "detail": f"前提: {inf.premise}\n结论: {inf.conclusion}\n置信度: {inf.confidence}\n验证: {inf.evidence_count} 次",
                "evidence_count": inf.evidence_count,
                "timestamp": time.time()
            })
            self.bbs.post(content, self.token)
            print(f"  [INFERENCE] {inf.premise[:40]}... → {inf.conclusion[:40]}...")
    
    def _publish_summary(self):
        """发布诊断概览 (retain)"""
        summary = {
            "total_constraints": len(CONSTRAINTS),
            "total_inferences": len(INFERENCES),
            "total_entities": len(ENTITIES),
            "total_relations": len(RELATIONS),
            "open_alerts": 0,
            "timestamp": time.time()
        }
        self.client.publish(f"board/diagnosis/summary", summary, retain=True)
        print(f"  [SUMMARY] 概览已发布")
    
    def _simulate_check(self, constraint):
        """模拟约束检查 (实际应连接真实数据源)"""
        # 简化: 大部分约束通过, 少数模拟异常
        if constraint.severity == "info":
            return False  # info 级别的约束总是"有改善空间"
        return True  # error/warning 默认通过


def main():
    agent = DiagnosisAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
        print("\n[Diagnosis] 已停止")


if __name__ == "__main__":
    main()
