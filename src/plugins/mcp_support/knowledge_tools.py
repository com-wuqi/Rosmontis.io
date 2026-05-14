import asyncio
import json
# 加载 json
import os
from typing import List

from openai import AsyncClient

_work_dir = os.path.abspath(os.path.dirname(__file__))
_md_dir = os.path.join(_work_dir, "knowledge")
_file_list = [
    os.path.join(_md_dir, f) for f in sorted(os.listdir(_md_dir))
    if os.path.isfile(os.path.join(_md_dir, f))
       and f.endswith(".json")
]
raw_jsons = []
# 每个文件的json对象是其中的一个元素. 这里缺失类型注释！
for _file in _file_list:
    try:
        with open(_file, "r", encoding="utf-8") as f:
            raw_jsons.append(json.load(f))
    except FileNotFoundError as e:
        pass
    except json.JSONDecodeError as e:
        pass
    except Exception as e:
        pass


async def get_embedding(
        txt: str, url: str | None,
        key: str | None, model_name: str | None,
        timeout=300, sem: asyncio.Semaphore = None,
        use_sem: bool = False  # 使用 asyncio.Semaphore
):
    if use_sem:
        async with sem:
            client = AsyncClient(base_url=url, api_key=key, timeout=int(timeout))
            text = txt.strip()
            res = await client.embeddings.create(input=[text], model=model_name)
            return res.data[0].embedding
    else:
        client = AsyncClient(base_url=url, api_key=key, timeout=int(timeout))
        text = txt.strip()
        res = await client.embeddings.create(input=[text], model=model_name)
        return res.data[0].embedding



async def get_all_embedding(sem: int, txt_list: List[str], url: str | None, key: str | None, model_name: str | None,
                            timeout=300):
    # 提供条目合集的向量化, 这里的 keys 对应 ids
    sems = asyncio.Semaphore(sem)
    workers = [
        get_embedding(
            sem=sems, txt=txt, url=url, key=key, model_name=model_name, timeout=int(timeout),
            use_sem=True
        )
        for txt in txt_list
    ]
    result = await asyncio.gather(*workers, return_exceptions=False)
    return result
