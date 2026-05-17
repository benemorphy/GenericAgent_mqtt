"""
测试: mqtt_bbs 持久化集成 — 单元测试 + 集成测试 + E2E

遵循 mqtt_testing 技能模式:
- 使用 pytest 编写测试
- Mock 隔离外部依赖
- 覆盖核心逻辑和边界情况
- 集成测试验证组件间协作
"""

import sys, os, json, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import patch, MagicMock
from mqtt_bbs.client import TaskOutput, TaskMessage
 

...[Truncated]...
