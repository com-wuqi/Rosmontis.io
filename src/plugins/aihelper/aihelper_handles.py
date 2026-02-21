import asyncio
from typing import List, Dict

from nonebot.log import logger
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from sqlalchemy import select

from .models import *

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session
from . import config
from .tools import *
import httpx

semaphore = asyncio.Semaphore(50)  # 网络限制最大并发数为50
semaphore_sql = asyncio.Semaphore(50) # 数据库最大并发50
semaphore_websearch = asyncio.Semaphore(50) # 网络搜索最大并发

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
        client = AsyncOpenAI(base_url=url,api_key=key,timeout=60)
        chat_completion = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=[WEB_SEARCH_TOOL],
            temperature=temperature
        )
        return chat_completion.choices[0].message


async def get_config_by_id(sid: int,session: async_scoped_session):
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == sid, Settings.is_enabled == 1)
        result = await session.execute(smt)
        row = result.scalars().first()
        # 一般就提取第一个配置文件
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


async def get_all_config_by_id(sid: int,session: async_scoped_session):
    async with semaphore_sql:
        smt = select(Settings).where(Settings.user_id == sid)
        result = await session.execute(smt)
        row = result.scalars().all()
        return row

async def del_config_by_config_id_and_uid(config_id: int,uid: int,session: async_scoped_session):
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


async def switch_is_enable_by_id(config_id: int, session: async_scoped_session, target: bool, user_id: int) -> int:
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

async def get_comments_by_id(sid: int,session: async_scoped_session):
    async with semaphore_sql:
        stmt = select(AIHelperComments).where(AIHelperComments.comment_id == sid)
        result = await session.execute(stmt)
        raw = result.scalars().first()
        return raw

async def save_comments_by_id(sid:int,session: async_scoped_session,msg:str):
    async with semaphore_sql:
        raw = AIHelperComments(comment_id=sid, message=msg)
        session.add(raw)
        await session.commit()

async def update_comments_by_id(sid:int,session: async_scoped_session,msg:str) -> int:
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


async def call_web_search(
        query: str,
        freshness: str,
        summary: bool = True,
        count: int = 10,
        timeout: float = config.websearch_timeout
) -> Dict:
    """
    异步调用 Web Search API（兼容 httpx）

    Args:
        query: 搜索关键词
        summary: 是否返回摘要（默认 True）
        count: 返回结果数量（默认 10）
        timeout: 请求超时时间（默认 60秒）
        freshness: 搜索指定时间范围内的网页 [noLimit,oneDay,oneWeek,oneMonth,oneYear]

    Returns:
        (数据清洗后的)字典，若出错则包含 error 字段, 成功为 success 字段
    """
    headers = {
        "Authorization": f"Bearer {config.websearch_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "summary": summary,
        "count": count,
        "freshness": freshness,
    }
    async with semaphore_websearch:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    config.websearch_base_url,
                    headers=headers,
                    json=payload  # httpx 会自动序列化字典为 JSON
                )
                response.raise_for_status()
                raw_data = response.json()
                data = {}
                _ids = 0
                for d in raw_data['data']["webPages"]["value"]:
                    # 数据清洗, 字段更易于阅读
                    data[_ids] = f"标题: {d['name']}\n, url: {d['url']}, 总结: {d['summary']}"
                    _ids += 1
                return {"success":data}
            except httpx.TimeoutException:
                return {"error": "请求超时"}
            except httpx.HTTPStatusError as e:
                return {"error": f"HTTP 错误 {e.response.status_code}: {e.response.text}"}
            except KeyError as e:
                return {"error": f"keyError: {e}"}
            except Exception as e:
                return {"error": f"请求异常: {str(e)}"}
