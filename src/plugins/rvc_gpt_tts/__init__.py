from nonebot.plugin import PluginMetadata, get_plugin_config
from .config import Config

__plugin_meta__ = PluginMetadata(
    name = "rvc_gpt_tts",
    description = "图片识别插件",
    usage = "",
    config = Config,
)

_config = get_plugin_config(Config)
config = _config.rvc_gpt_tts

if config.is_enable:
    from .tts import *
    from .rvc_gpt_tts_data import *