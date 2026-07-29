"""Benchmark: Database CRUD throughput via SQLAlchemy async."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import delete

from tests.benchmarks.bench_utils import async_bench
from src.plugins.aihelper.models import AIHelperComments, Settings


class TestGetConfig:
    @pytest.mark.parametrize("concurrency", [1, 10, 50])
    @pytest.mark.asyncio
    async def test_get_config_latency(self, db_session, concurrency: int):
        from src.plugins.aihelper.aihelper_handles import get_config_by_id

        async def get_one():
            return await get_config_by_id(sid="1", session=db_session)

        async def run():
            tasks = [get_one() for _ in range(concurrency)]
            return await asyncio.gather(*tasks)

        results = await run()
        assert all(r is not None for r in results)

        r = await async_bench(run, rounds=10, warmup=3)
        assert r.mean < 10.0, f"get_config too slow: {r.mean:.4f}s"


class TestSaveComments:
    @pytest.mark.parametrize("count", [10, 100])
    @pytest.mark.asyncio
    async def test_save_comments_throughput(self, db_session, count: int):
        from src.plugins.aihelper.aihelper_handles import save_comments_by_id

        async def run():
            for i in range(count):
                await save_comments_by_id(
                    sid=f"bench_cmt_{i}", session=db_session, msg=f"msg {i}"
                )

        await run()

        await db_session.execute(
            delete(AIHelperComments).where(
                AIHelperComments.comment_id.like("bench_cmt_%")
            )
        )
        await db_session.commit()


class TestUpdateComments:
    @pytest.mark.parametrize("concurrency", [1, 10, 50])
    @pytest.mark.asyncio
    async def test_update_contention(self, db_session, concurrency: int):
        from src.plugins.aihelper.aihelper_handles import (
            save_comments_by_id,
            update_comments_by_id,
        )

        sid = "bench_update_concurrent"
        await save_comments_by_id(sid=sid, session=db_session, msg="initial")

        async def update_one():
            return await update_comments_by_id(
                sid=sid, session=db_session, msg=f"updated {asyncio.get_running_loop().time()}"
            )

        async def run():
            tasks = [update_one() for _ in range(concurrency)]
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = await run()
        success = sum(1 for r in results if not isinstance(r, Exception) and r != -1)

        r = await async_bench(run, rounds=5, warmup=2)
        assert r.mean < 30.0, f"update contention too slow: {r.mean:.4f}s"

        await db_session.execute(
            delete(AIHelperComments).where(AIHelperComments.comment_id == sid)
        )
        await db_session.commit()


class TestLargeTable:
    @pytest.mark.asyncio
    async def test_get_all_comment_ids_memory(self, db_session):
        from src.plugins.aihelper.aihelper_handles import (
            get_all_comment_ids,
            save_comments_by_id,
        )

        for i in range(200):
            await save_comments_by_id(
                sid=f"bench_large_{i}", session=db_session, msg=f"test {i}",
            )

        ids = await get_all_comment_ids(db_session)
        assert len(ids) >= 200

        r = await async_bench(get_all_comment_ids, db_session, rounds=10, warmup=3)
        assert r.mean < 5.0, f"get_all_comment_ids too slow: {r.mean:.4f}s"

        await db_session.execute(
            delete(AIHelperComments).where(
                AIHelperComments.comment_id.like("bench_large_%")
            )
        )
        await db_session.commit()
