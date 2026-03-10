import asyncio
import time


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


_bucket_e2b = None
_bucket_websearch = None
_semaphore_websearch = None
_semaphore_e2b = None


def get_websearch_semaphore():
    global _semaphore_websearch
    if _semaphore_websearch is None:
        _semaphore_websearch = asyncio.Semaphore(5)
    return _semaphore_websearch


def get_semaphore_e2b():
    global _semaphore_e2b
    if _semaphore_e2b is None:
        _semaphore_e2b = asyncio.Semaphore(5)
    return _semaphore_e2b


def get_bucket_e2b():
    global _bucket_e2b
    if _bucket_e2b is None:
        _bucket_e2b = TokenBucket(rate=1, capacity=1)
    return _bucket_e2b


def get_bucket_websearch():
    global _bucket_websearch
    if _bucket_websearch is None:
        _bucket_websearch = TokenBucket(rate=3, capacity=5)
    return _bucket_websearch
