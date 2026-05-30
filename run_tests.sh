#!/bin/bash
# Rosmontis 测试运行脚本
# 运行 tests/ 目录中的所有测试（与.idea/pytest.xml配置一致）

set -e

echo "Running tests in tests/ directory..."
python -m pytest tests/ -v --tb=short