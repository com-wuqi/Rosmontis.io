"""
Root conftest: initializes NoneBot with test configuration before any imports.

The ``nonebot.init()`` call MUST happen at module load time (before any plugin
imports), otherwise fixtures that reference plugin modules will fail with
"NoneBot has not been initialized."
"""

import os

os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("SENTRY_SEND_DEFAULT_PII", "false")
os.environ.setdefault("ALEMBIC_STARTUP_CHECK", "false")
os.environ.setdefault("APSCHEDULER_AUTOSTART", "false")

import nonebot

nonebot.init(
    driver="~fastapi",
    host="127.0.0.1",
    port=8080,
    log_level="WARNING",
    command_start=["/"],
    superusers={"1001"},
    environment="test",
    sqlalchemy_database_url="sqlite+aiosqlite://",
    localstore_use_cwd=True,
    sentry_dsn="",
    sentry_send_default_pii="false",
    alembic_startup_check=False,
    apscheduler_autostart=False,
    aihelper__is_enable=True,
    aihelper__tools_max_once_calls=5,
    aihelper__is_enable_tool_prompt=False,
    aihelper__is_enable_design_prompts=False,
    aihelper__api_timeout=30,
    aihelper__message_queue_timeout=1,
    aihelper__message_queue_max_size=3,
    aihelper__max_workers=4,
    aihelper__redis_url="redis://localhost:6379/0",
    aihelper__redis_long_expire_time=3600,
    ai_file_reader__is_enable=False,
    yaohud__is_enable=False,
    mcpsupport__is_enable=True,
    publicapi__is_enable_upload=False,
    self_build_tts__is_enable=False,
    hooked_mcp___=True,
    onebot_ws_urls=[],
    onebot_access_token="test",
    selfhostaiusers=[],
)

pytest_plugins = []
