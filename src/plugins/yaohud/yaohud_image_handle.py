import asyncio

import httpx
from httpx import HTTPStatusError
from nonebot import require
from nonebot.log import logger

from . import config
from .limiterHelper import TokenBucket
from .signHelper import build_headers

require("nonebot_plugin_localstore")

_bucket_acg_adaptive = TokenBucket(rate=15, capacity=15)
_semaphore_image = asyncio.Semaphore(50)


async def get_acg_adaptive() -> str:
    """
    随机二次元图片
    :return:
    """
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
                return photo_url
            except HTTPStatusError as e:
                logger.warning(f"api/acg/adaptive failed with {e}")
                return ""
