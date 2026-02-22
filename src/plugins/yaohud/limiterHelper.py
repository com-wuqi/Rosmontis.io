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
