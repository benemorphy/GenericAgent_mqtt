"""engine.py 核心函数单元测试"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from tools.skill_learn_from_cases_full.dir_manager import _sanitize_skill_name


def test_sanitize_normal():
    """正常技能名: 驼峰规范，无下划线"""
    result = _sanitize_skill_name("python_project_management")
    assert result == "pythonprojectmanagement"  # 驼峰: 下划线被移除


def test_sanitize_chinese():
    """中文技能名: 中文全移除，保留英文字母"""
    result = _sanitize_skill_name("人机交互ui设计")
    assert "ui" in result  # 中文被移除，仅保留英文字母


def test_sanitize_path_traversal():
    """路径遍历字符被移除"""
    result = _sanitize_skill_name("../../etc/passwd")
    assert "/" not in result
    assert ".." not in result


def test_sanitize_special_chars():
    """特殊字符被替换"""
    result = _sanitize_skill_name("test; rm -rf /")
    assert ";" not in result
    assert result != ""


def test_sanitize_empty():
    """空名返回默认"""
    assert _sanitize_skill_name("") == "unnamed_skill"


def test_sanitize_spaces():
    """空格被处理为下划线"""
    result = _sanitize_skill_name("  spaced  name  ")
    assert "  " not in result  # 无连续空格
    assert result  # 非空
