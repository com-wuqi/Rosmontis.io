from nonebot.plugin import PluginMetadata, get_plugin_config

from .config import Config

__plugin_meta__ = PluginMetadata(
    name = "self_build_tts",
    description = "文字转语音功能",
    usage = "",
    config = Config,
)

_config = get_plugin_config(Config)
config = _config.self_build_tts

if config.is_enable:
    from .tts_api_handle import *
    from .message_handle import *
