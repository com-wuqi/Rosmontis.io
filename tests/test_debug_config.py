# tests/test_debug_config.py
import os

import pytest


@pytest.mark.asyncio
async def test_debug_orm_config():
    """验证 ORM 配置是否正确设置为内存数据库"""
    db_url = os.getenv("ORM_DATABASE_URL")
    print(f"\n🔍 ORM_DATABASE_URL: {db_url}")

    # 确认使用的是内存 SQLite
    assert db_url and "sqlite+aiosqlite:///:memory:" in db_url, \
        f"Expected memory SQLite, got: {db_url}"

    skip_check = os.getenv("ORM_SKIP_MIGRATION_CHECK")
