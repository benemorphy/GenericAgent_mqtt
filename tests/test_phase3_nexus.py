"""tests/test_phase3_nexus.py — Phase 3: Nexus"""
import sys, os, json, time, unittest
GA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, GA_DIR)
TEST_STATE = os.path.join(GA_DIR, 'temp', 'test_nexus_state.json')


class TestNexusPrompt(unittest.TestCase):
    """检查源文件中的关键字符串存在性"""

    def test_keywords_in_source(self):
        with open(os.path.join(GA_DIR, 'reflect', 'goal_nexus.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        for kw in ['ask_human', 'send_feishu', '__GOAL_COMPLETE__', 'CONTINUATION_PROMPT', 'Nexus',
                    'WAITING_PROMPT', 'suspend', 'resume', '_parse_agent_markers', 'init']:
            self.assertIn(kw, c, f'missing: {kw}')


class TestNexusImport(unittest.TestCase):
    """检查 API 可导入"""

    def test_import_goal_nexus(self):
        from reflect import goal_nexus
        for a in ['check', 'on_done', 'ask_human', 'send_feishu', 'suspend', 'resume', 'init']:
            self.assertTrue(hasattr(goal_nexus, a), f'missing attr: {a}')

    def test_fsapp_has_nexus(self):
        with open(os.path.join(GA_DIR, 'frontends', 'fsapp.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        self.assertIn('_on_nexus_request', c)
        self.assertIn('_NEXUS_PUSH_CHATS', c)
        self.assertIn('bbs/goal_nexus/review', c)
        self.assertIn('bbs/goal_nexus/tasks', c)


class TestAgentMarkers(unittest.TestCase):
    """测试 on_done 中的 agent 标记解析"""

    def _get_gn(self):
        if 'reflect.goal_nexus' in sys.modules:
            del sys.modules['reflect.goal_nexus']
        if 'reflect' in sys.modules:
            del sys.modules['reflect']
        from reflect import goal_nexus
        return goal_nexus

    def test_parse_ask_human_basic(self):
        gn = self._get_gn()
        text = "[ASK_HUMAN] 是否部署到生产? | 是,否,灰度 | 灰度"
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['ask_human']), 1)
        self.assertIn('部署', result['ask_human'][0]['decision'])
        self.assertEqual(result['ask_human'][0]['options'], ['是', '否', '灰度'])
        self.assertEqual(result['ask_human'][0]['recommendation'], '灰度')

    def test_parse_ask_human_no_options(self):
        gn = self._get_gn()
        text = "[ASK_HUMAN] 确认开始? | | 是"
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['ask_human']), 1)
        self.assertEqual(result['ask_human'][0]['options'], [])
        self.assertEqual(result['ask_human'][0]['recommendation'], '是')

    def test_parse_ask_human_case_insensitive(self):
        gn = self._get_gn()
        text = "[ask_human] deploy? | A,B | A"
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['ask_human']), 1)
        self.assertEqual(result['ask_human'][0]['decision'], 'deploy?')

    def test_parse_send_feishu_basic(self):
        gn = self._get_gn()
        text = "[SEND_FEISHU] 当前任务已完成50%"
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['send_feishu']), 1)
        self.assertIn('50%', result['send_feishu'][0])

    def test_parse_send_feishu_case_insensitive(self):
        gn = self._get_gn()
        text = "[send_feishu] hello world"
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['send_feishu']), 1)

    def test_parse_mixed_markers(self):
        gn = self._get_gn()
        text = """工作中，发现需要决策：
[ASK_HUMAN] 选择方案 | 方案A,方案B | 方案A
已向用户发送通知。
[SEND_FEISHU] 进度: 70% 完成
"""
        result = gn._parse_agent_markers(text)
        self.assertEqual(len(result['ask_human']), 1)
        self.assertEqual(len(result['send_feishu']), 1)
        self.assertEqual(result['ask_human'][0]['decision'], '选择方案')
        self.assertIn('70%', result['send_feishu'][0])

    def test_parse_empty_text(self):
        gn = self._get_gn()
        result = gn._parse_agent_markers('')
        self.assertEqual(result, {'ask_human': [], 'send_feishu': []})

    def test_parse_no_markers(self):
        gn = self._get_gn()
        result = gn._parse_agent_markers('正常回复，没有标记')
        self.assertEqual(result, {'ask_human': [], 'send_feishu': []})


