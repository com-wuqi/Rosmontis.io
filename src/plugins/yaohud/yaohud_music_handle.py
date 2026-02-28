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

_bucket_netease_music = TokenBucket(rate=20, capacity=20)  #
_bucket_qq_music = TokenBucket(rate=20, capacity=20)
_bucket_kuwo_music = TokenBucket(rate=20, capacity=20)

_semaphore_music = asyncio.Semaphore(60)


async def get_common_music(api_type: str, msg_type: str, msg: str, n: int = 1, g: int = 15):
    """
        通用音乐接口
    :param api_type: 接口类型, 支持 "wyvip" "qq_plus" "kuwo"
    :param msg_type: 类型, "search" or "get"
    :param msg: 搜索内容, 必须
    :param n: 选择的序号, 仅当 msg_type = "get" 时候生效
    :param g: 搜索结果数量
    :return: str | Path
    """
    if api_type == "wyvip":
        url = config.base_url + "/api/music/wyvip"
        body = {"key": config.api_key, "msg": msg, "level": config.wyvip_level, "g": g}
        if msg_type == "get":
            body["n"] = n
        await _bucket_netease_music.acquire()

    elif api_type == "qq_plus":
        url = config.base_url + "/api/music/qq_plus"
        body = {"key": config.api_key, "msg": msg, "size": config.qqmusic_level}
        if msg_type == "get":
            body["n"] = n
        await _bucket_qq_music.acquire()

    elif api_type == "kuwo":
        url = config.base_url + "/api/music/kuwo"
        body = {"key": config.api_key, "msg": msg, "size": config.kuwo_size}
        if msg_type == "get":
            body["n"] = n
        await _bucket_kuwo_music.acquire()

    else:
        return -1

    async with _semaphore_music:
        async with httpx.AsyncClient(timeout=120) as client:
            headers = build_headers()
            try:
                response = await client.get(url, headers=headers, params=body)
                response.raise_for_status()
                data_json = response.json()
                # logger.debug(data_json)
                if msg_type == "search":
                    return data_json["data"]["simplify"]

                if api_type == "wyvip":
                    music_url: str = data_json["data"]["vipmusic"]["url"]
                    _music = store.get_plugin_cache_file(f"wyvip-{data_json["data"]["name"]}-{time.time()}.mp3")
                elif api_type == "qq_plus":
                    music_url: str = data_json["data"]["music_url"]["url"]
                    _music = store.get_plugin_cache_file(f"qq_plus-{data_json["data"]["name"]}-{time.time()}.mp3")
                elif api_type == "kuwo":
                    music_url: str = data_json["data"]["vipmusic"]["url"]
                    _music = store.get_plugin_cache_file(f"kuwo-{data_json["data"]["name"]}-{time.time()}.mp3")

                logger.debug(f"music url: {music_url}")

                _res = await download_file(url=music_url, save_path=str(_music))
                if _res == 0:
                    _remote_path = await upload_file(path=str(_music))
                    _music.unlink()  # 删除文件
                    return _remote_path  # 返回远程地址
                else:
                    return -1
            except HTTPStatusError as e:
                logger.warning(f"get_common_music failed with {e}")
                return -1
            except JSONDecodeError as e:
                logger.warning(f"get_common_music failed with {e}")
                return -1
            except KeyError as e:
                logger.warning(f"get_common_music failed with {e}")
                return -1

