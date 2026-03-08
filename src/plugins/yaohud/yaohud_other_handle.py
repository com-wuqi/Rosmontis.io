import asyncio
from json import JSONDecodeError

import httpx
from httpx import HTTPStatusError
from nonebot import require
from nonebot.log import logger

from . import config
from .sharedFuncs import TokenBucket
from .signHelper import build_headers

require("nonebot_plugin_localstore")

bucket_whois = TokenBucket(rate=2 / 5, capacity=5)
_semaphore_other = asyncio.Semaphore(30)


async def whois(url: str):
    await bucket_whois.acquire()
    async with _semaphore_other:
        async with httpx.AsyncClient(timeout=120) as client:
            api_url = config.base_url + "/api/v5/whois"
            headers = build_headers()
            body = {"key": config.api_key, "msg": url}
            try:
                response = await client.get(url=api_url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()

                # 暂时不解析数据. 担心缺少字段 (其实是懒)
                return data_json["data"]

            except HTTPStatusError as e:
                logger.warning(f"/api/v5/whois failed with {e}")
                return -1
            except JSONDecodeError as e:
                logger.warning(f"/api/v5/whois failed with {e}")
                return -1
            except KeyError as e:
                logger.warning(f"/api/v5/whois failed with {e}")
                return -1
            except Exception as e:
                logger.warning(f"/api/v5/whois failed with {e}")
                return -1
