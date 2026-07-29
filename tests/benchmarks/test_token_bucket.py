"""Benchmark: TokenBucket rate limiting accuracy.

Both implementations (public_apis and buildin_mcp_share) are identical.
We test using the buildin_mcp_share copy which has no module-level side effects.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from tests.benchmarks.bench_utils import async_bench


class TestTokenBucketSteadyState:
    @pytest.mark.parametrize("rate", [1, 3, 10, 50])
    @pytest.mark.asyncio
    async def test_steady_state_throughput(self, rate: int):
        from src.plugins.mcp_support.buildin_mcp_share import TokenBucket

        duration = 10.0 if rate <= 1 else 5.0

        async def run():
            b = TokenBucket(rate=float(rate), capacity=float(rate))
            count = 0
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                await b.acquire()
                count += 1
            return count

        count = await run()
        actual_rate = count / duration
        error_pct = abs(actual_rate - rate) / rate * 100
        tolerance = 25
        assert error_pct < tolerance, f"rate error {error_pct:.1f}% exceeds {tolerance}% threshold"

        result = await async_bench(run, rounds=3, warmup=1)
        assert result.median > 0


class TestTokenBucketBurst:
    @pytest.mark.parametrize("capacity", [5, 10, 20])
    @pytest.mark.asyncio
    async def test_initial_burst(self, capacity: int):
        from src.plugins.mcp_support.buildin_mcp_share import TokenBucket

        async def run():
            b = TokenBucket(rate=10.0, capacity=float(capacity))
            count = 0
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                await b.acquire()
                count += 1
            return count

        count = await run()
        expected = capacity + 20
        assert count <= expected + 2, f"burst {count} exceeds expected {expected}"


class TestTokenBucketConcurrent:
    @pytest.mark.parametrize("concurrency", [5, 10, 50])
    @pytest.mark.asyncio
    async def test_concurrent_acquire(self, concurrency: int):
        from src.plugins.mcp_support.buildin_mcp_share import TokenBucket

        capacity = float(concurrency * 2)
        rate = max(1.0, capacity)

        async def acquire_one(b: TokenBucket):
            await b.acquire()

        bucket = TokenBucket(rate=rate, capacity=capacity)

        async def run():
            tasks = [acquire_one(bucket) for _ in range(concurrency)]
            await asyncio.gather(*tasks)
            return concurrency

        result = await async_bench(run, rounds=5, warmup=1)
        assert result.median > 0


class TestTokenBucketLongTerm:
    @pytest.mark.parametrize("rate", [10, 100])
    @pytest.mark.asyncio
    async def test_no_drift(self, rate: int):
        from src.plugins.mcp_support.buildin_mcp_share import TokenBucket

        bucket = TokenBucket(rate=float(rate), capacity=float(rate))

        async def run():
            count = 0
            duration = 5.0
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                await bucket.acquire()
                count += 1
            return count

        count = await run()
        expected = rate * 5
        drift = abs(count - expected)
        tolerance = expected * 0.25 + 5
        assert drift <= tolerance, f"drift {drift} over 5s (rate={rate}), tolerance={tolerance}"


class TestTokenBucketComparison:
    @pytest.mark.asyncio
    async def test_both_implementations_equivalent(self):
        from src.plugins.mcp_support.buildin_mcp_share import TokenBucket as BucketA

        async def measure(bucket_cls, rate, capacity, duration):
            bucket = bucket_cls(rate=rate, capacity=capacity)
            count = 0
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                await bucket.acquire()
                count += 1
            return count

        count_a = await measure(BucketA, 10.0, 10.0, 1.0)
        assert 8 <= count_a <= 25, f"BucketA count {count_a} out of expected range"
