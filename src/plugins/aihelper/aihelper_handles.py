import asyncio
from typing import List, Dict

from nonebot.log import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from sqlalchemy import select

from .models import *

require("nonebot_plugin_orm")
from nonebot_plugin_orm import AsyncSession
from . import config
from nonebot import require

require("src.plugins.aiagents")
import src.plugins.aiagents as agents

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


async def send_messages_to_ai(key:str,url:str,model_name:str,temperature:float,messages:List[Dict[str,str]]) -> ChatCompletionMessage:
    async with semaphore:
        tools = [agents.get_dict_by_name(name="GET_TIME_TOOL"), ]
        if config.is_enable_websearch:
            tools.append(agents.get_dict_by_name(name="WEB_SEARCH_TOOL"))
        if config.is_enable_e2b_sandbox:
            tools.append(agents.get_dict_by_name(name="E2B_SANDBOX_TOOL"))

        client = AsyncOpenAI(base_url=url,api_key=key,timeout=60)
        chat_completion = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools or None,
            temperature=temperature
        )
        return chat_completion.choices[0].message


async def get_config_by_id(sid: int, session: AsyncSession):
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == sid, Settings.is_enabled == 1)
        result = await session.execute(smt)
        row = result.scalars().first()
        # 一般就提取第一个配置文件
        if row is None:
            logger.warning("config not found, use default config : 当前配置未找到，使用默认配置")
            smt_default = select(Settings).where(Settings.id == 1)
            result_default = await session.execute(smt_default)
            row_default = result_default.scalars().first()
            if row_default is None:
                # 极端情况：默认配置不存在
                logger.error("数据库中没有 id=1 的默认配置，请检查数据初始化！")
                return {}
            return row_default
        return row


async def get_all_config_by_id(sid: int, session: AsyncSession):
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == sid)
        result = await session.execute(smt)
        row = result.scalars().all()
        return row


async def del_config_by_config_id_and_uid(config_id: int, uid: int, session: AsyncSession):
    async with semaphore_sql:
        # 保证只能操作自己的配置
        smt = select(Settings).where(Settings.id == config_id, Settings.user_id == uid)
        result = await session.execute(smt)
        _res = result.scalar_one_or_none()
        if _res is None:
            return -1
        else:
            await session.delete(_res)
            await session.commit()
            return 0


async def switch_is_enable_by_id(config_id: int, session: AsyncSession, target: bool, user_id: int) -> int:
    async with semaphore_sql:
        smt = select(Settings).where(Settings.id == config_id, Settings.user_id == user_id)
        result = await session.execute(smt)
        data = result.scalars().first()
        if data is None:
            return -1
        data.is_enabled = target
        session.add(data)
        await session.commit()
        return 0


async def get_comments_by_id(sid: int, session: AsyncSession):
    async with semaphore_sql:
        stmt = select(AIHelperComments).where(AIHelperComments.comment_id == sid)
        result = await session.execute(stmt)
        raw = result.scalars().first()
        return raw


async def save_comments_by_id(sid: int, session: AsyncSession, msg: str):
    async with semaphore_sql:
        raw = AIHelperComments(comment_id=sid, message=msg)
        session.add(raw)
        await session.commit()


async def update_comments_by_id(sid: int, session: AsyncSession, msg: str) -> int:
    async with semaphore_sql:
        stmt = select(AIHelperComments).where(AIHelperComments.comment_id == sid)
        result = await session.execute(stmt)
        raw = result.scalars().first()
        if raw is None:
            return -1
        raw.message = msg
        session.add(raw)
        await session.commit()
        return 0


async def get_all_comment_ids(session: AsyncSession) -> List[int]:
    async with semaphore_sql:
        stmt = select(AIHelperComments.comment_id)
        result = await session.execute(stmt)
        id_list = list(result.scalars().all())
        return id_list

