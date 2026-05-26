#!/usr/bin/env python3
"""
MASC实时步骤检测器 — 运行时检测工具执行异常

在BaseHandler的tool_after_callback中集成，对每次工具调用结果进行
实时分析，识别失败信号并注入到下一轮提示中。

集成方式（在handler子类中）:
```python
from tools.step_detector import StepDetector

class MyHandler(BaseHandler):
    def __init__(self):
        self._detector = StepDetector()
    
    def tool_after_callback(self, tool_name, args, response, ret):
        anomaly = self._detector.analyze(tool_name, args, ret)
        if anomaly:
            # 注入到response或上下文
            pass
```

用法:
  python tools/step_detector.py --test    # 自检/演示
"""

import re, json
from typing import Optional


class StepAnomaly:
    """检测到的步骤异常"""
    
    # 异常严重等级
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'
    
    SEVERITY_ORDER = {CRITICAL: 3, WARNING: 2, INFO: 1}
    
    def __init__(self, tool_name: str, pattern_id: str, severity: str,
                 message: str, evidence: str = ''):
        self.tool_name = tool_name
        self.pattern_id = pattern_id
        self.severity = severity
        self.message = message
        self.evidence = evidence[:200]  # 截断过长证据
    
    def to_json(self):
        return {
            'tool': self.tool_name,
            'pattern': self.pattern_id,
            'severity': self.severity,
            'msg': self.message,
            'evidence': self.evidence,
        }
    
    def __repr__(self):
        return f'[{self.severity.upper()}] {self.tool_name}: {self.message}'


# ============================================================
# 检测规则: (pattern_id, 匹配条件, 消息模板)
# ============================================================

