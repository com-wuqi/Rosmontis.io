"""Benchmark: Session I/O performance (Redis hash read/write)."""

from __future__ import annotations

import asyncio
import json

import pytest
from tests.benchmarks.bench_utils import async_bench, bench_sync


@pytest.fixture
def sample_messages():
    def _make(count: int):
        messages = []
        for i in range(count):
            messages.append({
                "role": "user",
                "content": f"用户消息 {i}: " + "测试内容 " * 20,
            })
            messages.append({
                "role": "assistant",
                "content": f"AI回复 {i}: " + "回复内容 " * 30,
            })
        return messages
    return _make


class TestSessionLoad:
    @pytest.mark.parametrize("msg_count", [0, 10, 50, 100, 500])
    @pytest.mark.asyncio
    async def test_load_latency(self, redis_client, sample_messages, msg_count: int):
        from src.plugins.aihelper.session import _session_load, _session_save

        sid = "bench_load_test"
        messages = sample_messages(msg_count)
        await _session_save(sid, messages, active=True)

        loaded_msgs, active = await _session_load(sid)
        assert len(loaded_msgs) == len(messages)
        assert active is True

        result = await async_bench(_session_load, sid, rounds=20, warmup=3)
        assert result.mean < 5.0, f"load too slow: {result.mean:.4f}s"

    @pytest.mark.parametrize("msg_count", [0, 10, 50, 100, 500, 1000])
    def test_json_overhead(self, sample_messages, msg_count: int):
        messages = sample_messages(msg_count)
        raw = json.dumps(messages, ensure_ascii=False)

        def serialize():
            json.dumps(messages, ensure_ascii=False)

        def deserialize():
            json.loads(raw)

        r1 = bench_sync(serialize, rounds=50, warmup=5)
        assert r1.mean < 1.0, f"serialize too slow: {r1.mean:.4f}s"

        r2 = bench_sync(deserialize, rounds=50, warmup=5)
        assert r2.mean < 1.0, f"deserialize too slow: {r2.mean:.4f}s"


class TestSessionSave:
    @pytest.mark.parametrize("msg_count", [0, 10, 50, 100, 500])
    @pytest.mark.asyncio
    async def test_save_latency(self, redis_client, sample_messages, msg_count: int):
        from src.plugins.aihelper.session import _session_save, _session_delete

        sid = "bench_save_test"
        messages = sample_messages(msg_count)
        await _session_save(sid, messages, active=True)

        async def save():
            await _session_save(sid, messages, active=True)

        result = await async_bench(save, rounds=20, warmup=3)
        assert result.mean < 5.0, f"save too slow: {result.mean:.4f}s"

        await _session_delete(sid)


class TestSessionConcurrent:
    @pytest.mark.parametrize("session_count", [10, 50])
    @pytest.mark.asyncio
    async def test_concurrent_read_write(
        self, redis_client, sample_messages, session_count: int
    ):
        from src.plugins.aihelper.session import _session_load, _session_save, _session_delete

        messages = sample_messages(5)

        async def load_save_one(i: int):
            sid = f"bench_concurrent_{i}"
            await _session_save(sid, messages, active=True)
            loaded, _ = await _session_load(sid)
            await _session_delete(sid)
            return len(loaded)

        tasks = [load_save_one(i) for i in range(session_count)]
        results = await asyncio.gather(*tasks)
        assert sum(results) == session_count * len(messages)

        async def run():
            tasks2 = [load_save_one(i) for i in range(session_count)]
            return await asyncio.gather(*tasks2)

        r = await async_bench(run, rounds=5, warmup=1)
        assert r.mean < 30.0, f"concurrent too slow: {r.mean:.4f}s"


class TestSessionLock:
    @pytest.mark.parametrize("concurrency", [2, 5, 10])
    @pytest.mark.asyncio
    async def test_lock_contention(self, redis_client, concurrency: int):
        from src.plugins.aihelper.chater import get_session_lock
        from src.plugins.aihelper.session import _session_save

        sid = "bench_lock_test"
        messages = [{"role": "user", "content": "test"}]

        async def hold_lock():
            lock = await get_session_lock(sid)
            async with lock:
                await _session_save(sid, messages, active=True)

        tasks = [hold_lock() for _ in range(concurrency)]
        await asyncio.gather(*tasks)
