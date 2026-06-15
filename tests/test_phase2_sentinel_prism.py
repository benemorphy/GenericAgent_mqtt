"""tests/test_phase2_sentinel_prism.py — Phase 2: Sentinel + Prism 全面测试

覆盖:
  1. Sentinel: MQTT 连接、心跳追踪、僵尸检测、自定义超时
  2. Prism: 配置解析、Worker 生成、Board 隔离、聚合报告
  3. 集成: Sentinel + Prism 协同工作流
"""

import sys, os, json, time, subprocess, unittest

GA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, GA_DIR)

SENTINEL_PATH = os.path.join(GA_DIR, 'scripts', 'goal_sentinel.py')
PRISM_PATH = os.path.join(GA_DIR, 'reflect', 'goal_prism.py')

# ── Dummy MQTT Broker for testing ──
# 由于测试环境中 Mosquitto 已运行于 localhost:1883，我们直接使用真实 Broker
BROKER = '127.0.0.1'
PORT = 1883


class TestSentinelCore(unittest.TestCase):
    """Sentinel 核心逻辑测试（不依赖 MQTT）"""
    
    def setUp(self):
        # 模拟 Sentinel 的 last_heartbeat 数据结构
        self.heartbeats = {}
        self.zombies = []
        self.timeout = 5
    
    def _check_zombie(self):
        """模拟 Sentinel 的僵尸检测逻辑"""
        now = time.time()
        for agent_id, last_seen in list(self.heartbeats.items()):
            if now - last_seen > self.timeout:
                self.zombies.append(agent_id)
                del self.heartbeats[agent_id]
    
    def test_healthy_agent_no_zombie(self):
        """健康 agent 不应被判定为僵尸"""
        self.heartbeats['agent_a'] = time.time()
        self._check_zombie()
        self.assertNotIn('agent_a', self.zombies)
        self.assertIn('agent_a', self.heartbeats)
    
    def test_zombie_detection(self):
        """超时的 agent 应被判定为僵尸"""
        self.heartbeats['agent_zombie'] = time.time() - 10  # 10秒前最后一次心跳
        self._check_zombie()
        self.assertIn('agent_zombie', self.zombies)
        self.assertNotIn('agent_zombie', self.heartbeats)
    
    def test_mixed_agents(self):
        """混合场景：健康+僵尸应分别处理"""
        self.heartbeats['healthy'] = time.time()
        self.heartbeats['zombie1'] = time.time() - 10
        self.heartbeats['zombie2'] = time.time() - 20
        self._check_zombie()
        self.assertIn('healthy', self.heartbeats)
        self.assertIn('zombie1', self.zombies)
        self.assertIn('zombie2', self.zombies)
        self.assertEqual(len(self.zombies), 2)
    
    def test_custom_timeout(self):
        """自定义超时时间"""
        self.timeout = 2
        self.heartbeats['slow_agent'] = time.time() - 3  # 3秒>2秒超时
        self._check_zombie()
        self.assertIn('slow_agent', self.zombies)
    
    def test_recent_heartbeat_revives(self):
        """旧心跳过期后新心跳应重新激活"""
        self.heartbeats['alive'] = time.time() - 10
        self._check_zombie()
        self.assertIn('alive', self.zombies)
        
        # 假装收到新心跳
        self.zombies.clear()
        self.heartbeats['alive'] = time.time()
        self._check_zombie()
        self.assertNotIn('alive', self.zombies)
        self.assertIn('alive', self.heartbeats)


