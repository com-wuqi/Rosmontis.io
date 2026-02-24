import asyncio
import time

import httpx
from httpx import HTTPStatusError
from nonebot import require
from nonebot.log import logger

from . import config
from .sharedFuncs import TokenBucket, download_file, upload_file
from .signHelper import build_headers

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

_bucket_acg_adaptive = TokenBucket(rate=15, capacity=15)
_bucket_acg_ai = TokenBucket(rate=15, capacity=15)
_bucket_acg_r18 = TokenBucket(rate=100, capacity=100)
_semaphore_image = asyncio.Semaphore(60)


async def get_acg(img_type: str):
    """
    随机二次元图片
    :param img_type: 图片类型
    """
    if img_type == "adaptive":
        await _bucket_acg_adaptive.acquire()  # 限流：获取令牌
        url = config.base_url + "/api/acg/adaptive"
    elif img_type == "ai":
        await _bucket_acg_ai.acquire()
        url = config.base_url + "/api/acg/AI"
    elif img_type == "r18":
        await _bucket_acg_r18.acquire()
        url = config.base_url + "/api/v2/setu"
    else:
        return -1  # 未知类型
    async with _semaphore_image:
        async with httpx.AsyncClient(timeout=120) as client:
            headers = build_headers()
            body = {"key": config.api_key}
            try:
                response = await client.get(url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                # logger.debug(f"json : {data_json}")
                if img_type == "adaptive" or img_type == "ai":
                    photo_url: str = data_json["data"]["image_url"]
                elif img_type == "r18":
                    photo_url: str = data_json["data"]["url"]
                logger.debug(f"photo_url:{photo_url}")
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
