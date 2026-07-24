from collections.abc import Callable
from types import CoroutineType
from typing import Any

from nonebot import get_plugin_config
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel

from src.plugins.shared.adapter_utils import download_to_cache, get_attachment_segments

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
    """文件阅读器配置项。segment_type 用于 Feishu 图片等无扩展名附件的类型匹配。"""
    is_enable: bool
    matcher: Callable[[str], bool]
    runner: Callable[[str, str], CoroutineType[Any, Any, str | None]]
    segment_type: str = ""


from . import image_reader as image_reader
from . import markitdown_reader as md_reader

filereader_config: list[FileReaderConfig] = [
    FileReaderConfig(
        is_enable=config.is_enable_image,
        matcher=image_reader.is_supported_image,
        runner=image_reader.read_image,
        segment_type="image",
    ),
    FileReaderConfig(
        is_enable=config.is_enable_markitdown,
        matcher=md_reader.is_markitdown_supported_file,
        runner=md_reader.read_markitdown_file,
    ),
]


async def get_file_from_event(event: Event, bot: Bot) -> tuple[int, str]:
    """从事件中提取附件，匹配阅读器解析后返回 (文件数, 文本内容)。

    支持 segment_type + 扩展名双重匹配。
    """
    if not config.is_enable:
        return 0, ""

    attachments = get_attachment_segments(event)
    reader_configs = [r for r in filereader_config if r.is_enable]
    if not reader_configs:
        return 0, ""

    _msg_parts: list[str] = []
    _counter = 0
    for att in attachments:
        file_name = att.get("file_name", "")
        att_type = att.get("type", "")

        matched_reader = next(
            (
                r
                for r in reader_configs
                if r.matcher(file_name)
                or (r.segment_type and r.segment_type == att_type)
            ),
            None,
        )
        if matched_reader is None:
            continue

        file_url = att.get("file_url")
        if file_url:
            result = await matched_reader.runner(file_name, file_url)
            if result:
                _msg_parts.append(result)
                _counter += 1
            else:
                logger.warning(f".runner failed {file_name}")
            continue

        local_path = await download_to_cache(bot, att)
        if local_path is None:
            logger.warning(f"download failed for {file_name}")
            continue

        result = await matched_reader.runner(file_name, f"file://{local_path}")
        if result:
            _msg_parts.append(result)
            _counter += 1

    return _counter, "\n".join(_msg_parts)
