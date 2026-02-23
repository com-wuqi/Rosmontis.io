import asyncio
import time

import httpx
from httpx import HTTPStatusError
from nonebot import require
from nonebot.log import logger

from . import config
from .limiterHelper import TokenBucket, download_file, upload_file
from .signHelper import build_headers

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

_bucket_acg_adaptive = TokenBucket(rate=15, capacity=15)
_semaphore_image = asyncio.Semaphore(50)


async def get_acg_adaptive():
    """
    随机二次元图片
    """
    await _bucket_acg_adaptive.acquire()  # 限流：获取令牌
    async with _semaphore_image:
        async with httpx.AsyncClient() as client:
            url = config.base_url + "/api/acg/adaptive"
            headers = build_headers()
            body = {"key": config.api_key}
            try:
                response = await client.get(url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                photo_url: str = data_json["data"]["image_url"]
                file_jpg = store.get_plugin_cache_file(f"acg_adaptive-{time.time()}.jpg")
                _res = await download_file(url=photo_url, save_path=str(file_jpg))
                if _res == 0:
                    _remote_path = await upload_file(path=str(file_jpg))
                    file_jpg.unlink()  # 删除文件
                    return _remote_path  # 返回远程地址
                else:
                    return -1

            except HTTPStatusError as e:
                logger.warning(f"api/acg/adaptive failed with {e}")
                return -1
