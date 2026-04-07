import asyncio
import time
from typing import Callable
from typing import List, Dict

import aiofiles
from nonebot.log import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from sqlalchemy import select

from .models import *

require("nonebot_plugin_orm")
from nonebot_plugin_orm import AsyncSession
# from . import config
from nonebot import require

require("src.plugins.mcp_support")
from src.plugins.mcp_support import mcp_manger

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
import src.plugins.public_apis as public_api

require("src.plugins.hooked_mcp_tools")
import src.plugins.hooked_mcp_tools as hooked_mcp_tools

checked_hooked_mcp_tools: Dict[str, Callable] = {}
for _key in hooked_mcp_tools.hooked_functions.keys():
    _func = hooked_mcp_tools.hooked_functions[_key]
    if callable(_func):
        checked_hooked_mcp_tools[_key] = _func
    else:
        logger.warning(f"hooked_mcp_tools key:{_key} ,function is not callable")
hooked_tools = hooked_mcp_tools.hooked_tools

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
        tools = mcp_manger.all_tools if mcp_manger is not None else []
        client = AsyncOpenAI(base_url=url, api_key=key, timeout=180)
        chat_completion = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools + hooked_tools,
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
    # 修改 config_id 的 is_enable 为 bool(target)
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


async def change_is_enable_by_id(config_id: int, session: AsyncSession, user_id: int) -> int | dict:
    # 将 用户 user_id 的 配置文件 config_id 修改为 True , 其他为 false
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == user_id)
        result = await session.execute(smt)
        data = result.scalars().all()
        if data is None:
            return -1
        _changed_to_true, _changed_to_false = 0, 0
        for item in data:
            if item.id == config_id:
                item.is_enabled = True
                _changed_to_true += 1
            else:
                _changed_to_false += 1
                item.is_enabled = False
        # session.add(data)
        await session.commit()
        return {"_changed_to_true": _changed_to_true, "_changed_to_false": _changed_to_false}


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


async def save_comments_to_file(_raw_msg: str, msg_type: str, user_id: int) -> str:
    # 保存信息到文件, 完成上传
    temp_path = store.get_plugin_cache_file(f"{user_id}_{msg_type}_{time.time()}.txt.bak")
    try:
        async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as f:
            await f.write(_raw_msg)
    except Exception as e:
        logger.error(f"save_comments_to_file failed: {e}")
        return ""

    _remote_path = await public_api.upload_file(str(temp_path))
    return _remote_path
