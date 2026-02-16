from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata


from .config import Config
from .models import *
from .setupai import *
from .chater import *

__plugin_meta__ = PluginMetadata(
    name="aiHelper",
    description="",
    usage="",
    config=Config,

)

config = get_plugin_config(Config)
