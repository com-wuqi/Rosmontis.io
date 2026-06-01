import asyncio
import time
import traceback
from pathlib import Path

from markitdown import MarkItDown
from nonebot import require
from nonebot.log import logger

from . import config

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
import src.plugins.public_apis as public_api

_token_bucket = public_api.TokenBucket(rate=config.markitdown_rate_limit, capacity=config.markitdown_rate_limit)

# markitdown[docx,pdf,pptx,xls,xlsx]==0.1.6

_MARKITDOWN_SUPPORTED_EXT = {
    ".png", ".jpg", ".jpeg",
    ".webp", ".gif", ".py",
    ".java"
}


def get_a_md() -> MarkItDown:
    md = MarkItDown(
        enable_plugins=None,
        enable_builtins=None
    )
    return md


def _sync_convert_worker(file_path: str) -> str:
    md = get_a_md()
    result = md.convert(file_path)
    return result.text_content


async def async_convert(source):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(public_api.global_progress_pool, _sync_convert_worker, source)
    return result


def is_markitdown_supported_file(s: str) -> bool:
    """
    判断文件后缀名是否是支持转换的文件
    :param s: 文件名称，包含后缀
    :return: bool, 是否匹配
    """
    return Path(s).suffix.lower() in _MARKITDOWN_SUPPORTED_EXT


async def read_markitdown_file(file_name: str, file_url: str) -> str | None:
    await _token_bucket.acquire()
    file_path = store.get_plugin_cache_file(f"{time.time()}-{file_name}")
    _return = None
    try:
        _try_download = await public_api.download_file(file_url, str(file_path))
        if _try_download != 0:
            raise RuntimeError("download failed")
        _return = await async_convert(file_path)
        logger.debug(f"read markitdown success:\n{_return}")
    except Exception as e:
        logger.warning(f"failed to read markitdown file: {e}")
        traceback.print_exc()
    finally:
        file_path.unlink(missing_ok=True)
    return _return
