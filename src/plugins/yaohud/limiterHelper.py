import asyncio
import time

import httpx
from nonebot.log import logger

from . import config
from .napcatqq_upload_stream import OneBotUploadTester as uploader

semaphore_download = asyncio.Semaphore(20)
semaphore_upload = asyncio.Semaphore(20)

class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        """
            令牌桶
        :param rate: 频率, 个/秒
        :param capacity: 桶大小, 最大允许多少突发
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity  # 初始满桶
        self.last_refill = time.monotonic()  # 单向时钟
        self._lock = asyncio.Lock()  # 锁

    async def acquire(self):
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill  # 计算时间差
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_refill = now  # 刚刚重新填充的桶
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


async def download_file(url: str, save_path: str):
    # 下载工具类
    _header = {"Content-Type": "application/x-www-form-urlencoded",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with semaphore_download:
        async with httpx.AsyncClient(headers=_header) as client:
            async with client.stream("GET", url) as response:
                try:
                    response.raise_for_status()  # 检查 HTTP 错误
                    with open(save_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                    return 0
                except Exception as e:
                    return -1


async def upload_file(path: str) -> str:
    async with semaphore_upload:
        upload = uploader(ws_url=config.upload_ws_url, access_token=config.upload_ws_token)
        await upload.connect()
        remote_path = await upload.upload_file_stream_batch(file_path=path, chunk_size=1024)
        await upload.disconnect()
        logger.debug("img remote_path: {}".format(remote_path))
        return remote_path