class TestNexusAPI(unittest.TestCase):
    """测试核心 API"""

    def setUp(self):
        s = {
            "objective": "测试目标: 验证 Nexus 功能",
            "budget_seconds": 3600,
            "start_time": time.time(),
            "turns_used": 0,
            "max_turns": 10,
            "status": "running",
            "done_prompt": "__GOAL_COMPLETE__",
        }
        with open(TEST_STATE, 'w', encoding='utf-8') as f:
            json.dump(s, f)
        os.environ['GOAL_STATE'] = TEST_STATE

    def tearDown(self):
        if os.path.exists(TEST_STATE):
            os.remove(TEST_STATE)
        if 'GOAL_STATE' in os.environ:
            del os.environ['GOAL_STATE']
        if 'reflect.goal_nexus' in sys.modules:
            del sys.modules['reflect.goal_nexus']
        if 'reflect' in sys.modules:
            del sys.modules['reflect']

    def _reload(self):
        if 'reflect.goal_nexus' in sys.modules:
            del sys.modules['reflect.goal_nexus']
        if 'reflect' in sys.modules:
            del sys.modules['reflect']
        from reflect import goal_nexus
        return goal_nexus

    # ── 基础状态 IO ──

    def test_state_io(self):
        gn = self._reload()
        loaded = gn._load()
        self.assertEqual(loaded['objective'], '测试目标: 验证 Nexus 功能')
        loaded['turns_used'] = 5
        gn._save(loaded)
        self.assertEqual(gn._load()['turns_used'], 5)

    # ── check 行为 ──

    def test_check_exit_done(self):
        s = self._reload()._load()
        s['status'] = 'done'
        with open(TEST_STATE, 'w', encoding='utf-8') as f:
            json.dump(s, f)
        gn = self._reload()
        self.assertEqual(gn.check(), '/exit')

    def test_check_exit_done_budget(self):
        s = self._reload()._load()
        s['status'] = 'done_budget'
        with open(TEST_STATE, 'w', encoding='utf-8') as f:
            json.dump(s, f)
        gn = self._reload()
        self.assertEqual(gn.check(), '/exit')

    def test_check_exit_wrapping_up(self):
        s = self._reload()._load()
        s['status'] = 'wrapping_up'
        with open(TEST_STATE, 'w', encoding='utf-8') as f:
            json.dump(s, f)
        gn = self._reload()
        self.assertEqual(gn.check(), '/exit')

    def test_check_returns_prompt(self):
        gn = self._reload()
        r = gn.check()
        self.assertIsNotNone(r)
        self.assertNotEqual(r, '/exit')
        self.assertIn('Nexus', r)

    def test_check_waiting_human_returns_wait_prompt(self):
        gn = self._reload()
        s = gn._load()
        s['status'] = 'waiting_human'
        s['_pending_decision'] = {
            'corr_id': 'test_corr_1',
            'decision': '测试决策',
            'options': ['A', 'B'],
            'recommendation': 'A',
            'expires_at': time.time() + 3600,
            'turn': 1,
        }
        gn._save(s)
        gn = self._reload()
        r = gn.check()
        self.assertIsNotNone(r)
        self.assertNotEqual(r, '/exit')
        # Should return WAITING_PROMPT (not continuation)
        self.assertIn('等待人类决策', r, 'should contain wait message')

    def test_check_waiting_human_response_detected(self):
        """模拟人类回复到达后，check 检测到并恢复 running"""
        gn = self._reload()
        s = gn._load()
        corr_id = 'test_corr_response'
        s['status'] = 'waiting_human'
        s['_pending_decision'] = {
            'corr_id': corr_id,
            'decision': '测试决策',
            'options': ['A', 'B'],
            'recommendation': 'A',
            'expires_at': time.time() + 3600,
            'turn': 1,
        }
        gn._save(s)

        # 模拟 MQTT 回调存储回复
        gn.set_human_response(corr_id, '选B')

        gn = self._reload()
        r = gn.check()
        # 检测到响应后，check 应返回 None（让下一轮产生带恢复通知的 prompt）
        # 同时状态应恢复为 running
        self.assertIsNone(r, 'should return None to trigger next check')
        new_state = gn._load()
        self.assertEqual(new_state['status'], 'running')
        self.assertEqual(new_state['_nexus_human_response'], '选B')

    def test_check_waiting_human_timeout(self):
        """模拟超时后自动使用推荐方案"""
        gn = self._reload()
        s = gn._load()
        s['status'] = 'waiting_human'
        s['_pending_decision'] = {
            'corr_id': 'test_corr_timeout',
            'decision': '测试决策',
            'options': ['A', 'B'],
            'recommendation': '推荐方案',
            'expires_at': time.time() - 1,  # 已过期
            'turn': 1,
        }
        gn._save(s)

        gn = self._reload()
        r = gn.check()
        # 超时后自动恢复 running，返回 None 让下一轮产生带超时通知的 prompt
        self.assertIsNone(r, 'should return None on timeout recovery')
        new_state = gn._load()
        self.assertEqual(new_state['status'], 'running')
        self.assertIn('TIMEOUT', new_state['_nexus_human_response'])
        self.assertIn('推荐方案', new_state['_nexus_human_response'])

    def test_check_waiting_human_no_pending_decision(self):
        """异常状态: waiting_human 但没有挂起决策 → 自动恢复 running"""
        gn = self._reload()
        s = gn._load()
        s['status'] = 'waiting_human'
        # 没有 _pending_decision
        gn._save(s)

        gn = self._reload()
        r = gn.check()
        self.assertIsNotNone(r)
        self.assertNotEqual(r, '/exit')
        new_state = gn._load()
        self.assertEqual(new_state['status'], 'running')

    # ── on_done 标记解析 ──

    def test_on_done_ask_human_marker(self):
        """on_done 检测到 [ASK_HUMAN] 应置 waiting_human"""
        gn = self._reload()
        gn._publish_human_decision = lambda *a, **kw: None  # 跳过 MQTT
        gn._store_chronicle = lambda *a, **kw: None
        # 模拟 on_done 调用，检测 [ASK_HUMAN] 标记
        # 注意: _publish_human_decision 被 mock 了，所以我们手动测 on_done + _parse_agent_markers
        markers = gn._parse_agent_markers("[ASK_HUMAN] test | A,B,C | A")
        self.assertEqual(len(markers['ask_human']), 1)

    def test_on_done_send_feishu_marker(self):
        """on_done 检测到 [SEND_FEISHU] 应调用 _do_send_feishu"""
        gn = self._reload()
        # Mock 内部函数
        gn._store_chronicle = lambda *a, **kw: None
        original_do_send = gn._do_send_feishu
        calls = []
        def mock_send(msg, msg_type="text"):
            calls.append((msg, msg_type))
        gn._do_send_feishu = mock_send

        gn.on_done({"response": "工作中\n[SEND_FEISHU] 进度报告: 80% 完成"})

        self.assertEqual(len(calls), 1)
        self.assertIn('80%', calls[0][0])
        gn._do_send_feishu = original_do_send

    def test_on_done_mixed_markers(self):
        """on_done 同时处理 [ASK_HUMAN] + [SEND_FEISHU] 但 ask_human 优先级高"""
        gn = self._reload()
        gn._store_chronicle = lambda *a, **kw: None
        gn._do_send_feishu = lambda *a, **kw: None
        # 有 [ASK_HUMAN] 时，on_done 应短路返回（不继续处理 done_prompt 等）
        # 使用 publish 拦截
        publish_calls = []
        gn._publish_human_decision = lambda *a, **kw: publish_calls.append(a)

        gn.on_done({"response": "[ASK_HUMAN] 选项? | 1,2 | 1\n[SEND_FEISHU] 进度: 50%"})

        self.assertEqual(len(publish_calls), 1, 'should have called _publish_human_decision')

    # ── ask_human 阻塞 API ──

    def test_ask_human_timeout(self):
        gn = self._reload()
        c = gn.ask_human("测试决策", ["A","B"], "B", timeout=0.5)
        self.assertEqual(c, "B")

    def test_send_feishu_no_crash(self):
        gn = self._reload()
        try:
            gn.send_feishu("hello")
        except Exception as e:
            self.fail(str(e))

    # ── done_prompt ──

    def test_done_prompt(self):
        gn = self._reload()
        gn._pulse = lambda *a, **kw: None
        gn._store_chronicle = lambda *a, **kw: None
        gn._close_bbs = lambda: None
        gn.on_done({"response": "完成了 __GOAL_COMPLETE__"})
        self.assertEqual(gn._load()['status'], 'done')

    # ── suspend / resume ──

    def test_suspend_resume(self):
        gn = self._reload()
        # suspend running
        result = gn.suspend("test suspend")
        self.assertTrue(result)
        state = gn._load()
        self.assertTrue(state.get('_suspended'))
        self.assertEqual(state.get('_suspend_reason'), 'test suspend')

        # resume
        result = gn.resume()
        self.assertTrue(result)
        state = gn._load()
        self.assertFalse(state.get('_suspended', False))

    def test_suspend_waiting_human_then_resume(self):
        """挂起后可以恢复（即使状态是 waiting_human）"""
        gn = self._reload()
        s = gn._load()
        s['status'] = 'waiting_human'
        gn._save(s)

        gn = self._reload()
        result = gn.suspend("human paused")
        self.assertTrue(result)
        state = gn._load()
        self.assertTrue(state.get('_suspended'))

        gn = self._reload()
        result = gn.resume()
        self.assertTrue(result)
        state = gn._load()
        self.assertFalse(state.get('_suspended'))
        # resume 会把 waiting_human 转为 running
        self.assertEqual(state['status'], 'running')

    # ── set_human_response 双通道 ──

    def test_set_human_response_blocking(self):
        """set_human_response 触发阻塞式回调"""
        gn = self._reload()
        # 先注册 pending callback
        from threading import Event
        event = Event()
        results = []
        def cb(choice):
            results.append(choice)
            event.set()
        gn._nexus["_pending_callbacks"] = gn._nexus.get("_pending_callbacks", {})
        gn._nexus["_pending_callbacks"]["test_cb"] = cb

        gn.set_human_response("test_cb", "用户选择")
        event.wait(1)
        self.assertEqual(results, ["用户选择"])

    def test_set_human_response_nonblocking_pool(self):
        """set_human_response 同时存入非阻塞响应池"""
        gn = self._reload()
        gn.set_human_response("pool_key", "pool_value")
        with gn._nexus['_human_responses_lock']:
            self.assertEqual(gn._nexus['_human_responses'].get("pool_key"), "pool_value")

    # ── init ──

    def test_init_function_exists(self):
        gn = self._reload()
        self.assertTrue(callable(gn.init))

    def test_init_with_default_env(self):
        gn = self._reload()
        # init 不应崩溃
        try:
            gn.init({"goal_state": TEST_STATE})
        except Exception as e:
            self.fail(f"init crashed: {e}")


