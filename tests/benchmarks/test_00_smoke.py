"""Smoke test: verify all benchmark fixtures load correctly."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_redis_client_fixture(redis_client):
    await redis_client.ping()
    assert await redis_client.ping() is True


@pytest.mark.asyncio
async def test_redis_streams_fixture(redis_streams):
    from src.plugins.aihelper import _STREAM_INCOMING, _STREAM_TASKS
    info_in = await redis_streams.xinfo_stream(_STREAM_INCOMING)
    assert info_in is not None


@pytest.mark.asyncio
async def test_db_session_fixture(db_session):
    from sqlalchemy import select
    from src.plugins.aihelper.models import Settings
    result = await db_session.execute(select(Settings).where(Settings.id == 1))
    row = result.scalars().first()
    assert row is not None
    assert row.user_id == "0"


@pytest.mark.asyncio
async def test_mock_ai_response(mock_ai_response):
    resp = await mock_ai_response(content="Hello")
    assert resp.choices[0].message.content == "Hello"
    assert resp.choices[0].message.role == "assistant"


@pytest.mark.asyncio
async def test_mock_bot(mock_bot):
    assert mock_bot.adapter_name == "OneBot V11"
    await mock_bot.send(None, "test")
    assert len(mock_bot._sent_messages) == 1


@pytest.mark.asyncio
async def test_mock_mcp_manager(mock_mcp_manager):
    from src.plugins.aihelper.aihelper_handles import mcp_manger
    assert "ros_get_current_time" in mcp_manger.tool_map
    result = await mcp_manger.call_tool("ros_get_current_time", {})
    assert result == "mock tool result"


@pytest.mark.asyncio
async def test_session_dicts(session_dicts):
    msgs, switch, cfg = session_dicts
    assert isinstance(msgs, dict)
    assert isinstance(switch, dict)
    assert isinstance(cfg, dict)
