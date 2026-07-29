"""Benchmark: AI API call latency, retry behavior, and semaphore saturation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tests.benchmarks.bench_utils import async_bench


def _make_response(content: str, delay: float = 0.01):
    from tests.benchmarks.conftest import make_chat_completion

    async def _mock(*args, **kwargs):
        await asyncio.sleep(delay)
        return make_chat_completion(content=content)
    return _mock


class TestLatencyDistribution:
    @pytest.mark.parametrize("delay", [0.01, 0.1])
    @pytest.mark.parametrize("concurrency", [1, 10])
    @pytest.mark.asyncio
    async def test_send_latency(
        self, delay: float, concurrency: int, mock_mcp_manager
    ):
        from src.plugins.aihelper.aihelper_handles import send_messages_to_ai

        async def call_one():
            return await send_messages_to_ai(
                key="sk-test", url="https://api.test/v1",
                model_name="gpt-4", temperature=1.0,
                messages=[{"role": "user", "content": "hello"}],
            )

        async def run():
            tasks = [call_one() for _ in range(concurrency)]
            return await asyncio.gather(*tasks)

        with patch(
            "src.plugins.aihelper.aihelper_handles.AsyncOpenAI"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = _make_response("OK", delay)
            mock_client_class.return_value = mock_client
            with patch("src.plugins.aihelper.aihelper_handles.semaphore", asyncio.Semaphore(50)):
                results = await run()
                assert len(results) == concurrency
                assert all(r.content == "OK" for r in results)


class TestRetryBehavior:
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, mock_mcp_manager):
        from src.plugins.aihelper.aihelper_handles import send_messages_to_ai
        from tests.benchmarks.conftest import make_chat_completion

        call_count = [0]

        async def fail_first(*args, **kwargs):
            call_count[0] += 1
            await asyncio.sleep(0.01)
            return make_chat_completion(content=f"call {call_count[0]} succeeded")

        with patch(
            "src.plugins.aihelper.aihelper_handles.AsyncOpenAI"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = fail_first
            mock_client_class.return_value = mock_client
            with patch("src.plugins.aihelper.aihelper_handles.semaphore", asyncio.Semaphore(50)):
                result = await send_messages_to_ai(
                    key="sk-test", url="https://api.test/v1",
                    model_name="gpt-4", temperature=1.0,
                    messages=[{"role": "user", "content": "hello"}],
                )

        assert result.content == "call 1 succeeded"
        assert call_count[0] == 1


class TestSemaphoreSaturation:
    @pytest.mark.parametrize("semaphore_limit", [5, 10, 50])
    @pytest.mark.asyncio
    async def test_saturation(self, semaphore_limit: int, mock_mcp_manager):
        from src.plugins.aihelper.aihelper_handles import send_messages_to_ai

        async def call_one():
            return await send_messages_to_ai(
                key="sk-test", url="https://api.test/v1",
                model_name="gpt-4", temperature=1.0,
                messages=[{"role": "user", "content": "hello"}],
            )

        async def run():
            tasks = [call_one() for _ in range(50)]
            return await asyncio.gather(*tasks)

        with patch(
            "src.plugins.aihelper.aihelper_handles.AsyncOpenAI"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = _make_response("ok", 0.05)
            mock_client_class.return_value = mock_client
            with patch(
                "src.plugins.aihelper.aihelper_handles.semaphore",
                asyncio.Semaphore(semaphore_limit),
            ):
                results = await run()
                assert len(results) == 50


class TestToolPayloadOverhead:
    @pytest.mark.parametrize("tool_count", [0, 10, 50, 100])
    def test_payload_size(self, tool_count: int):
        from tests.benchmarks.bench_utils import bench_sync
        import json

        tools = [
            {
                "type": "function",
                "function": {
                    "name": f"tool_{i}",
                    "description": f"Tool number {i} for testing",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "arg1": {"type": "string", "description": "test arg"}
                        },
                    },
                },
            }
            for i in range(tool_count)
        ]

        def serialize():
            return json.dumps(tools, ensure_ascii=False)

        payload = serialize()
        assert len(payload) > 0

        r = bench_sync(serialize, rounds=50, warmup=5)
        assert r.mean < 1.0, f"serialize too slow: {r.mean:.4f}s"
