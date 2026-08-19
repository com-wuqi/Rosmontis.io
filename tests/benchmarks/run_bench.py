#!/usr/bin/env python3
"""Standalone benchmark runner. Generates a performance report table."""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ["DRIVER"] = "~fastapi+~httpx+~websockets"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["LOCALSTORE_USE_CWD"] = "true"
os.environ["COMMAND_START"] = '["/"]'
os.environ["SUPERUSERS"] = '["1001"]'
os.environ["AIHELPER__IS_ENABLE"] = "true"
os.environ["AIHELPER__MAX_WORKERS"] = "4"
os.environ["AIHELPER__API_TIMEOUT"] = "30"
os.environ["AIHELPER__TOOLS_MAX_ONCE_CALLS"] = "5"
os.environ["AIHELPER__IS_ENABLE_TOOL_PROMPT"] = "false"
os.environ["AIHELPER__MESSAGE_QUEUE_TIMEOUT"] = "1"
os.environ["AIHELPER__MESSAGE_QUEUE_MAX_SIZE"] = "3"
os.environ["AIHELPER__REDIS_URL"] = "redis://localhost:6379/0"
os.environ["AIHELPER__REDIS_LONG_EXPIRE_TIME"] = "3600"
os.environ["AI_FILE_READER__IS_ENABLE"] = "false"
os.environ["YAOHUD__IS_ENABLE"] = "false"
os.environ["MCPSUPPORT__IS_ENABLE"] = "true"
os.environ["PUBLICAPI__IS_ENABLE_UPLOAD"] = "false"
os.environ["SELF_BUILD_TTS__IS_ENABLE"] = "false"
os.environ["HOOKED_MCP___"] = "true"
os.environ["SENTRY_DSN"] = ""
os.environ["SENTRY_SEND_DEFAULT_PII"] = "false"

import nonebot
nonebot.init(
    driver="~fastapi", host="127.0.0.1", port=8080, log_level="ERROR",
    command_start=["/"], superusers={"1001"}, environment="test",
    sqlalchemy_database_url="sqlite+aiosqlite://", localstore_use_cwd=True,
    sentry_dsn="", sentry_send_default_pii="false",
    aihelper__is_enable=True, aihelper__tools_max_once_calls=5,
    aihelper__is_enable_tool_prompt=False, aihelper__api_timeout=30,
    aihelper__message_queue_timeout=1, aihelper__message_queue_max_size=3,
    aihelper__max_workers=4, aihelper__redis_url="redis://localhost:6379/0",
    aihelper__redis_long_expire_time=3600,
    ai_file_reader__is_enable=False, yaohud__is_enable=False,
    mcpsupport__is_enable=True, publicapi__is_enable_upload=False,
    self_build_tts__is_enable=False, hooked_mcp___=True,
    onebot_ws_urls=[], onebot_access_token="test", selfhostaiusers=[],
)

nonebot.load_plugins("src/plugins")

ROUNDS = 15
WARMUP = 5


def header(msg: str):
    print(f"\n{'='*72}")
    print(f"  {msg}")
    print(f"{'='*72}")


def pct(data, p):
    return sorted(data)[int(len(data) * p / 100)]


async def bench_async(func, *args, rounds=ROUNDS, warmup=WARMUP):
    for _ in range(warmup):
        await func(*args)
    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        await func(*args)
        times.append(time.perf_counter() - t0)
    return {"min": min(times), "max": max(times), "med": statistics.median(times),
            "p95": pct(times, 95), "avg": statistics.mean(times)}


def bench_sync(func, *args, rounds=ROUNDS, warmup=WARMUP):
    for _ in range(warmup):
        func(*args)
    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        func(*args)
        times.append(time.perf_counter() - t0)
    return {"min": min(times), "max": max(times), "med": statistics.median(times),
            "p95": pct(times, 95), "avg": statistics.mean(times)}


# ── TokenBucket ──────────────────────────────────────────────────────────

async def bench_token_bucket():
    header("TokenBucket 限流精度")
    from src.plugins.mcp_support.buildin_mcp_share import TokenBucket

    for rate, cap, dur in [(1, 1, 10), (10, 10, 5), (50, 50, 5), (100, 100, 3)]:
        async def run():
            b = TokenBucket(float(rate), float(cap))
            cnt = deadline = 0
            deadline = time.monotonic() + dur
            while time.monotonic() < deadline:
                await b.acquire()
                cnt += 1
            return cnt

        count = await run()
        eff = count / dur
        r = await bench_async(run, rounds=3)
        print(f"  rate={rate:>4}/s  |  cap={cap:>4}  |  dur={dur}s  |  "
              f"actual_count={count:>4}  |  eff_rate={eff:.1f}/s  |  "
              f"loop_median={r['med']:.3f}s")

    for concurrency in [10, 50]:
        async def run_concurrent():
            b = TokenBucket(float(concurrency * 2), float(concurrency * 2))
            async def one():
                await b.acquire()
            await asyncio.gather(*(one() for _ in range(concurrency)))

        r = await bench_async(run_concurrent, rounds=5)
        print(f"  concurrent_acquire({concurrency}): median={r['med']:.4f}s")


# ── Session I/O ──────────────────────────────────────────────────────────

