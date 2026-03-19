from nonebot.log import logger
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
    _enabled_list = [config.is_enable_gpt_sovits, config.is_enable_qwen3_customvoice]
    if True in _enabled_list:
        logger.warning("self_build_tts 是实验性功能, 不做可用性保证, 有过时风险")
    from .message_handle import *
