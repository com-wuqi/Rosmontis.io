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
message_handle_loops = []


if config.is_enable:
    from .setupai import *
    from .chater import *
    from .backupHelper import *


    @driver.on_bot_connect
    async def startup(bot: Bot):
        task = asyncio.create_task(message_handle_loop(bot))
        message_handle_loops.append(task)


    @driver.on_shutdown
    async def shutdown():
        for task in message_handle_loops:
            task.cancel()
        await asyncio.gather(*message_handle_loops, return_exceptions=True)
