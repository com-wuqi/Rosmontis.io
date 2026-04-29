from typing import Dict, Callable

from nonebot import get_plugin_config
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="ai_file_reader",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.ai_file_reader

from .image_reader import *

message_matcher: Dict[Callable, Callable] = {
    is_supported_image: read_image
}


async def ai_file_reader(segment: MessageSegment, bot: Bot) -> str:
    # 这里根据文件类型进行分流, 异步操作, 返回描述
    result_msg = "暂不支持的信息类型"
    if not config.is_enable:
        return result_msg

    if segment.type == "file":
        file_id = segment.data.get("file_id", None)
        # 文件的唯一ID
        file_name = segment.data.get("file", None)
        # 文件名
        if (file_id is None) or (file_name is None):
            return result_msg

        file_info = await bot.call_api("get_private_file_url", file_id=file_id)
        file_url = file_info["url"]

    else:
        file_name = segment.data.get("file", None)
        file_url = segment.data.get("url", None)
        if (file_url is None) or (file_name is None):
            return result_msg

    for key, value in message_matcher.items():
        if key(file_name):
            _result_msg = await value(file_name, file_url)
            result_msg = _result_msg if _result_msg else result_msg
            break

    return result_msg
