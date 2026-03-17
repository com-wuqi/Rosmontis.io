from nonebot.plugin import PluginMetadata, get_plugin_config
from .config import Config
from nonebot import logger

__plugin_meta__ = PluginMetadata(
    name = "self_build_tts",
    description = "文字转语音功能",
    usage = "",
    config = Config,
)

_config = get_plugin_config(Config)
config = _config.self_build_tts

if config.is_enable:
    # 前置校验
    if not config.self_tts_api_url:
        logger.error("未检测到url")
        raise ValueError("tts_api_url 未配置!")
    if not config.self_ref_audio_path:
        logger.error("未检测到参考音频路径")
        raise ValueError("ref_audio_path 未配置!")
    if not config.self_prompt_text:
        logger.error("未检测到参考音频文本")
        raise ValueError("prompt_text 未配置!")
    # 校验完成再导入
    from .self_build_tts_data import *
    from .self_build_tts_audio import *