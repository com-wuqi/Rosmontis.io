"""Benchmark: End-to-end message pipeline with REAL Redis.

Full message flow:
    xadd(ai:incoming) → main_loop → handle_merge → xadd(ai:tasks)
    → _single_worker → single_user_event_handle → send_messages_to_ai (mock)
    → send_reply (captured)

Requires real Redis (redis://localhost:6379/0).  Auto-skipped if unavailable.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


# ── REAL Redis E2E pipeline ─────────────────────────────────────────────

class TestRealE2ELatency:
    """End-to-end pipeline with real Redis.  Requires local Redis."""

    @pytest.mark.asyncio
    async def test_single_message_roundtrip(
        self, real_redis_streams, mock_bot, mock_mcp_manager
    ):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import _bots, config, _STREAM_INCOMING
        from src.plugins.aihelper.session import (
            _Messages_dicts, _ai_switch, _config_settings,
        )
        from src.plugins.aihelper.models import Settings
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.chater as chater_mod

        for k in list(_bots.keys()):
            del _bots[k]
        _bots["OneBot V11"] = mock_bot

        settings = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="test", temperature=1.0, is_enabled=True,
        )

        async def mock_send(**kwargs):
            await asyncio.sleep(0.02)
            return make_chat_completion(content="real redis reply").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        replies = []

        async def capture_reply(bot, s, t, m):
            replies.append((s, m))

        chater_mod.send_reply = capture_reply

        orig_qsize = config.message_queue_max_size
        config.message_queue_max_size = 1

        sid = "e2e_real"
        _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
        _ai_switch[sid] = True
        _config_settings[sid] = settings

        workers = MessageHandleWorkers(mock_bot, _bots)
        await workers.init_workers()
        ml = asyncio.create_task(workers.main_loop())

        try:
            t0 = time.monotonic()
            await real_redis_streams.xadd(
                _STREAM_INCOMING,
                {
                    "type": "msg", "session_id": sid,
                    "session_type": "private", "adapter": "OneBot V11",
                },
            )

            deadline = time.monotonic() + 10.0
            while len(replies) < 1 and time.monotonic() < deadline:
                await asyncio.sleep(0.02)

            dt = time.monotonic() - t0
            assert len(replies) == 1, f"Expected 1 reply, got {len(replies)}"
            assert replies[0][0] == sid
            assert dt < 10.0, f"E2E latency {dt:.2f}s exceeds limit"
        finally:
            await workers.close_workers()
            ml.cancel()
            try:
                await asyncio.wait_for(ml, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            chater_mod.send_messages_to_ai = mock_send
            config.message_queue_max_size = orig_qsize
            _Messages_dicts.clear()
            _ai_switch.clear()
            _config_settings.clear()

    @pytest.mark.parametrize("count", [3, 5])
    @pytest.mark.asyncio
    async def test_batch_throughput(
        self, count: int, real_redis_streams, mock_bot, mock_mcp_manager
    ):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import _bots, config, _STREAM_INCOMING
        from src.plugins.aihelper.session import (
            _Messages_dicts, _ai_switch, _config_settings,
        )
        from src.plugins.aihelper.models import Settings
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.chater as chater_mod

        for k in list(_bots.keys()):
            del _bots[k]
        _bots["OneBot V11"] = mock_bot

        settings = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="test", temperature=1.0, is_enabled=True,
        )

        async def mock_send(**kwargs):
            await asyncio.sleep(0.02)
            return make_chat_completion(content="ok").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        replies = []

        async def cnt(bot, s, t, m):
            replies.append(s)

        chater_mod.send_reply = cnt

        orig_qsize = config.message_queue_max_size
        config.message_queue_max_size = 1

        for i in range(count):
            sid = f"e2e_real_{i}"
            _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
            _ai_switch[sid] = True
            _config_settings[sid] = settings

        workers = MessageHandleWorkers(mock_bot, _bots)
        await workers.init_workers()
        ml = asyncio.create_task(workers.main_loop())

        try:
            t0 = time.monotonic()
            for i in range(count):
                await real_redis_streams.xadd(
                    _STREAM_INCOMING,
                    {
                        "type": "msg", "session_id": f"e2e_real_{i}",
                        "session_type": "private", "adapter": "OneBot V11",
                    },
                )

            deadline = time.monotonic() + 30.0
            while len(replies) < count and time.monotonic() < deadline:
                await asyncio.sleep(0.02)

            dt = time.monotonic() - t0
            assert len(replies) == count, (
                f"Expected {count} replies, got {len(replies)} in {dt:.1f}s"
            )
        finally:
            await workers.close_workers()
            ml.cancel()
            config.message_queue_max_size = orig_qsize
            _Messages_dicts.clear()
            _ai_switch.clear()
            _config_settings.clear()


# ── Isolated component tests (fakeredis) ────────────────────────────────

class TestHandleMerge:
    @pytest.mark.asyncio
    async def test_dispatches_when_queue_full(self, redis_streams):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import _STREAM_INCOMING, _STREAM_TASKS, _GROUP, config

        with patch.object(config, "message_queue_max_size", 1):
            bot = AsyncMock()
            bot.adapter_name = "OneBot V11"
            workers = MessageHandleWorkers(bot, {"OneBot V11": bot})

            sid = "merge_test"
            await redis_streams.xadd(
                _STREAM_INCOMING,
                {
                    "type": "msg", "session_id": sid,
                    "session_type": "private", "adapter": "OneBot V11",
                },
            )
            workers._message_type[sid] = "private"
            workers._messages_counter[sid] = 1
            workers._message_adapter[sid] = "OneBot V11"
            workers._last_active_time[sid] = asyncio.get_running_loop().time()

            await workers.handle_merge()

            result = await redis_streams.xread(
                streams={_STREAM_TASKS: "0-0"}, count=10, block=100
            )
            assert result is not None
            matching = []
            for _, entries in result:
                for _, fields in entries:
                    if fields.get("session_id") == sid:
                        matching.append(fields)
            assert len(matching) >= 1, "handle_merge did not xadd to tasks"

    @pytest.mark.asyncio
    async def test_skips_when_queue_not_full(self, redis_streams):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import _STREAM_TASKS, config

        with patch.object(config, "message_queue_max_size", 5):
            bot = AsyncMock()
            workers = MessageHandleWorkers(bot, {"OneBot V11": bot})

            sid = "merge_skip"
            workers._message_type[sid] = "private"
            workers._messages_counter[sid] = 1
            workers._last_active_time[sid] = asyncio.get_running_loop().time()

            await workers.handle_merge()

            result = await redis_streams.xread(
                streams={_STREAM_TASKS: "0-0"}, count=10, block=100
            )
            if result:
                matching = []
                for _, entries in result:
                    for _, fields in entries:
                        if fields.get("session_id") == sid:
                            matching.append(fields)
                assert len(matching) == 0, "handle_merge should not dispatch below threshold"


class TestSingleUserEvent:
    @pytest.mark.asyncio
    async def test_completes_and_sends_reply(
        self, redis_client, mock_bot, mock_mcp_manager, session_dicts
    ):
        from src.plugins.aihelper.session import _Messages_dicts, _ai_switch, _config_settings
        from src.plugins.aihelper.models import Settings
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.chater as chater_mod

        sid = "handle_test"
        settings = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="你是一个测试助手。", temperature=1.0,
            is_enabled=True,
        )
        _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
        _ai_switch[sid] = True
        _config_settings[sid] = settings

        async def mock_send(**kwargs):
            await asyncio.sleep(0.02)
            return make_chat_completion(content="test reply").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        got_reply = []

        async def capture(bot, s, t, m):
            got_reply.append(m)

        chater_mod.send_reply = capture

        from src.plugins.aihelper.chater import single_user_event_handle
        await single_user_event_handle(sid, "private", mock_bot)

        assert len(got_reply) == 1
        assert got_reply[0] == "test reply"

        _Messages_dicts.clear()
        _ai_switch.clear()
        _config_settings.clear()

    @pytest.mark.asyncio
    async def test_handles_tool_calls(
        self, redis_client, mock_bot, mock_mcp_manager, session_dicts
    ):
        from src.plugins.aihelper.session import _Messages_dicts, _ai_switch, _config_settings
        from src.plugins.aihelper.models import Settings
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.chater as chater_mod

        sid = "tool_test"
        settings = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="test", temperature=1.0, is_enabled=True,
        )
        _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
        _ai_switch[sid] = True
        _config_settings[sid] = settings

        call_count = [0]

        async def mock_send_with_tool(**kwargs):
            call_count[0] += 1
            await asyncio.sleep(0.02)
            if call_count[0] == 1:
                return make_chat_completion(
                    content="calling tool",
                    tool_calls=[{
                        "id": "call_1", "function": {
                            "name": "ros_get_current_time", "arguments": {},
                        },
                    }],
                ).choices[0].message
            return make_chat_completion(content="final reply").choices[0].message

        chater_mod.send_messages_to_ai = mock_send_with_tool

        got_reply = []

        async def capture(bot, s, t, m):
            got_reply.append(m)

        chater_mod.send_reply = capture

        from src.plugins.aihelper.chater import single_user_event_handle
        await single_user_event_handle(sid, "private", mock_bot)

        assert call_count[0] == 2, f"Expected 2 AI calls (tool + final), got {call_count[0]}"
        assert len(got_reply) == 1
        assert got_reply[0] == "final reply"

        _Messages_dicts.clear()
        _ai_switch.clear()
        _config_settings.clear()


class TestWorkerPoolLifecycle:
    @pytest.mark.asyncio
    async def test_init_and_close(self, mock_bot):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import config

        with patch.object(config, "max_workers", 2):
            workers = MessageHandleWorkers(mock_bot, {"OneBot V11": mock_bot})
            assert len(workers._workers) == 0

            await workers.init_workers()
            assert len(workers._workers) == 2
            assert all(isinstance(t, asyncio.Task) for t in workers._workers)

            await workers.close_workers()
            assert len(workers._workers) == 0
            assert workers._stop_signal.is_set()

    @pytest.mark.parametrize("n", [1, 4, 8])
    @pytest.mark.asyncio
    async def test_worker_count(self, mock_bot, n: int):
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import config

        with patch.object(config, "max_workers", n):
            workers = MessageHandleWorkers(mock_bot, {"OneBot V11": mock_bot})
            await workers.init_workers()
            assert len(workers._workers) == n
            await workers.close_workers()
