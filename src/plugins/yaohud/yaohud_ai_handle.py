import asyncio
import time
from json import JSONDecodeError

import httpx
from httpx import HTTPStatusError
from nonebot import require
from nonebot.log import logger

from . import config
from .sharedFuncs import TokenBucket, download_file, upload_file
from .signHelper import build_headers

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

bucket_index_tts2 = TokenBucket(rate=1 / 20, capacity=1)
bucket_yaohu_picture = TokenBucket(rate=1 / 40, capacity=1)
bucket_weijin = TokenBucket(rate=20, capacity=20)  # 高性能违禁词检验
_semaphore_ai = asyncio.Semaphore(60)


async def get_index_tts2(voice_txt: str, voice_from: str):
    await bucket_index_tts2.acquire()
    async with _semaphore_ai:
        async with httpx.AsyncClient(timeout=120) as client:
            url = config.base_url + "/api/model/index_tts2"
            headers = build_headers()
            body = {"key": config.api_key, "text": voice_txt, "voice": voice_from}
            try:
                response = await client.get(url=url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                mp3_url: str = data_json["data"]["data"]["url"]
                file_mp3 = store.get_plugin_cache_file(f"index_tts2-{time.time()}.mp3")
                _res = await download_file(url=mp3_url, save_path=str(file_mp3))
                if _res == 0:
                    _remote_path = await upload_file(path=str(file_mp3))
                    file_mp3.unlink()
                    return _remote_path
                else:
                    return -1
            except HTTPStatusError as e:
                logger.warning(f"/api/model/index_tts2 failed with {e}")
                return -1
            except JSONDecodeError as e:
                logger.warning(f"/api/model/index_tts2 failed with {e}")
                return -1
            except KeyError as e:
                logger.warning(f"/api/model/index_tts2 failed with {e}")
                return -1


async def get_yaohu_picture(txt: str):
    await bucket_yaohu_picture.acquire()
    async with _semaphore_ai:
        async with httpx.AsyncClient(timeout=180) as client:
            url = config.base_url + "/api/model/yaohu-picture"
            headers = build_headers()
            body = {"key": config.api_key, "text": txt}
            try:
                response = await client.get(url=url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                logger.debug(f"yaohu_picture : {data_json}")
                png_url: str = data_json["local_image_urls"][0]
                file_png = store.get_plugin_cache_file(f"yaohu_ai_picture-{time.time()}.jpg")
                _res = await download_file(url=png_url, save_path=str(file_png))
                if _res == 0:
                    _remote_path = await upload_file(path=str(file_png))
                    file_png.unlink()
                    return _remote_path
                else:
                    return -1

            except HTTPStatusError as e:
                logger.warning(f"/api/model/yaohu-picture failed with {e}")
                return -1
            except JSONDecodeError as e:
                logger.warning(f"/api/model/yaohu-picture failed with {e}")
                return -1
            except KeyError as e:
                logger.warning(f"/api/model/yaohu-picture failed with {e}")
                return -1


async def get_weijin(txt: str) -> bool:
    await bucket_weijin.acquire()
    async with _semaphore_ai:
        async with httpx.AsyncClient(timeout=60) as client:
            url = config.base_url + "/api/v5/weijin"
            headers = build_headers()
            body = {"key": config.api_key, "text": txt, "yange": "no"}
            try:
                response = await client.get(url=url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                if data_json["data"]["typetext"] == "正常":
                    return True
                else:
                    logger.warning(f"/api/v5/weijin failed with {data_json}")
                    return False
            except Exception as e:
                logger.warning(f"/api/v5/weijin failed with {e}")
                return False
