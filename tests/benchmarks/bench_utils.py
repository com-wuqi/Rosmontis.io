"""Async benchmark helper for pytest-asyncio tests."""

from __future__ import annotations

import statistics
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class BenchResult:
    rounds: int = 0
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    stdev: float = 0.0


async def async_bench(
    func: Callable[..., Awaitable[object]],
    *args,
    rounds: int = 10,
    warmup: int = 2,
    **kwargs,
) -> BenchResult:
    for _ in range(max(warmup, 1)):
        await func(*args, **kwargs)

    samples: list[float] = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        await func(*args, **kwargs)
        samples.append(time.perf_counter() - t0)

    return BenchResult(
        rounds=rounds,
        min=min(samples),
        max=max(samples),
        mean=statistics.mean(samples),
        median=statistics.median(samples),
        stdev=statistics.stdev(samples) if len(samples) >= 2 else 0.0,
    )


def bench_sync(
    func: Callable[..., object],
    *args,
    rounds: int = 10,
    warmup: int = 2,
    **kwargs,
) -> BenchResult:
    for _ in range(max(warmup, 1)):
        func(*args, **kwargs)

    samples: list[float] = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        func(*args, **kwargs)
        samples.append(time.perf_counter() - t0)

    return BenchResult(
        rounds=rounds,
        min=min(samples),
        max=max(samples),
        mean=statistics.mean(samples),
        median=statistics.median(samples),
        stdev=statistics.stdev(samples) if len(samples) >= 2 else 0.0,
    )
