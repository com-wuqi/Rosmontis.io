from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="qzone_handle",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.qzone_handle

if config.is_enable:
    from .message_handle import *
