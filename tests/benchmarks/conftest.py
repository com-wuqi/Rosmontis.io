"""
Benchmark fixtures: mock Redis, AI API, MCP manager, database, and bot adapters.

All mock fixtures inject at the module level so that plugin code under test
uses controlled dependencies.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function
from openai.types.completion_usage import CompletionUsage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Redis fixture (fakeredis)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with (
        patch("src.plugins.aihelper._redis", client),
        patch("src.plugins.aihelper.get_redis", return_value=client),
    ):
        yield client

    await client.aclose()


@pytest_asyncio.fixture
async def redis_streams(redis_client):
    from src.plugins.aihelper import (
        _GROUP,
        _STREAM_INCOMING,
        _STREAM_TASKS,
    )

    for stream in (_STREAM_INCOMING, _STREAM_TASKS):
        try:
            await redis_client.xgroup_create(stream, _GROUP, id="0", mkstream=True)
        except Exception:
            pass

    yield redis_client

    for stream in (_STREAM_INCOMING, _STREAM_TASKS):
        try:
            await redis_client.delete(stream)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# AI API mock
# ---------------------------------------------------------------------------

@dataclass
class AIMockConfig:
    delay: float = 0.05
    content: str = "Mock AI response."
    tool_calls: list[dict] | None = None
    error: type[Exception] | None = None


def make_chat_completion(content: str, tool_calls: list[dict] | None = None):
    tc_list = None
    if tool_calls:
        tc_list = [
            ChatCompletionMessageToolCall(
                id=tc.get("id", f"call_{i}"),
                type="function",
                function=Function(
                    name=tc["function"]["name"],
                    arguments=json.dumps(tc["function"]["arguments"]),
                ),
            )
            for i, tc in enumerate(tool_calls)
        ]
    return ChatCompletion(
        id="chatcmpl-mock",
        choices=[
            Choice(
                finish_reason="tool_calls" if tc_list else "stop",
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tc_list,
                ),
            )
        ],
        created=int(time.time()),
        model="mock-model",
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        ),
    )


@pytest_asyncio.fixture
async def mock_ai_response():
    async def _response(
        delay: float = 0.02,
        content: str = "Mock AI response.",
        tool_calls: list[dict] | None = None,
    ):
        await asyncio.sleep(delay)
        return make_chat_completion(content=content, tool_calls=tool_calls)

    return _response


# ---------------------------------------------------------------------------
# MCP Manager mock
# ---------------------------------------------------------------------------

@dataclass
class MockMCPTool:
    name: str
    description: str = ""
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    delay: float = 0.01
    result: str = "mock tool result"


def build_mock_mcp_tools(tools: list[MockMCPTool]):
    result = []
    for t in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or f"[{t.name}] mock tool",
                    "parameters": t.parameters,
                },
            }
        )
    return result


class MockMultiMCPManager:
    def __init__(self, tools: list[MockMCPTool] | None = None):
        tools = tools or []
        self._tools = tools
        self.all_tools = build_mock_mcp_tools(tools)
        self.tool_map: dict[str, str] = {t.name: f"mock_server_{i}" for i, t in enumerate(tools)}
        self.tool_original_map: dict[str, str] = {t.name: t.name for t in tools}

    async def call_tool(self, tool_name: str, arguments: dict[str, object]):
        for t in self._tools:
            if t.name == tool_name:
                await asyncio.sleep(t.delay)
                return t.result
        raise ValueError(f"tool {tool_name} not registered")


@pytest_asyncio.fixture
async def mock_mcp_manager():
    builtin_tools = [
        MockMCPTool(name="ros_get_current_time", description="获取当前时间"),
        MockMCPTool(name="ros_web_search", description="网络搜索", delay=0.1),
    ]
    mgr = MockMultiMCPManager(tools=builtin_tools)

    with patch("src.plugins.aihelper.aihelper_handles.mcp_manger", mgr):
        yield mgr


# ---------------------------------------------------------------------------
# Database fixture (aiosqlite)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    from sqlalchemy import text

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    from src.plugins.aihelper.models import AIHelperComments, Settings

    async with engine.begin() as conn:
        await conn.run_sync(Settings.metadata.create_all)
        await conn.run_sync(AIHelperComments.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        default_settings = Settings(
            id=1,
            user_id="0",
            url="https://api.openai.com/v1",
            api_key="sk-test",
            model_name="gpt-4",
            max_length=15,
            system="你是一个有用的AI助手。",
            temperature=1.0,
            is_enabled=True,
        )
        session.add(default_settings)

        test_settings = Settings(
            id=2,
            user_id="test_user",
            url="https://api.openai.com/v1",
            api_key="sk-test",
            model_name="gpt-4",
            max_length=15,
            system="你是测试助手。",
            temperature=0.7,
            is_enabled=True,
        )
        session.add(test_settings)
        await session.commit()

    async with async_session() as session:
        with patch("src.plugins.aihelper.aihelper_handles.semaphore_sql", asyncio.Semaphore(50)):
            yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Mock Bot / Event fixtures
# ---------------------------------------------------------------------------

class MockBot:
    def __init__(self, adapter_name: str = "OneBot V11"):
        self.adapter_name = adapter_name
        self.self_id = "mock_bot_001"
        self._sent_messages: list[dict] = []

    async def send(self, event, message, **kwargs):
        self._sent_messages.append({"event": event, "message": message, "kwargs": kwargs})


class MockEvent:
    def __init__(
        self,
        session_id: str = "test_session_001",
        session_type: str = "private",
        user_id: str = "test_user",
        group_id: str | None = None,
        message: str = "Hello",
        sender_role: str = "member",
    ):
        self.session_id = session_id
        self.session_type = session_type
        self.user_id = user_id
        self.group_id = group_id
        self.message = message
        self.sender = MagicMock()
        self.sender.role = sender_role

    def get_session_id(self) -> str:
        return self.session_id

    def get_user_id(self) -> str:
        return self.user_id

    def get_message(self) -> str:
        return self.message


@pytest_asyncio.fixture
async def mock_bot():
    return MockBot()


@pytest_asyncio.fixture
def make_event():
    def _make(
        session_id: str = "test_session_001",
        session_type: str = "private",
        user_id: str = "test_user",
        message: str = "Hello",
    ):
        return MockEvent(
            session_id=session_id,
            session_type=session_type,
            user_id=user_id,
            message=message,
        )
    return _make


# ---------------------------------------------------------------------------
# Shared utility: session helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def session_dicts(redis_client):
    from src.plugins.aihelper.session import (
        _Messages_dicts,
        _ai_switch,
        _config_settings,
    )

    _Messages_dicts.clear()
    _ai_switch.clear()
    _config_settings.clear()
    yield _Messages_dicts, _ai_switch, _config_settings
    _Messages_dicts.clear()
    _ai_switch.clear()
    _config_settings.clear()


@pytest_asyncio.fixture
def make_settings_row():
    from src.plugins.aihelper.models import Settings

    def _make(
        user_id: str = "test_user",
        url: str = "https://api.test/v1",
        api_key: str = "sk-test",
        model_name: str = "gpt-4",
        system: str = "你是有用的助手。",
        temperature: float = 1.0,
        is_enabled: bool = True,
    ):
        return Settings(
            user_id=user_id,
            url=url,
            api_key=api_key,
            model_name=model_name,
            max_length=15,
            system=system,
            temperature=temperature,
            is_enabled=is_enabled,
        )
    return _make
