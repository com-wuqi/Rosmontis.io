"""Benchmark: Chat history compression (common_zip_message)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tests.benchmarks.bench_utils import async_bench, bench_sync
from src.plugins.aihelper.chater import chunk_messages, generate_zip_message


def generate_mock_history(count: int) -> list[dict]:
    messages = [{"role": "system", "content": "你是一个测试助手。"}]
    for i in range(count):
        messages.append({"role": "user", "content": f"用户 {i}: 这是一个测试消息。" * 3})
        messages.append({
            "role": "assistant",
            "content": f"助手 {i}: 收到。这是回复内容。" * 5,
            "tool_calls": [
                {"id": f"call_{i}", "type": "function", "function": {"name": "get_time", "arguments": "{}"}},
            ],
        })
        messages.append({"role": "tool", "tool_call_id": f"call_{i}", "content": "2024-01-01T00:00:00Z"})
    return messages


class TestChunking:
    @pytest.mark.parametrize("total,chunk_size", [(20, 4), (100, 8), (200, 16)])
    def test_chunk_messages(self, total: int, chunk_size: int):
        messages = generate_mock_history(total)

        result = chunk_messages(messages, chunk_size)
        actual_count = len(messages)
        expected = (actual_count // chunk_size) + (1 if actual_count % chunk_size else 0)
        assert len(result) == expected

        r = bench_sync(lambda: chunk_messages(messages, chunk_size), rounds=50, warmup=5)
        assert r.mean < 0.1, f"chunk_messages too slow: {r.mean:.4f}s"


class TestCompressionLatency:
    @pytest.mark.parametrize("msg_count", [20, 50, 100])
    @pytest.mark.asyncio
    async def test_compression_latency(self, msg_count: int, mock_mcp_manager):
        from tests.benchmarks.conftest import make_chat_completion

        messages = generate_mock_history(msg_count)

        async def mock_create(*args, **kwargs):
            await asyncio.sleep(0.01)
            return make_chat_completion(content="chunk summary")

        from src.plugins.aihelper.chater import common_zip_message
        from src.plugins.aihelper.models import Settings

        row = Settings(
            user_id="test", url="https://api.test/v1", api_key="sk-test",
            model_name="gpt-4", system="test", temperature=1.0, is_enabled=True,
        )

        with patch(
            "src.plugins.aihelper.aihelper_handles.AsyncOpenAI"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = mock_create
            mock_client_class.return_value = mock_client
            with patch("src.plugins.aihelper.aihelper_handles.semaphore", asyncio.Semaphore(50)):
                result = await common_zip_message(_input_msg=messages, row=row)
                assert result is not None
                assert len(result) >= 1
                assert result[0]["role"] == "system"

                async def run():
                    return await common_zip_message(_input_msg=messages, row=row)

                r = await async_bench(run, rounds=5, warmup=2)
                assert r.mean < 30.0, f"compression too slow: {r.mean:.4f}s"


class TestZipMessageGeneration:
    @pytest.mark.parametrize("msg_count", [10, 50, 100])
    def test_generate_zip_message(self, msg_count: int):
        messages = generate_mock_history(msg_count)

        result, system_msgs = generate_zip_message(messages)
        assert len(result) > 0
        assert result[0]["role"] == "system"

        r = bench_sync(lambda: generate_zip_message(messages), rounds=20, warmup=5)
        assert r.mean < 1.0, f"generate_zip_message too slow: {r.mean:.4f}s"


class TestCompressionRatio:
    @pytest.mark.parametrize("msg_count", [50, 100, 200])
    def test_token_count_comparison(self, msg_count: int):
        import json
        messages = generate_mock_history(msg_count)
        raw_text = json.dumps(messages, ensure_ascii=False)
        chunks = chunk_messages(messages, 8)

        original_tokens_approx = len(raw_text) // 3
        chunk_count = len(chunks)
        assert chunk_count >= 1
        assert original_tokens_approx > 0
