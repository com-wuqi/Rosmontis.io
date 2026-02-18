from sqlalchemy import select, update, delete
from .models import *
from nonebot.log import logger
from openai import AsyncOpenAI
from nonebot import require
from typing import List, Dict
import asyncio
require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session


semaphore = asyncio.Semaphore(50)  # 网络限制最大并发数为50
semaphore_sql = asyncio.Semaphore(50) # 数据库最大并发50

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


async def send_messages_to_ai(key:str,url:str,model_name:str,messages:List[Dict[str,str]]) -> str:
    async with semaphore:
        client = AsyncOpenAI(base_url=url,api_key=key,timeout=60)
        chat_completion = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=1
        )
        return chat_completion.choices[0].message.content


async def get_config_by_id(sid: int,session: async_scoped_session):
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == sid)
        result = await session.execute(smt)
        row = result.scalars().first()
        if row is None:
            logger.warning("confifg not found, use default config")
            smt_default = select(Settings).where(Settings.id == 1)
            result_default = await session.execute(smt_default)
            row_default = result_default.scalars().first()
            if row_default is None:
                # 极端情况：默认配置不存在
                logger.error("数据库中没有 id=1 的默认配置，请检查数据初始化！")
                return {}
            return row_default
        return row


async def get_comments_by_id(sid: int,session: async_scoped_session):
    async with semaphore_sql:
        stmt = select(AIHelperComments).where(AIHelperComments.comment_id == sid)
        result = await session.execute(stmt)
        raw = result.scalars().first()
        return raw