class StepDetector:
    """运行时步骤检测器 — 分析工具执行结果"""
    
    def __init__(self):
        self._anomaly_history = []  # 本轮检测到的所有异常
        self._consecutive_errors = {}  # 每个工具的连续错误计数
    
    def analyze(self, tool_name: str, args: dict, ret) -> Optional[StepAnomaly]:
        """分析单次工具调用结果, 返回异常(如有)"""
        
        # 提取返回值文本
        ret_text = self._extract_text(ret)
        if ret_text is None:
            return None
        
        anomaly = self._check_all_patterns(tool_name, args, ret, ret_text)
        
        if anomaly:
            self._anomaly_history.append(anomaly)
            # 更新连续错误计数
            key = f'{tool_name}/{anomaly.pattern_id}'
            self._consecutive_errors[key] = self._consecutive_errors.get(key, 0) + 1
        
        return anomaly
    
    def _extract_text(self, ret):
        """统一提取返回值文本"""
        if ret is None:
            return ''
        if isinstance(ret, str):
            return ret
        if isinstance(ret, dict):
            # StepOutcome.data 或其他dict
            return json.dumps(ret, ensure_ascii=False)
        if hasattr(ret, 'data'):
            # StepOutcome
            data = ret.data
            if data is None:
                return ''
            if isinstance(data, dict):
                return json.dumps(data, ensure_ascii=False)
            return str(data)
        return str(ret)
    
    def _check_all_patterns(self, tool_name, args, ret, text) -> Optional[StepAnomaly]:
        """检查所有已知失败模式"""
        
        checks = [
            # ---- 通用模式 ----
            ('empty_result', self._check_empty, StepAnomaly.WARNING),
            ('error_message', self._check_error_msg, StepAnomaly.WARNING),
            ('permission_denied', self._check_permission, StepAnomaly.CRITICAL),
            ('timeout', self._check_timeout, StepAnomaly.CRITICAL),
            ('truncated_output', self._check_truncated, StepAnomaly.INFO),
            
            # ---- 工具特定模式 ----
            ('file_not_found', self._check_file_not_found, StepAnomaly.WARNING),
            ('empty_scan', self._check_empty_scan, StepAnomaly.INFO),
            ('parse_error', self._check_parse_error, StepAnomaly.WARNING),
        ]
        
        for pattern_id, checker, severity in checks:
            result = checker(tool_name, args, ret, text)
            if result:
                return StepAnomaly(tool_name, pattern_id, severity, result, evidence=text[:150])
        
        # 连续失败检测 (同一工具连续3次异常)
        consecutive = self._check_consecutive_failures(tool_name)
        if consecutive:
            return StepAnomaly(tool_name, 'consecutive_failures', StepAnomaly.CRITICAL,
                               consecutive, evidence='')
        
        return None
    
    # ---- 通用检测器 ----
    
    def _check_empty(self, tool_name, args, ret, text) -> Optional[str]:
        """空结果检测"""
        if not text or text.strip() in ('', '{}', '[]', 'null', 'None', '""', "''"):
            return f'返回结果为空'
        return None
    
    def _check_error_msg(self, tool_name, args, ret, text) -> Optional[str]:
        """错误消息检测"""
        error_keywords = [
            'error', 'failed', 'failure', 'exception', 'traceback',
            '错误', '失败', '异常', '出错',
            'unexpected', 'invalid', 'cannot', "couldn't", "can't",
            'not found', 'not exist',
        ]
        lower = text.lower()
        for kw in error_keywords:
            if kw in lower:
                return f'检测到错误关键词: "{kw}"'
        return None
    
    def _check_permission(self, tool_name, args, ret, text) -> Optional[str]:
        """权限拒绝检测"""
        lower = text.lower()
        if any(kw in lower for kw in ['permission denied', 'access denied', '拒绝访问',
                                        'access is denied', '没有权限', '未经授权']):
            return '权限不足'
        return None
    
    def _check_timeout(self, tool_name, args, ret, text) -> Optional[str]:
        """超时检测"""
        lower = text.lower()
        if any(kw in lower for kw in ['timeout', 'timed out', '超时', 'time out']):
            return '操作超时'
        return None
    
    def _check_truncated(self, tool_name, args, ret, text) -> Optional[str]:
        """截断检测"""
        if text.endswith('...') or text.endswith('...(truncated)'):
            return '输出被截断'
        # Check for truncated JSON
        if text.count('{') != text.count('}') or text.count('[') != text.count(']'):
            return '输出可能不完整(括号不匹配)'
        return None
    
    # ---- 工具特定检测器 ----
    
    def _check_file_not_found(self, tool_name, args, ret, text) -> Optional[str]:
        """文件不存在检测"""
        lower = text.lower()
        if any(kw in lower for kw in ['no such file', 'file not found', '找不到文件',
                                        'cannot find', 'does not exist', '找不到']):
            path = args.get('path', args.get('file_path', ''))
            hint = f' ({path})' if path else ''
            return f'文件不存在{hint}'
        return None
    
    def _check_empty_scan(self, tool_name, args, ret, text) -> Optional[str]:
        """空扫描检测 (web_scan)"""
        if tool_name != 'web_scan':
            return None
        if not text or len(text.strip()) < 50:
            return 'web_scan返回内容过少, 可能页面未加载完全'
        return None
    
    def _check_parse_error(self, tool_name, args, ret, text) -> Optional[str]:
        """解析错误检测"""
        lower = text.lower()
        if any(kw in lower for kw in ['parse error', 'parsing failed', 'syntax error',
                                        'json decode', 'unmarshal', '解析失败',
                                        'could not parse']):
            return '解析错误'
        return None
    
    # ---- 连续失败检测 ----
    
    def _check_consecutive_failures(self, tool_name: str) -> Optional[str]:
        """连续失败检测 — 同一工具反复失败"""
        thresholds = {
            'code_run': 2,
            'web_scan': 2,
            'file_read': 2,
            'file_write': 2,
            'web_execute_js': 2,
        }
        threshold = thresholds.get(tool_name, 3)
        
        total_errors = sum(
            count for key, count in self._consecutive_errors.items()
            if key.startswith(tool_name + '/')
        )
        if total_errors >= threshold:
            return f'连续{total_errors}次失败, 建议切换策略'
        return None
    
    # ---- 批量结果 ----
    
    def get_summary(self) -> list:
        """获取本轮检测摘要"""
        if not self._anomaly_history:
            return []
        # 按严重等级排序
        sorted_anomalies = sorted(
            self._anomaly_history,
            key=lambda a: StepAnomaly.SEVERITY_ORDER.get(a.severity, 0),
            reverse=True
        )
        return [a.to_json() for a in sorted_anomalies]
    
    def clear(self):
        """重置检测状态"""
        self._anomaly_history.clear()
        self._consecutive_errors.clear()
    
    def generate_prompt_suffix(self) -> str:
        """生成注入到LLM上下文的提示后缀"""
        summary = self.get_summary()
        if not summary:
            return ''
        
        # 只注入critical和warning
        significant = [s for s in summary 
                       if s['severity'] in (StepAnomaly.CRITICAL, StepAnomaly.WARNING)]
        if not significant:
            return ''
        
        lines = ['\n--- 运行时步骤检测结果 ---']
        for s in significant[:3]:  # 最多3条
            lines.append(f"[{s['severity'].upper()}] {s['tool']}: {s['msg']}")
        lines.append('---\n')
        return '\n'.join(lines)


# ============================================================
# 自检/演示
# ============================================================

def _demo():
    """演示各种检测场景"""
    d = StepDetector()
    
    test_cases = [
        ('code_run', {}, 'ERROR: permission denied'),
        ('web_scan', {}, ''),
        ('file_read', {'path': '/etc/passwd'}, 'No such file or directory'),
        ('code_run', {}, 'Success! Task done.'),
        ('code_run', {}, 'Traceback (most recent call last): ValueError'),
        ('web_execute_js', {}, 'timeout exceeded'),
        ('file_read', {}, '{"data": "ok"}'),
        ('code_run', {}, ''),
        ('code_run', {}, 'ERROR: timeout'),
        ('code_run', {}, 'ERROR: timeout'),
    ]
    
    for tool, args, result in test_cases:
        anomaly = d.analyze(tool, args, result)
        status = f"  异常: {anomaly}" if anomaly else "  正常"
        print(f"[{tool:<15}] {result[:50]:<50} {status}")
    
    print("\n=== 摘要 ===")
    print(json.dumps(d.get_summary(), ensure_ascii=False, indent=2))
    
    print("\n=== 注入提示 ===")
    print(d.generate_prompt_suffix() or "(无)")


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        _demo()
    else:
        print("StepDetector: MASC实时步骤检测器")
        print(f"  可检测模式: empty_result, error_message, permission_denied, timeout, truncated_output, file_not_found, empty_scan, parse_error, consecutive_failures")
        print(f"  用法: python tools/step_detector.py --test  # 自检演示")
