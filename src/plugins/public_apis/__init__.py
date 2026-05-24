from concurrent.futures import ProcessPoolExecutor

from nonebot import get_plugin_config, get_driver
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="public_apis",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.publicapi
driver = get_driver()
global_progress_pool: ProcessPoolExecutor = None

from .napcatqq_upload_stream import OneBotUploadTester
from .shared_funcs import *


@driver.on_startup
async def startup():
    global global_progress_pool
    global_progress_pool = ProcessPoolExecutor(max_workers=config.global_progress_pool_max_workers)
    logger.debug("global_progress_pool max_workers={}".format(config.global_progress_pool_max_workers))


@driver.on_shutdown
async def shutdown():
    global global_progress_pool
    global_progress_pool.shutdown(wait=True, cancel_futures=True)