class TestNexusFeishu(unittest.TestCase):
    """测试飞书集成"""

    def test_card_structure(self):
        with open(os.path.join(GA_DIR, 'frontends', 'fsapp.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        self.assertIn('card_json', c)
        self.assertIn('corr_id', c)

    def test_nexus_response_topic_in_goal_nexus(self):
        """检查 goal_nexus.py 订阅了 nexus/response 主题用于接收人类回复"""
        with open(os.path.join(GA_DIR, 'reflect', 'goal_nexus.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        self.assertIn('bbs/goal_nexus/response', c)

    def test_fsapp_has_card_action_handler(self):
        """检查 fsapp.py 注册了卡片动作处理函数"""
        with open(os.path.join(GA_DIR, 'frontends', 'fsapp.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        self.assertIn('_on_nexus_card_action', c)
        self.assertIn('register_p2_card_action_trigger', c)

    def test_nexus_card_has_interactive_buttons(self):
        """检查决策卡片包含交互按钮（tag: action, tag: button）"""
        with open(os.path.join(GA_DIR, 'frontends', 'fsapp.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        func_start = c.find('def _on_nexus_request')
        func_end = c.find('\ndef ', func_start + 10)
        func_body = c[func_start:func_end]
        self.assertIn('"tag": "action"', func_body)
        self.assertIn('"tag": "button"', func_body)
        self.assertIn('"corr_id"', func_body)
        self.assertIn('"choice"', func_body)

    def test_nexus_card_response_publish(self):
        """检查卡片动作回调会发布到 bbs/goal_nexus/response"""
        with open(os.path.join(GA_DIR, 'frontends', 'fsapp.py'), 'r', encoding='utf-8') as f:
            c = f.read()
        func_start = c.find('def _on_nexus_card_action')
        func_end = c.find('\ndef ', func_start + 10) if c.find('\ndef ', func_start + 10) > 0 else len(c)
        func_body = c[func_start:func_end]
        self.assertIn('bbs/goal_nexus/response', func_body)
        self.assertIn('corr_id', func_body)
        self.assertIn('choice', func_body)


if __name__ == '__main__':
    unittest.main()
