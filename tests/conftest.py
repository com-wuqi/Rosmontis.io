import os

os.environ["SENTRY_DSN"] = ""
os.environ["SENTRY_ENABLED"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ORM_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ[
    "APSCHEDULER_CONFIG"] = '{"apscheduler.jobstores":{"default":{"type":"sqlalchemy","url":"sqlite:///:memory:","tablename":"apscheduler_jobs"}}}'

import nonebot
import pytest
# 导入适配器
from nonebot.adapters.onebot.v11 import Adapter as onebot_v11_Adapter
from pytest_asyncio import is_async_test
from nonebug import NONEBOT_INIT_KWARGS

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
