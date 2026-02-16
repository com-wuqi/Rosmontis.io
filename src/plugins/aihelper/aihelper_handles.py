from httpx import AsyncClient
from sqlalchemy import select, update, delete
from .models import *
from nonebot.log import logger
from openai import AsyncOpenAI
from nonebot import require
import asyncio
require("nonebot_plugin_orm")


semaphore = asyncio.Semaphore(50)  # 限制最大并发数为50

async def get_model_names(key:str,url:str) -> List[str]:
    async with semaphore:
        client = AsyncOpenAI(base_url=url,api_key=key,timeout=10)
        try:
            # 异步调用模型列表接口
            response = await client.models.list()
            # 提取模型 ID 列表
            model_names = [model.id for model in response.data]
            return model_names
        except Exception as e:
            logger.error(e)
            return []