async def bench_session():
    header("Session I/O")
    import fakeredis.aioredis
    from src.plugins.aihelper.session import _session_save, _session_load, _session_delete, \
        _Messages_dicts as _M, _ai_switch as _A, _config_settings as _C

    rc = fakeredis.aioredis.FakeRedis(decode_responses=True)
    import src.plugins.aihelper as mod
    mod._redis = rc

    msgs_200 = [{"role": "user", "content": f"msg {i}: " + "data " * 30}
                for i in range(100)]
    msgs_200.extend({"role": "assistant", "content": f"reply {i}: " + "text " * 30}
                    for i in range(100))

    await _session_save("bench", msgs_200, True)

    r = await bench_async(_session_load, "bench", rounds=50)
    print(f"  _session_load (200 msgs): med={r['med']:.4f}s  "
          f"min={r['min']:.4f}s  p95={r['p95']:.4f}s")

    r = await bench_async(_session_save, "bench", msgs_200, True, rounds=50)
    print(f"  _session_save (200 msgs): med={r['med']:.4f}s  "
          f"min={r['min']:.4f}s  p95={r['p95']:.4f}s")

    raw = json.dumps(msgs_200, ensure_ascii=False)
    r = bench_sync(lambda: json.dumps(msgs_200, ensure_ascii=False), rounds=200)
    print(f"  json.dumps  (200 msgs): med={r['med']:.6f}s")
    r = bench_sync(lambda: json.loads(raw), rounds=200)
    print(f"  json.loads  (200 msgs): med={r['med']:.6f}s")
    print(f"  serialized size: {len(raw):,} bytes")

    await _session_delete("bench")
    await rc.aclose()


# ── Dict Lookup ──────────────────────────────────────────────────────────

async def bench_dict():
    header("Dict Lookup (MCP tool resolution)")
    for size in [50, 500, 5_000, 50_000]:
        d = {f"ros_tool_{i}": f"server_{i % 10}" for i in range(size)}
        r = bench_sync(lambda: d.get(f"ros_tool_{size // 2}"), rounds=5000)
        print(f"  dict.get ({size:>6} keys):  med={r['med']:.9f}s  "
              f"p95={r['p95']:.9f}s")


# ── Chat Compression ─────────────────────────────────────────────────────

async def bench_compression():
    header("Chat Compression")
    from src.plugins.aihelper.chater import chunk_messages, generate_zip_message

    for n in [50, 200, 500]:
        msgs = [{"role": "system", "content": "test"}] + [
            {"role": "user", "content": f"user {i}: " + "内容 " * 10}
            for i in range(n)
        ]
        r = bench_sync(lambda: chunk_messages(msgs, 8), rounds=30)
        print(f"  chunk_messages ({n:>3} msgs, size=8):  med={r['med']:.6f}s  "
              f"chunks={len(msgs)//8 + 1}")

    msgs = [{"role": "system", "content": "test"}] + [
        {"role": "user", "content": f"u {i}: 测试 " * 10}
        for i in range(200)
    ]
    r = bench_sync(lambda: generate_zip_message(msgs), rounds=10)
    print(f"  generate_zip_message (200 msgs):  med={r['med']:.4f}s")


# ── DB CRUD ──────────────────────────────────────────────────────────────

async def bench_db():
    header("DB CRUD (SQLite)")
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from src.plugins.aihelper.models import Settings, AIHelperComments

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Settings.metadata.create_all)
        await conn.run_sync(AIHelperComments.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        s.add(Settings(id=1, user_id="0", url="http://x", api_key="k",
                       model_name="m", system="s", temperature=1.0, is_enabled=True))
        await s.commit()

    async with async_session() as s:
        r = await bench_async(
            lambda: s.execute(select(Settings).where(Settings.id == 1)),
            rounds=100,
        )
        print(f"  SELECT by id:  med={r['med']:.4f}s  "
              f"p95={r['p95']:.4f}s  min={r['min']:.4f}s")

        for i in range(200):
            s.add(AIHelperComments(comment_id=f"c_{i}", message=f"msg {i}"))
        await s.commit()

    async with async_session() as s:
        from src.plugins.aihelper.aihelper_handles import get_all_comment_ids
        r = await bench_async(lambda: get_all_comment_ids(s), rounds=10)
        count = len(await get_all_comment_ids(s))
        print(f"  get_all_comment_ids ({count} rows):  med={r['med']:.4f}s")

    await engine.dispose()


# ── Redis Stream ─────────────────────────────────────────────────────────

async def bench_stream():
    header("Redis Stream Ops (fakeredis)")
    import fakeredis.aioredis
    rc = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await rc.xgroup_create("s:in", "g", id="0", mkstream=True)

    async def xadd_one(i):
        await rc.xadd("s:in", {"type": "msg", "sid": f"s_{i}", "st": "p"})

    r = await bench_async(lambda: asyncio.gather(*(xadd_one(i) for i in range(100))), rounds=10)
    print(f"  xadd ×100:  med={r['med']:.4f}s  p95={r['p95']:.4f}s")

    for i in range(200):
        await rc.xadd("s:in", {"type": "msg", "sid": f"s_{i}", "st": "p"})

    async def read():
        res = await rc.xreadgroup("g", "c1", {"s:in": ">"}, count=10, block=100)
        if res:
            for mid, _ in res[0][1]:
                await rc.xack("s:in", "g", mid)

    r = await bench_async(read, rounds=20)
    print(f"  xreadgroup (count=10):  med={r['med']:.4f}s  p95={r['p95']:.4f}s")

    await rc.aclose()


# ── Main ─────────────────────────────────────────────────────────────────

async def main():
    print(f"Rosmontis Benchmark Report")
    print(f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python    : {sys.version.split()[0]}")
    print(f"Platform  : {sys.platform}")
    print(f"Rounds    : {ROUNDS} / warmup={WARMUP}")

    t0 = time.perf_counter()

    await bench_token_bucket()
    await bench_session()
    await bench_dict()
    await bench_compression()
    await bench_db()
    await bench_stream()

    elapsed = time.perf_counter() - t0
    print(f"\n{'='*72}")
    print(f"  Total: {elapsed:.1f}s  |  {ROUNDS} rounds/warmup={WARMUP}")
    print(f"{'='*72}")


if __name__ == "__main__":
    asyncio.run(main())
