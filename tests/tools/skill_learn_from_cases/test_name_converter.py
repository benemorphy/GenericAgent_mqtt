"""name_converter 单元测试"""
import sys, os
# Add project root to path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from tools.skill_learn_from_cases_full.name_converter import convert_name


def test_english_name():
    """纯英文名转驼峰"""
    assert convert_name("docker_compose_production") == "dockerComposeProduction"


def test_chinese_name():
    """中文名正确转驼峰（大小写不敏感检查）"""
    result = convert_name("小微贷款图像凭证鉴定")
    assert result == "imageVoucherVerificationMicroLoan"


def test_mixed_name():
    """中英文混合转驼峰"""
    result = convert_name("python项目管理")
    assert result == "pythonProjectManagement"


def test_ui_hci_name():
    """UI/HCI 专有名词"""
    result = convert_name("人机交互ui设计")
    assert result == "uiHciDesign"


def test_prototype_handoff():
    """原型+handoff 技能"""
    result = convert_name("原型设计handoff")
    assert "handoff" in result or "prototype" in result or "prototyp" in result


def test_path_traversal_safety():
    """路径遍历防护"""
    result = convert_name("../etc/passwd")
    assert "/" not in result and ".." not in result
    assert result  # 不应返回空


def test_empty_name():
    """空名容错"""
    assert convert_name("") == "unknown"
    assert convert_name(None) == "unknown"
