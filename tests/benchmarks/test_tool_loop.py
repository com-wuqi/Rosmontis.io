"""Benchmark: Tool calling loop performance and MCP routing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tests.benchmarks.bench_utils import async_bench, bench_sync


class TestMCPToolRouting:
    @pytest.mark.parametrize("tool_count", [5, 20, 50, 100])
    @pytest.mark.asyncio
    async def test_call_tool_latency(self, tool_count: int, mock_mcp_manager):
        from tests.benchmarks.conftest import MockMCPTool, MockMultiMCPManager
        from src.plugins.aihelper.aihelper_handles import mcp_manger as orig_mgr

        mgr = MockMultiMCPManager(tools=[
            MockMCPTool(name=f"tool_{i}", description=f"Tool {i}", delay=0.01)
            for i in range(tool_count)
        ])

        with patch("src.plugins.aihelper.aihelper_handles.mcp_manger", mgr):
            new_mgr = mgr

            result = await new_mgr.call_tool("tool_0", {})
            assert result is not None

            async def call():
                return await new_mgr.call_tool("tool_0", {})

            r = await async_bench(call, rounds=20, warmup=3)
            assert r.mean < 1.0, f"call_tool too slow: {r.mean:.4f}s"

    @pytest.mark.parametrize("tool_count", [10, 100, 500, 1000])
    def test_tool_lookup_overhead(self, tool_count: int):
        from tests.benchmarks.conftest import MockMCPTool, MockMultiMCPManager

        mgr = MockMultiMCPManager(tools=[
            MockMCPTool(name=f"tool_{i}") for i in range(tool_count)
        ])

        def lookup():
            return mgr.tool_map.get(f"tool_{tool_count // 2}")

        result = lookup()
        assert result is not None

        r = bench_sync(lookup, rounds=200, warmup=20)
        assert r.mean < 0.01, f"dict lookup too slow: {r.mean:.6f}s"


class TestToolLoopIteration:
    @pytest.mark.parametrize("iterations", [1, 3, 5])
    @pytest.mark.asyncio
    async def test_tool_loop_latency(
        self, iterations: int, mock_mcp_manager, mock_ai_response, redis_client, session_dicts,
    ):
        from tests.benchmarks.conftest import make_chat_completion

        call_index = [0]

        async def mock_create(*args, **kwargs):
            call_index[0] += 1
            await asyncio.sleep(0.02)
            if call_index[0] <= iterations:
                return make_chat_completion(
                    content="calling tool",
                    tool_calls=[
                        {
                            "id": f"call_{call_index[0]}",
                            "function": {"name": "ros_get_current_time", "arguments": {}},
                        }
                    ],
                )
            return make_chat_completion(content="final answer")

        from src.plugins.aihelper.aihelper_handles import send_messages_to_ai
        from src.plugins.aihelper.aihelper_handles import mcp_manger

        messages = [{"role": "system", "content": "test"}, {"role": "user", "content": "hello"}]

        max_iters = iterations + 2  # enough to get the final answer

        async def run():
            count = 0
            result = None
            while count < max_iters:
                result = await send_messages_to_ai(
                    key="sk-test", url="https://api.test/v1",
                    model_name="gpt-4", temperature=1.0, messages=messages,
                )
                if not result.tool_calls:
                    break
                for tc in result.tool_calls:
                    messages.append({
                        "role": "assistant", "content": result.content,
                        "tool_calls": [{
                            "id": tc.id, "type": tc.type,
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }],
                    })
                    tool_result = await mcp_manger.call_tool(tc.function.name, {})
                    messages.append({
                        "tool_call_id": tc.id, "role": "tool", "content": str(tool_result),
                    })
                count += 1
            return result.content if result else ""

        with patch(
            "src.plugins.aihelper.aihelper_handles.AsyncOpenAI"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = mock_create
            mock_client_class.return_value = mock_client
            with patch("src.plugins.aihelper.aihelper_handles.semaphore", asyncio.Semaphore(50)):
                result = await run()
                assert "final" in str(result)

                call_index[0] = 0
                messages.clear()
                messages.extend([{"role": "system", "content": "test"}, {"role": "user", "content": "hello"}])

                r = await async_bench(run, rounds=5, warmup=1)
                assert r.mean < 30.0, f"tool loop too slow: {r.mean:.4f}s"


class TestMCPCallTool:
    @pytest.mark.asyncio
    async def test_builtin_call_tool_baseline(self, mock_mcp_manager):
        from src.plugins.aihelper.aihelper_handles import mcp_manger

        result = await mcp_manger.call_tool("ros_get_current_time", {})
        assert result == "mock tool result"

        async def call():
            return await mcp_manger.call_tool("ros_get_current_time", {})

        r = await async_bench(call, rounds=20, warmup=3)
        assert r.mean < 1.0, f"builtin call_tool too slow: {r.mean:.4f}s"
