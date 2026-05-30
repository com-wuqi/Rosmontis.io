import os
from pathlib import Path

import nonebot
import pytest
from dotenv import load_dotenv
# 导入适配器
from nonebot.adapters.onebot.v11 import Adapter as onebot_v11_Adapter
from nonebug import NONEBOT_INIT_KWARGS
from pytest_asyncio import is_async_test


@pytest.fixture(scope="session", autouse=True)
def load_env_for_tests():
    """在测试开始前加载项目根目录的 .env 文件"""
    # 定位项目根目录（假设 tests/ 在项目根目录下）
    root_dir = Path(__file__).parent.parent
    env_file = root_dir / ".env.prod"

    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
        print(f"✓ Loaded .env from {env_file}")
    else:
        # 备选：尝试加载 .env.example
        example_file = root_dir / ".env.example"
        if example_file.exists():
            load_dotenv(dotenv_path=example_file, override=True)
            print(f"✓ Loaded .env.example from {example_file}")

    os.environ["SENTRY_DSN"] = ""
    os.environ["SENTRY_ENABLED"] = "false"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["ORM_SKIP_MIGRATION_CHECK"] = "true"
    os.environ[
        "APSCHEDULER_CONFIG"] = '{"apscheduler.jobstores":{"default":{"type":"sqlalchemy","url":"aiosqlite:///:memory:","tablename":"apscheduler_jobs"}}}'
    yield



def pytest_configure(config: pytest.Config):
    config.stash[NONEBOT_INIT_KWARGS] = {"secret": os.getenv("INPUT_SECRET")}


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init():
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(onebot_v11_Adapter)

    # 加载插件
    nonebot.load_from_toml("pyproject.toml")
