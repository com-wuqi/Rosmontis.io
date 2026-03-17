import asyncio

import aiofiles
import httpx
from nonebot import require
from nonebot.log import logger

require("src.plugins.public_apis")
import src.plugins.public_apis as public_apis

semaphore_download = asyncio.Semaphore(20)

TokenBucket = public_apis.TokenBucket


async def download_file(url: str, save_path: str):
    # 下载工具类
    _header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",  # 包含所有现代压缩算法
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }
    async with semaphore_download:
        async with httpx.AsyncClient(headers=_header, http2=True, follow_redirects=True, max_redirects=5,
                                     timeout=120) as client:
            async with client.stream("GET", url) as response:
                try:
                    response.raise_for_status()  # 检查 HTTP 错误
                    async with aiofiles.open(save_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=262144):
                            await f.write(chunk)
                    return 0
                except Exception as e:
                    logger.warning(e)
                    return -1


async def upload_file(path: str) -> str:
    _res = await public_apis.upload_file(path)
    return _res
