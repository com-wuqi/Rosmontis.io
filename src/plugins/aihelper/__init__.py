from nonebot import get_plugin_config, get_driver
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
message_handle_workers = None
message_handle_loop = None

if config.is_enable:
    from .setupai import *
    from .chater import *
    from .backupHelper import *

    @driver.on_bot_connect
    async def startup(bot: Bot):
        global message_handle_workers, message_handle_loop
        message_handle_workers = MessageHandleWorkers(bot)
        await message_handle_workers.init_workers()
        message_handle_loop = asyncio.create_task(message_handle_workers.main_loop())



    @driver.on_shutdown
    async def shutdown():
        global message_handle_workers, message_handle_loop
        await message_handle_workers.close_workers()
        message_handle_loop.cancel()
