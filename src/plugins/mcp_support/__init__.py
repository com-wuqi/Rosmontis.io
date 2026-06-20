from nonebot import get_driver, on_command
from nonebot import get_plugin_config
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="mcp_support",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.mcpsupport
driver = get_driver()

from .MultiMCPManager import MultiMCPManager

if config.is_enable:
    mcp_manger = MultiMCPManager()
else:
    mcp_manger = None


@driver.on_startup
async def _init_mcp_support():
    if mcp_manger is not None:
        await mcp_manger.connect_all()


@driver.on_shutdown
async def _shutdown_mcp_support():
    if mcp_manger is not None:
        await mcp_manger.close_all()


_superusers = get_driver().config.superusers
_superusers = [int(k) for k in _superusers]
mcp_status = on_command("mcp-status")
mcp_reload = on_command("mcp-reload")  # 需要特权

@mcp_status.handle()
async def mcp_status_handle():
    if mcp_manger is not None:
        await mcp_status.finish(f"{mcp_manger.get_status()}")
    else:
        await mcp_status.finish("mcp is disabled")


@mcp_reload.handle()
async def mcp_reload_handle(event: MessageEvent):
    if (event.user_id not in _superusers) or (not isinstance(event, PrivateMessageEvent)):
        await mcp_reload.finish("Permission denied")
        return
    if mcp_manger is None:
        await mcp_reload.finish("mcp is disabled")
        return
    await mcp_reload.send("mcp is closing")
    await mcp_manger.close_all()
    await mcp_reload.send("mcp is starting")
    await mcp_manger.connect_all()
    await mcp_reload.finish("mcp is reloaded")
