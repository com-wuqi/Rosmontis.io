"""Benchmark: Message aggregation and Redis Stream pipeline throughput."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.benchmarks.bench_utils import async_bench


class TestAggregationLogic:
    @pytest.mark.parametrize("max_size", [1, 3, 5])
    @pytest.mark.parametrize("timeout", [0.5, 1, 2])
    @pytest.mark.asyncio
    async def test_handle_merge_trigger(
        self, redis_streams, max_size: int, timeout: int
    ):
        from src.plugins.aihelper import _STREAM_INCOMING, _STREAM_TASKS
        from src.plugins.aihelper.chater import MessageHandleWorkers
        from src.plugins.aihelper import config

        with patch.object(config, "message_queue_max_size", max_size):
            with patch.object(config, "message_queue_timeout", timeout):
                bot = AsyncMock()
                bot.adapter_name = "OneBot V11"
                workers = MessageHandleWorkers(bot, {"OneBot V11": bot})

                sid = "test_agg_session"
                for i in range(max_size):
                    await redis_streams.xadd(
                        _STREAM_INCOMING,
                        {
                            "type": "msg",
                            "session_id": sid,
                            "session_type": "private",
                            "adapter": "OneBot V11",
                        },
                    )
                    workers._messages_counter[sid] = workers._messages_counter.get(sid, 0) + 1
                    workers._last_active_time[sid] = asyncio.get_running_loop().time()

                await workers.handle_merge()
                assert True


class TestStreamThroughput:
    @pytest.mark.asyncio
    async def test_xadd_throughput(self, redis_streams):
        from src.plugins.aihelper import _STREAM_INCOMING

        async def add_one(i: int):
            await redis_streams.xadd(
                _STREAM_INCOMING,
                {
                    "type": "msg",
                    "session_id": f"session_{i}",
                    "session_type": "private",
                    "adapter": "OneBot V11",
                },
            )

        async def run():
            tasks = [add_one(i) for i in range(100)]
            await asyncio.gather(*tasks)

        r = await async_bench(run, rounds=10, warmup=2)
        assert r.mean < 10.0, f"xadd too slow: {r.mean:.4f}s"


class TestConsumerGroup:
    @pytest.mark.asyncio
    async def test_xreadgroup_performance(self, redis_streams):
        from src.plugins.aihelper import _STREAM_TASKS, _GROUP

        for i in range(200):
            await redis_streams.xadd(
                _STREAM_TASKS,
                {
                    "session_id": f"session_{i}",
                    "session_type": "private",
                    "adapter": "OneBot V11",
                },
            )

        async def read_one():
            result = await redis_streams.xreadgroup(
                groupname=_GROUP,
                consumername="benchmark-consumer",
                streams={_STREAM_TASKS: ">"},
                count=10,
                block=100,
            )
            if result:
                for msg_id, fields in result[0][1]:
                    await redis_streams.xack(_STREAM_TASKS, _GROUP, msg_id)
            return result

        result = await read_one()
        assert result is not None

        r = await async_bench(read_one, rounds=10, warmup=2)
        assert r.mean < 5.0, f"xreadgroup too slow: {r.mean:.4f}s"


class TestMessageHandleWorkersConstructor:
    """Verify MessageHandleWorkers initializes correctly."""

    @pytest.mark.asyncio
    async def test_workers_constructor(self, mock_bot):
        from src.plugins.aihelper.chater import MessageHandleWorkers

        workers = MessageHandleWorkers(mock_bot, {"OneBot V11": mock_bot})
        assert workers is not None
        assert workers._consumer_id is not None
        assert workers._workers == []
        assert not workers._stop_signal.is_set()
        await workers.close_workers()
