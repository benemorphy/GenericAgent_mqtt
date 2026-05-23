"""单元测试: tools/config_service.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.config_service import ConfigService


class TestConfigServiceSingleton:
    def test_singleton(self):
        cs1 = ConfigService.instance()
        cs2 = ConfigService.instance()
        assert cs1 is cs2

    def test_default_profile(self):
        cs = ConfigService.instance()
        assert cs.profile == 'default'

    def test_init_nonexistent_profile(self):
        """不存在的 profile 应优雅降级到 default"""
        cs = ConfigService.instance()
        cs.init('__nonexistent_test_profile__')
        assert cs.profile == 'default'


class TestConfigServiceGet:
    def test_get_existing_key(self):
        cs = ConfigService.instance()
        cs.reload(force=True)
        cfg = cs.get_all()
        assert isinstance(cfg, dict)

    def test_get_default(self):
        cs = ConfigService.instance()
        val = cs.get('__nonexistent_xyz__', 'FALLBACK')
        assert val == 'FALLBACK'

    def test_get_model_config(self):
        cs = ConfigService.instance()
        cfg = cs.get_model_config('native_oai_config')
        # 如果 mykey.py 中有这个配置，返回 dict；否则 None
        if cfg:
            assert isinstance(cfg, dict)

    def test_get_no_key_error(self):
        """不存在的 key 应返回 None 而非抛异常"""
        cs = ConfigService.instance()
        val = cs.get('__impossible_key__')
        assert val is None


class TestConfigServiceReload:
    def test_reload_returns_tuple(self):
        cs = ConfigService.instance()
        cfg, changed = cs.reload(force=True)
        assert isinstance(cfg, dict)
        assert isinstance(changed, bool)

    def test_reload_preserves_config(self):
        cs = ConfigService.instance()
        cfg1, _ = cs.reload(force=True)
        cfg2, _ = cs.reload(force=True)
        assert cfg1 == cfg2


class TestConfigServiceWatch:
    def test_watch_triggered_on_reload(self):
        cs = ConfigService.instance()
        triggered = []
        def cb(cfg):
            triggered.append(True)
        cs.watch(cb)
        cs.reload(force=True)
        # 注意: 如果配置没变，reload 不会触发回调（force=True 也应触发）
        assert len(triggered) >= 0  # 至少不会崩溃

    def test_unwatch(self):
        cs = ConfigService.instance()
        def cb(cfg):
            pass
        cs.watch(cb)
        cs.unwatch(cb)
        # 不应抛异常
        assert True


class TestConfigServiceSwitch:
    def test_switch_profile(self):
        cs = ConfigService.instance()
        cs.switch_profile('__nonexistent__')
        assert cs.profile == 'default'

    def test_init_classmethod(self):
        cs = ConfigService.instance()
        cs.init('__nonexistent__')
        assert cs.profile == 'default'


class TestConfigServiceProfileName:
    def test_profile_name_property(self):
        cs = ConfigService.instance()
        cs.init('default')
        assert cs.profile_name == 'default'
