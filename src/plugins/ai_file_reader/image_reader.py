import re
import time

from nonebot import require

from . import config

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
from src.plugins.public_apis import TokenBucket, download_file

_token_bucket = TokenBucket(rate=config.image_ai_rate_limit, capacity=config.image_ai_rate_limit)

def is_supported_image(s: str) -> bool:
    """
    判断文件后缀名是否是 openai 支持的图片
    :param s: 图片名称，包含后缀
    :return: bool, 是否匹配
    """
    pattern = r"\.(png|jpe?g|webp|gif)(\?.*)?$"
    return bool(re.search(pattern, s.strip(), re.IGNORECASE))


async def read_image(file_name: str, file_url: str) -> str | None:
    await _token_bucket.acquire()
    image_path = store.get_plugin_cache_file(f"{time.time()}-{file_name}")
    _try_download = await download_file(file_url, str(image_path))
