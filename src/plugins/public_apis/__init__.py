from nonebot import get_plugin_config
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

from .napcatqq_upload_stream import OneBotUploadTester
from .shared_funcs import *
