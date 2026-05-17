"""env_detector 单元测试"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from tools.skill_learn_from_cases_full.env_detector import _port_open


def test_port_open_localhost():
    """常见端口检测"""
    result = _port_open("127.0.0.1", 8090) or _port_open("127.0.0.1", 7687)
    assert isinstance(result, bool)


def test_port_open_invalid():
    """无效主机返回 False 或抛异常"""
    import socket
    try:
        result = _port_open("256.256.256.256", 9999)
        assert result is False
    except socket.gaierror:
        pass  # 某些环境会直接抛地址解析异常
