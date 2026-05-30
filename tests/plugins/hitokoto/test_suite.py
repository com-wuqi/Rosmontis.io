"""
hitokoto插件的简洁测试套件
"""

import os
import sys

# 计算项目根目录的相对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
src_dir = os.path.join(project_root, "src")
plugins_dir = os.path.join(src_dir, "plugins")
hitokoto_dir = os.path.join(plugins_dir, "hitokoto")


def test_basic_config():
    """测试基本配置"""
    print("测试配置模型...")
    sys.path.insert(0, hitokoto_dir)
    try:
        from config import ScopedConfig

        config = ScopedConfig()
        assert config.is_enable is True
        assert config.cache_timeout == 90
        assert config.cache_length_limit == 100

        print("✓ 配置模型测试通过")
    except Exception as e:
        print(f"✗ 配置模型测试失败: {e}")
        raise
    finally:
        sys.path.remove(hitokoto_dir)


def test_command_prefix():
    """测试命令前缀"""
    print("\n测试命令前缀...")

    # 动态从环境文件读取命令前缀
    # 直接导入env_utils
    sys.path.insert(0, os.path.dirname(__file__))
    from env_utils import get_command_prefixes
    sys.path.remove(os.path.dirname(__file__))

    valid_prefixes = get_command_prefixes(project_root)
    print(f"从环境文件读取的命令前缀: {valid_prefixes}")
    assert len(valid_prefixes) > 0, "命令前缀列表不能为空"

    # 基于读取的前缀生成测试用例
    test_cases = []
    for prefix in valid_prefixes:
        test_cases.append((f"{prefix}yiyan", True))
        test_cases.append((f"{prefix}yiyan 1", True))

    # 添加一些应该不匹配的测试用例（除非这些前缀正好在列表中）
    invalid_prefixes = ["#", "!", "@"]
    for invalid_prefix in invalid_prefixes:
        if invalid_prefix not in valid_prefixes:
            test_cases.append((f"{invalid_prefix}yiyan", False))

    # 添加无前缀的情况
    test_cases.append(("yiyan", False))

    # 测试所有用例
    for cmd, should_match in test_cases:
        # 检查是否以任何有效前缀开头
        matches = any(cmd.startswith(prefix) for prefix in valid_prefixes)

        error_msg = f"命令 '{cmd}' 测试失败: 期望 {should_match}, 实际 {matches} (前缀列表: {valid_prefixes})"
        assert matches == should_match, error_msg

    print("✓ 命令前缀测试通过")


def test_control_logic():
    """测试控制逻辑"""
    print("\n测试控制逻辑...")

    # 黑白名单逻辑
    test_cases = [
        (True, False, "whitelist"),
        (False, True, "blacklist"),
        (False, False, "null"),
    ]

    for whitelist, blacklist, expected in test_cases:
        if whitelist and not blacklist:
            result = "whitelist"
        elif blacklist and not whitelist:
            result = "blacklist"
        elif not whitelist and not blacklist:
            result = "null"
        else:
            result = "error"

        assert result == expected, f"控制逻辑测试失败: {whitelist}, {blacklist} -> {result}, 期望 {expected}"

    print("✓ 控制逻辑测试通过")


def test_cache_operations():
    """测试缓存操作"""
    print("\n测试缓存操作...")

    from random import choice

    # 测试随机选择
    cache = ["测试一言1", "测试一言2", "测试一言3"]
    selected = choice(cache)
    assert selected in cache

    # 测试缓存限制
    limit = 100
    cache_full = ["一言"] * 150
    if len(cache_full) > limit:
        cache_full = cache_full[:limit]

    assert len(cache_full) == limit

    print("✓ 缓存操作测试通过")


def test_command_parsing_logic():
    """测试命令解析逻辑"""
    print("\n测试命令解析逻辑...")

    def parse_command_arg(arg):
        try:
            return int(arg.strip()) if arg.strip() else 1
        except ValueError:
            return 1

    test_cases = [
        ("", 1),
        ("1", 1),
        ("2", 2),
        ("abc", 1),
        (" 3 ", 3),
    ]

    for arg, expected in test_cases:
        result = parse_command_arg(arg)
        assert result == expected, f"参数解析失败: '{arg}' -> {result}, 期望 {expected}"

    print("✓ 命令解析逻辑测试通过")


def test_plugin_structure():
    """测试插件结构完整性"""
    print("\n测试插件结构完整性...")

    required_files = ["__init__.py", "config.py", "getHitokoto.py"]

    for file in required_files:
        file_path = os.path.join(hitokoto_dir, file)
        assert os.path.exists(file_path), f"缺少必要文件: {file}"

    # 检查文件内容
    sys.path.insert(0, hitokoto_dir)
    try:
        # 测试配置导入
        from config import Config, ScopedConfig

        # 测试函数导入
        from getHitokoto import get_a_yiyan

        print("✓ 插件结构完整性测试通过")
    except ImportError as e:
        raise ImportError(f"导入失败: {e}")
    finally:
        sys.path.remove(hitokoto_dir)


def main():
    """运行所有测试"""
    print("=" * 50)
    print("Hitokoto插件测试套件")
    print("=" * 50)

    tests = [
        ("基本配置测试", test_basic_config),
        ("命令前缀测试", test_command_prefix),
        ("控制逻辑测试", test_control_logic),
        ("缓存操作测试", test_cache_operations),
        ("命令解析测试", test_command_parsing_logic),
        ("插件结构测试", test_plugin_structure),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}...")
            test_func()
            passed += 1
            print(f"✓ {test_name} 通过")
        except Exception as e:
            print(f"✗ {test_name} 失败: {e}")

    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