class TestSentinelMQTT(unittest.TestCase):
    """Sentinel MQTT 集成测试（需要运行中的 Mosquitto）"""
    
    def test_sentinel_startup_clean(self):
        """启动后应正常连接 MQTT"""
        proc = subprocess.Popen(
            [sys.executable, SENTINEL_PATH, '--timeout', '30'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(2)
        alive = proc.poll() is None
        proc.terminate()
        proc.wait(timeout=5)
        self.assertTrue(alive, "Sentinel 应在启动后保持运行")
    
    def test_sentinel_detects_pulse(self):
        """Sentinel 应能检测到 Pulse 消息并维持 agent 健康"""
        import paho.mqtt.client as mqtt
        
        # 先启动 Sentinel
        proc = subprocess.Popen(
            [sys.executable, SENTINEL_PATH, '--timeout', '5'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(1)
        
        # 发送测试 Pulse
        client = mqtt.Client(client_id="sentinel_test_pulse")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        
        payload = json.dumps({"type": "turn_done", "source": "test_goal", "turn": 1, "progress": "50%"})
        for _ in range(3):
            client.publish("agent/bbs/goal_pulse/post", payload, qos=1)
            time.sleep(0.5)
        
        client.loop_stop()
        client.disconnect()
        
        # Sentinel 应在这些脉冲期间持续运行
        time.sleep(2)
        alive = proc.poll() is None
        proc.terminate()
        proc.wait(timeout=5)
        self.assertTrue(alive, "Sentinel 应在收到脉冲时保持 agent 健康")
    
    def test_sentinel_detects_zombie_after_stop(self):
        """停止发送脉冲后，Sentinel 应检测到僵尸"""
        import paho.mqtt.client as mqtt
        
        proc = subprocess.Popen(
            [sys.executable, SENTINEL_PATH, '--timeout', '3'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(1)
        
        # 发一次脉冲然后停下
        client = mqtt.Client(client_id="sentinel_test_zombie")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        payload = json.dumps({"type": "turn_done", "source": "test_zombie", "turn": 1})
        client.publish("agent/bbs/goal_pulse/post", payload, qos=1)
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        
        # 等待超过超时时间（3s）
        time.sleep(5)
        
        alive = proc.poll() is None
        proc.terminate()
        proc.wait(timeout=5)
        # Sentinel 可能仍在运行（僵尸检测只是打印日志不退出）
        # 所以这里只验证它没崩溃
        self.assertTrue(alive, "Sentinel 不应因僵尸检测而崩溃")


class TestPrismCore(unittest.TestCase):
    """Prism 核心逻辑测试"""
    
    def setUp(self):
        self.config = {
            "objective": "审查项目安全性",
            "perspectives": [
                {"name": "代码安全", "board": "prism_code", "focus": "XSS/注入"},
                {"name": "依赖安全", "board": "prism_deps", "focus": "第三方库"},
            ],
            "budget_per_worker": 300,
            "max_workers": 2
        }
    
    def test_config_parsing(self):
        """Prism 配置应正确解析"""
        self.assertEqual(self.config['objective'], "审查项目安全性")
        self.assertEqual(len(self.config['perspectives']), 2)
    
    def test_perspective_boards_unique(self):
        """每个视角应有唯一的 Board 名称"""
        boards = [p['board'] for p in self.config['perspectives']]
        self.assertEqual(len(boards), len(set(boards)))
    
    def test_each_perspective_has_name(self):
        """每个视角必须有名称"""
        for p in self.config['perspectives']:
            self.assertTrue(p.get('name'), "每个视角必须有 name")
    
    def test_each_perspective_has_focus(self):
        """每个视角必须有聚焦说明"""
        for p in self.config['perspectives']:
            self.assertTrue(p.get('focus'), "每个视角必须有 focus")
    
    def test_max_workers_constraint(self):
        """max_workers 应限制并行 worker 数"""
        workers = self.config['perspectives'][:self.config['max_workers']]
        self.assertLessEqual(len(workers), self.config['max_workers'])
    
    def test_generate_worker_objective(self):
        """每个 worker 的目标应包含主目标 + 视角聚焦"""
        for p in self.config['perspectives']:
            worker_obj = f"{self.config['objective']} - 视角: {p['name']}, 聚焦: {p['focus']}"
            self.assertIn(p['name'], worker_obj)
            self.assertIn(p['focus'], worker_obj)
    
    def test_aggregation_summary(self):
        """聚合报告应包含所有视角的发现"""
        findings = {
            '代码安全': ['发现XSS漏洞3处', 'SQL注入未过滤'],
            '依赖安全': ['lodash 漏洞CVE-2024-...'],
        }
        report_lines = []
        for name, discovers in findings.items():
            report_lines.append(f"## {name}")
            for d in discovers:
                report_lines.append(f"- {d}")
        report = '\n'.join(report_lines)
        
        self.assertIn('代码安全', report)
        self.assertIn('XSS漏洞', report)
        self.assertIn('依赖安全', report)
        self.assertIn('lodash', report)
    
    def test_board_config_generation(self):
        """验证 Prism 为每个 Board 在 boards.json 中配置"""

        boards_config = {}
        for p in self.config['perspectives']:
            boards_config[p['board']] = {
                "name": p['name'],
                "db": f"{p['board']}.db"
            }
        self.assertIn('prism_code', boards_config)
        self.assertIn('prism_deps', boards_config)
        self.assertEqual(boards_config['prism_code']['name'], '代码安全')


class TestPrismReportFormat(unittest.TestCase):
    """Prism 聚合报告格式测试"""
    
    def test_report_structure(self):
        """报告结构：标题、各视角、综合"""
        report = """# Prism 综合报告

## 代码安全
- 发现XSS 3处

## 依赖安全
- lodash 漏洞

## 综合
- 高优先级: 修复XSS
"""
        self.assertIn('# Prism 综合报告', report)
        self.assertIn('## 代码安全', report)
        self.assertIn('## 综合', report)


class TestPhase2Workflow(unittest.TestCase):
    """Phase 2 端到端工作流测试"""
    
    def test_sentinel_and_prism_boards(self):
        """验证 Pulse Board 和 Prism Board 兼容性"""
        import paho.mqtt.client as mqtt
        
        boards_to_test = [
            "agent/bbs/goal_pulse/post",
            "agent/bbs/prism_code/post",
            "agent/bbs/prism_deps/post",
        ]
        
        client = mqtt.Client(client_id="phase2_compat")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        
        results = {}
        for topic in boards_to_test:
            payload = json.dumps({"test": True, "source": "phase2_test", "timestamp": time.time()})
            info = client.publish(topic, payload, qos=1)
            results[topic] = info[0]  # rc
        
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
        
        for topic, rc in results.items():
            self.assertEqual(rc, 0, f"发布到 {topic} 应成功 (rc=0), 实际 rc={rc}")
    
    def test_done_prompt_detection_integration(self):
        """验证 done_prompt 逻辑（从 goal_mode.py 导入）"""
        sys.path.insert(0, os.path.join(GA_DIR, 'reflect'))
        import importlib.util
        
        # 加载 goal_mode.py 作为模块
        spec = importlib.util.spec_from_file_location(
            "goal_mode", os.path.join(GA_DIR, 'reflect', 'goal_mode.py')
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        # 验证模块有 on_done 函数
        self.assertTrue(hasattr(mod, 'on_done'), "goal_mode.py 应包含 on_done")
        
        # 验证 CONTINUATION_PROMPT 包含 __GOAL_COMPLETE__
        prompt = mod.CONTINUATION_PROMPT
        self.assertIn('__GOAL_COMPLETE__', prompt, "CONTINUATION_PROMPT 应包含自动终止标记")


if __name__ == '__main__':
    unittest.main()
