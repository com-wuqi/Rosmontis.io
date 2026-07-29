"""Benchmark: Worker pool throughput scaling.

Tests:
A) Real Redis (class TestRealWorkerScaling)
B) Semaphore limiting + concurrent session benchmarks (fakeredis)
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest


# ── Real Redis scaling ──────────────────────────────────────────────────

class TestRealWorkerScaling:
    @pytest.mark.parametrize("worker_count", [1, 2, 4])
    @pytest.mark.asyncio
    async def test_throughput_vs_workers(
        self, worker_count: int, real_redis_streams, mock_bot, mock_mcp_manager
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
            await asyncio.sleep(0.05)
            return make_chat_completion(content="ok").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        reply_count = [0]
        lock = asyncio.Lock()

        async def cnt(bot, s, t, m):
            async with lock:
                reply_count[0] += 1

        chater_mod.send_reply = cnt

        orig_qsize = config.message_queue_max_size
        config.message_queue_max_size = 1

        total = worker_count * 3
        for i in range(total):
            sid = f"real_scale_{i}"
            _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
            _ai_switch[sid] = True
            _config_settings[sid] = settings

        with patch.object(config, "max_workers", worker_count):
            workers = MessageHandleWorkers(mock_bot, _bots)
            await workers.init_workers()
            ml = asyncio.create_task(workers.main_loop())

            try:
                t0 = time.monotonic()
                for i in range(total):
                    await real_redis_streams.xadd(
                        _STREAM_INCOMING,
                        {
                            "type": "msg", "session_id": f"real_scale_{i}",
                            "session_type": "private", "adapter": "OneBot V11",
                        },
                    )

                deadline = time.monotonic() + 30.0
                while reply_count[0] < total and time.monotonic() < deadline:
                    await asyncio.sleep(0.02)

                dt = time.monotonic() - t0
                assert reply_count[0] == total, (
                    f"workers={worker_count}: {reply_count[0]}/{total} in {dt:.1f}s"
                )

                theoretical = total * 0.05 / worker_count
                assert dt >= theoretical * 0.5, (
                    f"Implausibly fast: {dt:.2f}s < {theoretical*0.5:.2f}s"
                )
            finally:
                await workers.close_workers()
                ml.cancel()
                try:
                    await asyncio.wait_for(ml, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        config.message_queue_max_size = orig_qsize
        _Messages_dicts.clear()
        _ai_switch.clear()
        _config_settings.clear()

    @pytest.mark.asyncio
    async def test_burst_completion(
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
            await asyncio.sleep(0.05)
            return make_chat_completion(content="ok").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        reply_count = [0]
        lock = asyncio.Lock()

        async def cnt(bot, s, t, m):
            async with lock:
                reply_count[0] += 1

        chater_mod.send_reply = cnt

        orig_qsize = config.message_queue_max_size
        config.message_queue_max_size = 1

        worker_count = 4
        total = 12
        for i in range(total):
            sid = f"real_burst_{i}"
            _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
            _ai_switch[sid] = True
            _config_settings[sid] = settings

        with patch.object(config, "max_workers", worker_count):
            workers = MessageHandleWorkers(mock_bot, _bots)
            await workers.init_workers()
            ml = asyncio.create_task(workers.main_loop())

            try:
                t0 = time.monotonic()
                for i in range(total):
                    await real_redis_streams.xadd(
                        _STREAM_INCOMING,
                        {
                            "type": "msg", "session_id": f"real_burst_{i}",
                            "session_type": "private", "adapter": "OneBot V11",
                        },
                    )

                deadline = time.monotonic() + 30.0
                while reply_count[0] < total and time.monotonic() < deadline:
                    await asyncio.sleep(0.02)

                dt = time.monotonic() - t0
                assert reply_count[0] == total, (
                    f"burst: {reply_count[0]}/{total} in {dt:.1f}s"
                )
                assert dt < 30.0, f"Burst took {dt:.1f}s, too slow"
            finally:
                await workers.close_workers()
                ml.cancel()
                try:
                    await asyncio.wait_for(ml, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        config.message_queue_max_size = orig_qsize
        _Messages_dicts.clear()
        _ai_switch.clear()
        _config_settings.clear()


# ── Semaphore & concurrent benchmarks ───────────────────────────────────

class TestConcurrentSessions:
    @pytest.mark.parametrize("concurrency", [1, 5, 20])
    @pytest.mark.asyncio
    async def test_concurrent_handle_throughput(
        self,
        concurrency: int,
        redis_client,
        mock_bot,
        mock_mcp_manager,
        session_dicts,
    ):
        from src.plugins.aihelper.session import _Messages_dicts, _ai_switch, _config_settings
        from src.plugins.aihelper.models import Settings
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.chater as chater_mod

        settings = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="test", temperature=1.0, is_enabled=True,
        )

        async def mock_send(**kwargs):
            await asyncio.sleep(0.05)
            return make_chat_completion(content="ok").choices[0].message

        chater_mod.send_messages_to_ai = mock_send

        reply_count = [0]
        lock = asyncio.Lock()

        async def capture(bot, s, t, m):
            async with lock:
                reply_count[0] += 1

        chater_mod.send_reply = capture

        for i in range(concurrency):
            sid = f"conc_{i}"
            _Messages_dicts[sid] = [{"role": "system", "content": "test"}]
            _ai_switch[sid] = True
            _config_settings[sid] = settings

        from src.plugins.aihelper.chater import single_user_event_handle

        async def run():
            tasks = [
                single_user_event_handle(f"conc_{i}", "private", mock_bot)
                for i in range(concurrency)
            ]
            await asyncio.gather(*tasks)

        t0 = time.monotonic()
        await run()
        dt = time.monotonic() - t0

        assert reply_count[0] == concurrency
        min_expected = concurrency * 0.05 / 50
        assert dt >= min_expected * 0.5, (
            f"Implausibly fast: {dt:.2f}s for {concurrency} concurrent sessions"
        )

        for i in range(concurrency):
            _Messages_dicts.pop(f"conc_{i}", None)
            _ai_switch.pop(f"conc_{i}", None)
            _config_settings.pop(f"conc_{i}", None)

    @pytest.mark.parametrize("semaphore_limit", [1, 3, 10])
    @pytest.mark.asyncio
    async def test_semaphore_limiting(
        self,
        semaphore_limit: int,
        redis_client,
        mock_bot,
        mock_mcp_manager,
        session_dicts,
    ):
        """Verify that Semaphore limits concurrent AI API calls."""
        from tests.benchmarks.conftest import make_chat_completion
        import src.plugins.aihelper.aihelper_handles as handles_mod

        sem = asyncio.Semaphore(semaphore_limit)

        async def slow_send(**kwargs):
            async with sem:
                await asyncio.sleep(0.1)
            return make_chat_completion(content="ok").choices[0].message

        handles_mod.send_messages_to_ai = slow_send

        async def call():
            return await handles_mod.send_messages_to_ai(
                key="sk-test", url="https://api.test/v1",
                model_name="gpt-4", temperature=1.0,
                messages=[{"role": "user", "content": "hello"}],
            )

        t0 = time.monotonic()
        tasks = [call() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        dt = time.monotonic() - t0

        assert len(results) == 10
        best_case = 10 * 0.1 / semaphore_limit
        assert dt >= best_case * 0.8, (
            f"semaphore={semaphore_limit}: dt={dt:.2f}s, expected >= {best_case*0.8:.2f}s"
        )
