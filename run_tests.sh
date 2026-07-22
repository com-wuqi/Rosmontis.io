#!/bin/bash
# Rosmontis 测试运行脚本
# 运行 tests/ 目录中的所有测试（与.idea/pytest.xml配置一致）

set -e

echo "Syncing dependencies..."
uv sync --frozen --all-groups

echo "Running tests in tests/ directory..."
uv run pytest tests/ -v --tb=short
