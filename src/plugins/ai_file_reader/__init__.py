from types import CoroutineType
from typing import Callable, Any

from nonebot import get_plugin_config
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="ai_file_reader",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.ai_file_reader


class FileReaderConfig(BaseModel):
    is_enable: bool
    matcher: Callable[[str], bool]
    runner: Callable[[str, str], CoroutineType[Any, Any, str | None]]


from . import image_reader as image_reader
from . import markitdown_reader as md_reader

filereader_config: list[FileReaderConfig] = [
    FileReaderConfig(
        is_enable=config.is_enable_image,
        matcher=image_reader.is_supported_image,
        runner=image_reader.read_image
    ),
    FileReaderConfig(
        is_enable=config.is_enable_markitdown,
        matcher=md_reader.is_markitdown_supported_file,
        runner=md_reader.read_markitdown_file
    )

]

async def get_file_from_event(event: MessageEvent, bot: Bot) -> tuple[int, str]:
    _msg = ""
    _counter = 0
    for segment in event.message:
        logger.debug("segment.data : {}".format(segment.data))
        try:
            _read_file = await ai_file_reader(segment, bot)
            _msg = _msg + "\n" + _read_file
            _counter += 1
        except Exception as e:
            logger.warning(f"读取失败: {e}")
    return _counter, _msg


async def ai_file_reader(segment: MessageSegment, bot: Bot) -> str:
    # 这里根据文件类型进行分流, 异步操作, 返回描述
    result_msg = "暂不支持的信息类型"
    if not config.is_enable:
        return result_msg

    message_type = ""

    if segment.type == "file":
        file_id = segment.data.get("file_id", None)
        # 文件的唯一ID
        file_name = segment.data.get("file", None)
        # 文件名
        if (file_id is None) or (file_name is None):
            return result_msg
        message_type = "file_id"
        file_url = None

    else:
        file_name = segment.data.get("file", None)
        file_url = segment.data.get("url", None)
        if (file_url is None) or (file_name is None):
            return result_msg
        message_type = "file_url"
        file_id = None

    _reader_configs = [_ for _ in filereader_config if _.is_enable]
    for _r_config in _reader_configs:
        if _r_config.matcher(file_name):
            if message_type == "file_id":
                file_info = await bot.call_api("get_private_file_url", file_id=file_id)
                file_url = file_info["url"]
            _result_msg = await _r_config.runner(file_name, file_url)
            # logger.debug(f"_result_msg: {_result_msg}")
            # logger.debug(f"_result_msg type: {type(_result_msg)}")
            if _result_msg is None:
                logger.warning(f"_result_msg is None with file {file_name}")
            else:
                result_msg = _result_msg
            break
    return result_msg
