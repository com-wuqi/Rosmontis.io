import asyncio
import time

from nonebot.log import logger

from . import config
from .napcatqq_upload_stream import OneBotUploadTester

semaphore_upload = asyncio.Semaphore(10)


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


async def upload_file(path: str) -> str:
    if not config.is_enable_upload:
        return path
    async with semaphore_upload:
        upload = OneBotUploadTester()
        is_connected = False
        try:
            await upload.connect()
            is_connected = True
            remote_path = await upload.upload_file_stream_batch(file_path=path, chunk_size=1024 * 1024)
            await upload.disconnect()
            logger.debug("remote_path: {}".format(remote_path))
            return remote_path
        except Exception as e:
            logger.error("failed to upload file: {}".format(e))
            if is_connected:
                try:
                    await upload.disconnect()
                except Exception as e:
                    logger.error("failed to disconnect: {}".format(e))
            return ""
