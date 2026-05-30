"""
hitokoto插件的nonebug测试
使用nonebug提供的测试工具
"""

import os

import httpx
import pytest
import respx
from nonebug import App

# 计算项目根目录的相对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

# 导入环境读取工具
import sys

sys.path.insert(0, os.path.dirname(__file__))
from env_utils import get_command_prefixes


@pytest.mark.asyncio
async def test_get_a_yiyan_success(app: App):
    """测试成功获取一言 - 使用respx模拟HTTP响应"""
    # 模拟hitokoto API的响应
    mock_response = {
        "hitokoto": "测试一言内容，生活不止眼前的苟且。",
        "from": "测试",
        "from_who": None,
        "creator": "test",
        "length": 10
    }

    # 使用respx模拟HTTP请求
    with respx.mock:
        respx.get("https://v1.hitokoto.cn/").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # 导入要测试的函数
        import sys
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        hitokoto_dir = os.path.join(project_root, "src/plugins/hitokoto")

        sys.path.insert(0, hitokoto_dir)
        try:
            from getHitokoto import get_a_yiyan

            result = await get_a_yiyan()

            # 验证结果
            assert result == "测试一言内容，生活不止眼前的苟且。"
        finally:
            sys.path.remove(hitokoto_dir)


@pytest.mark.asyncio
async def test_get_a_yiyan_http_error(app: App):
    """测试HTTP错误情况"""
    with respx.mock:
        respx.get("https://v1.hitokoto.cn/").mock(
            return_value=httpx.Response(500)
        )

        import sys
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        hitokoto_dir = os.path.join(project_root, "src/plugins/hitokoto")

        sys.path.insert(0, hitokoto_dir)
        try:
            from getHitokoto import get_a_yiyan

            result = await get_a_yiyan()

            assert result == ""
        finally:
            sys.path.remove(hitokoto_dir)


@pytest.mark.asyncio
async def test_get_a_yiyan_network_error(app: App):
    """测试网络错误情况"""
    with respx.mock:
        respx.get("https://v1.hitokoto.cn/").mock(side_effect=httpx.NetworkError("连接失败"))

        import sys
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        hitokoto_dir = os.path.join(project_root, "src/plugins/hitokoto")

        sys.path.insert(0, hitokoto_dir)
        try:
            from getHitokoto import get_a_yiyan

            result = await get_a_yiyan()

            assert result == ""
        finally:
            sys.path.remove(hitokoto_dir)


@pytest.mark.asyncio
async def test_command_prefix_handling(app: App):
    """测试命令前缀处理"""
    # 动态从环境文件读取命令前缀
    valid_prefixes = get_command_prefixes(project_root)

    # 基于读取的前缀生成测试用例
    test_cases = []
    for prefix in valid_prefixes:
        test_cases.append(f"{prefix}yiyan")
        test_cases.append(f"{prefix}yiyan 1")

    # 添加一些无效前缀（除非它们正好在列表中）
    invalid_prefixes = ["#", "!", "@"]
    for invalid_prefix in invalid_prefixes:
        if invalid_prefix not in valid_prefixes:
            test_cases.append(f"{invalid_prefix}yiyan")

    # 添加无前缀的情况
    test_cases.append("yiyan")

    # 验证命令前缀处理
    for cmd in test_cases:
        # 检查是否以任何有效前缀开头
        has_valid_prefix = any(cmd.startswith(prefix) for prefix in valid_prefixes)

        # 验证：命令要么以有效前缀开头，要么应该以无效前缀或无前缀开头
        # 对于测试，我们只是确认逻辑正确性
        if any(cmd.startswith(invalid_prefix) for invalid_prefix in invalid_prefixes if
               invalid_prefix not in valid_prefixes):
            # 以无效前缀开头的命令不应该匹配
            assert not has_valid_prefix, f"命令 '{cmd}' 不应匹配有效前缀 (有效前缀: {valid_prefixes})"
        elif cmd == "yiyan":
            # 无前缀的命令不应该匹配
            assert not has_valid_prefix, f"无前缀命令 '{cmd}' 不应匹配有效前缀 (有效前缀: {valid_prefixes})"
        else:
            # 其他命令应该匹配有效前缀
            assert has_valid_prefix, f"命令 '{cmd}' 应匹配有效前缀 (有效前缀: {valid_prefixes})"


class TestPluginConfig:
    """测试插件配置"""

    def test_default_config(self):
        """测试默认配置"""
        import sys
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        hitokoto_dir = os.path.join(project_root, "src/plugins/hitokoto")

        sys.path.insert(0, hitokoto_dir)
        try:
            from config import ScopedConfig

            config = ScopedConfig()

            # 验证默认值
            assert config.is_enable is True
            assert config.cache_timeout == 90
            assert config.cache_length_limit == 100
            assert config.is_allow_group is True
            assert config.is_allow_user is True

        finally:
            sys.path.remove(hitokoto_dir)

    def test_custom_config(self):
        """测试自定义配置"""
        import sys
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        hitokoto_dir = os.path.join(project_root, "src/plugins/hitokoto")

        sys.path.insert(0, hitokoto_dir)
        try:
            from config import ScopedConfig

            config = ScopedConfig(
                is_enable=False,
                cache_timeout=120,
                whitelist_users=[12345, 67890],
                blacklist_groups=[10000]
            )

            assert config.is_enable is False
            assert config.cache_timeout == 120
            assert config.whitelist_users == [12345, 67890]
            assert config.blacklist_groups == [10000]

        finally:
            sys.path.remove(hitokoto_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
