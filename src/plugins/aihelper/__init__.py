import redis.asyncio as aioredis
from nonebot import get_driver, get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config
from .models import *

__plugin_meta__ = PluginMetadata(
    name="aiHelper",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.aihelper
driver = get_driver()

_redis: aioredis.Redis | None = None
message_handle_workers = None
message_handle_loop = None

_STREAM_INCOMING = "ai:incoming"
_STREAM_TASKS = "ai:tasks"
_GROUP = "aihelper"


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. The bot has not started yet.")
    return _redis


if config.is_enable:
    from .backupHelper import *
    from .chater import *
    from .setupai import *

    @driver.on_bot_connect
    async def startup(bot: Bot):
        global _redis, message_handle_workers, message_handle_loop

        if _redis is None:
            _redis = aioredis.from_url(config.redis_url, decode_responses=True)
            await _redis.ping()
            logger.info(f"Redis connected: {config.redis_url}")

        for stream in (_STREAM_INCOMING, _STREAM_TASKS):
            try:
                await _redis.xgroup_create(stream, _GROUP, id="0", mkstream=True)
                logger.info(f"Consumer group '{_GROUP}' created for stream '{stream}'")
            except aioredis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group '{_GROUP}' already exists for stream '{stream}'")
                else:
                    raise

        if message_handle_workers is None:
            message_handle_workers = MessageHandleWorkers(bot)
            await message_handle_workers.init_workers()
        if message_handle_loop is None:
            message_handle_loop = asyncio.create_task(message_handle_workers.main_loop())

    @driver.on_shutdown
    async def shutdown():
        global _redis, message_handle_workers, message_handle_loop

        if message_handle_workers is not None:
            await message_handle_workers.close_workers()
        if message_handle_loop is not None:
            message_handle_loop.cancel()
        if _redis is not None:
            await _redis.aclose()
            _redis = None
            logger.info("Redis connection closed")
