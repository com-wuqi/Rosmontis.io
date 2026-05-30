"""
环境配置文件读取工具
用于测试中读取.env和.env.prod文件中的配置
"""

import ast
import json
import os
from typing import List, Dict


def load_env_file(env_path: str) -> Dict[str, str]:
    """加载.env文件"""
    env_config = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue

                # 解析键值对（支持简单赋值和JSON格式）
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    env_config[key] = value
    return env_config


def parse_command_start(value: str) -> List[str]:
    """解析COMMAND_START配置，支持多种格式"""
    if not value:
        return ["*", "$", "/"]  # 默认值

    # 尝试解析JSON数组
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return [str(item) for item in result]
    except json.JSONDecodeError:
        pass

    # 尝试解析Python列表（ast.literal_eval）
    try:
        result = ast.literal_eval(value)
        if isinstance(result, list):
            return [str(item) for item in result]
    except (ValueError, SyntaxError):
        pass

    # 简单分割（处理类似 ["*","$","/"] 的情况）
    if value.startswith('[') and value.endswith(']'):
        # 去除方括号
        value = value[1:-1]
        # 分割并清理
        items = []
        current_item = ""
        in_quotes = False
        quote_char = None

        for char in value:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ',' and not in_quotes:
                if current_item.strip():
                    items.append(current_item.strip().strip('"\''))
                current_item = ""
            else:
                current_item += char

        if current_item.strip():
            items.append(current_item.strip().strip('"\''))

        if items:
            return items

    return ["*", "$", "/"]  # 默认值


def get_command_prefixes(project_root: str) -> List[str]:
    """
    获取命令前缀列表
    优先从.env读取，如果不存在则从.env.prod读取
    """
    # 尝试读取.env
    env_path = os.path.join(project_root, ".env")
    env_config = load_env_file(env_path)

    command_start = env_config.get("COMMAND_START")

    # 如果.env中没有或值为空，尝试.env.prod
    if not command_start:
        env_prod_path = os.path.join(project_root, ".env.prod")
        env_config = load_env_file(env_prod_path)
        command_start = env_config.get("COMMAND_START")

    return parse_command_start(command_start)


def get_hitokoto_config(project_root: str, key: str, default: str = "") -> str:
    """
    获取hitokoto相关配置
    支持从.env和.env.prod读取
    """
    # 尝试读取.env
    env_path = os.path.join(project_root, ".env")
    env_config = load_env_file(env_path)

    # 构建完整的配置键
    full_key = f"HITOKOTO__{key}"
    value = env_config.get(full_key)

    # 如果.env中没有，尝试.env.prod
    if value is None:
        env_prod_path = os.path.join(project_root, ".env.prod")
        env_config = load_env_file(env_prod_path)
        value = env_config.get(full_key)

    return value if value is not None else default


# 测试函数
if __name__ == "__main__":
    # 获取项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

    # 测试命令前缀读取
    prefixes = get_command_prefixes(project_root)
    print(f"命令前缀: {prefixes}")

    # 测试hitokoto配置读取
    is_enable = get_hitokoto_config(project_root, "IS_ENABLE", "true")
    print(f"HITOKOTO是否启用: {is_enable}")

    # 测试不同格式的解析
    test_cases = [
        '["*","$","/"]',
        "['*','$','/']",
        '["/"]',
        '["!", "?", "#"]',
        "*,$,/",
        "",
    ]

    print("\n测试命令前缀解析:")
    for test_case in test_cases:
        result = parse_command_start(test_case)
        print(f"  '{test_case}' -> {result}")
