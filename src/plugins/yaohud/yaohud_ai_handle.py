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

bucket_index_tts2 = TokenBucket(rate=1 / 20, capacity=1)
_semaphore_ai = asyncio.Semaphore(20)


async def get_index_tts2(voice_txt: str, voice_from: str):
    await _semaphore_ai.acquire()
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
