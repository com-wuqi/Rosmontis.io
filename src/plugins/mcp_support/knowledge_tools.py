import asyncio
from typing import List

from openai import AsyncClient


async def get_embedding(sem, txt: str, url: str, key: str, model_name: str, timeout=300):
    async with sem:
        client = AsyncClient(base_url=url, api_key=key, timeout=timeout)
        text = txt.strip()
        res = await client.embeddings.create(input=[text], model=model_name)
        return res


async def get_all_embedding(sems: int, txt_list: List[str], url: str, key: str, model_name: str, timeout=300):
    sem = asyncio.Semaphore(sems)
    workers = [get_embedding(sem, txt, url, key, model_name, timeout) for txt in txt_list]
    result = await asyncio.gather(*workers, return_exceptions=True)
    return result
