import asyncio

import redis.asyncio as aioredis
from nonebot import Bot, get_driver, get_plugin_config
from nonebot.log import logger
from nonebot.plugin import PluginMetadata

from src.plugins.shared.adapter_utils import get_adapter_name

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
_bots: dict[str, Bot] = {}
message_handle_workers = None
message_handle_loop = None

_STREAM_INCOMING = "ai:incoming"
_STREAM_TASKS = "ai:tasks"
_GROUP = "aihelper"
_SESSION_PREFIX = "ai:session:"
_SESSION_TTL = config.redis_long_expire_time

def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. The bot has not started yet.")
    return _redis


if config.is_enable:
    from .backupHelper import *
    from .chater import *
    from .setupai import *

    @driver.on_startup
    async def init_infra():
        """初始化 Redis 和 Stream 消费组。若 bot 先于 Redis 连接则在此处补启动 worker。"""  # noqa: E501
        global _redis, message_handle_workers, message_handle_loop

        _redis = aioredis.from_url(config.redis_url, decode_responses=True)
        await _redis.ping()
        logger.info("Redis connected")

        for stream in (_STREAM_INCOMING, _STREAM_TASKS):
            try:
                await _redis.xgroup_create(stream, _GROUP, id="0", mkstream=True)
                logger.info(f"Consumer group '{_GROUP}' created for stream '{stream}'")
            except aioredis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(
                        f"Consumer group '{_GROUP}' "
                        f"already exists for stream '{stream}'"
                    )
                else:
                    raise

        if _bots and message_handle_workers is None:
            bot = next(iter(_bots.values()))
            message_handle_workers = MessageHandleWorkers(bot, _bots)
            await message_handle_workers.init_workers()
            message_handle_loop = asyncio.create_task(
                message_handle_workers.main_loop()
            )
            logger.info("Workers started from on_startup (bots connected before Redis)")

    @driver.on_bot_connect
    async def on_bot(bot: Bot):
        """注册 bot 实例，首次连接时启动 worker。若 Redis 未就绪则等待 on_startup 补启动。"""  # noqa: E501
        global _bots, message_handle_workers, message_handle_loop

        _bots[get_adapter_name(bot)] = bot

        if _redis is None or message_handle_workers is not None:
            return

        message_handle_workers = MessageHandleWorkers(bot, _bots)
        await message_handle_workers.init_workers()
        message_handle_loop = asyncio.create_task(message_handle_workers.main_loop())
        logger.info("Workers started from on_bot_connect")

    @driver.on_shutdown
    async def shutdown():
        global _redis, message_handle_workers, message_handle_loop

        try:
            if message_handle_workers is not None:
                await message_handle_workers.close_workers()
            if message_handle_loop is not None:
                message_handle_loop.cancel()
            if _redis is not None:
                await _redis.aclose()
                _redis = None
                logger.info("Redis connection closed")
        except asyncio.CancelledError:
            pass
