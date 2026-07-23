#!/usr/bin/env python3
# deepseek


import argparse
import sys
from pathlib import Path


def parse_env_file(filepath):
    """
    解析 .env 文件，返回键值对字典。
    忽略空行和以 '#' 开头的注释行。
    键和值会去除首尾空白，值可以包含等号。
    """
    env_dict = {}
    with Path(filepath).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith("#"):
                continue
            # 按第一个 '=' 分割
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                env_dict[key] = value
            else:
                # 没有 '=' 的行，按某些规范可能视为无效，这里忽略或警告
                print(f"警告：忽略无效行（无等号）: {line}")
    return env_dict


def compare_env_files(file1, file2):
    """比较两个 .env 文件，打印差异。"""
    dict1 = parse_env_file(file1)
    dict2 = parse_env_file(file2)

    if dict1 == dict2:
        print("两个 .env 文件的条目完全相同。")
        return True

    # 找出差异
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    common_keys = keys1 & keys2
    only_in_file1 = keys1 - keys2
    only_in_file2 = keys2 - keys1

    print("两个 .env 文件的条目存在差异：")
    if only_in_file1:
        print(f"仅在 {file1} 中存在的键：")
        for key in sorted(only_in_file1):
            print(f"  {key}={dict1[key]}")
    if only_in_file2:
        print(f"仅在 {file2} 中存在的键：")
        for key in sorted(only_in_file2):
            print(f"  {key}={dict2[key]}")

    # 比较共同键的值
    diff_values = {key for key in common_keys if dict1[key] != dict2[key]}
    if diff_values:
        print("共同键但值不同的条目：")
        for key in sorted(diff_values):
            print(f"  {key}:")
            print(f"    {file1}: {dict1[key]}")
            print(f"    {file2}: {dict2[key]}")

    return False


def main():
    parser = argparse.ArgumentParser(description="比较两个 .env 文件的环境变量条目")
    parser.add_argument("file1", type=str, help="第一个 .env 文件路径")
    parser.add_argument("file2", type=str, help="第二个 .env 文件路径")
    args = parser.parse_args()

    file1 = Path(args.file1)
    file2 = Path(args.file2)

    if not file1.exists():
        print(f"错误：文件 {file1} 不存在")
        sys.exit(1)
    if not file2.exists():
        print(f"错误：文件 {file2} 不存在")
        sys.exit(1)

    compare_env_files(file1, file2)


if __name__ == "__main__":
    main()
