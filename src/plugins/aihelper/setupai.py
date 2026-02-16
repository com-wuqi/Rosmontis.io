from nonebot import on_command, Bot
from nonebot.params import CommandArg,ArgPlainText
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Message, MessageEvent, GroupMessageEvent

from nonebot.log import logger
from nonebot import get_driver,require
require("nonebot_plugin_orm")
from .models import *
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select, update, delete
from .aihelper_handles import get_model_names
_superusers = get_driver().config.superusers
_superusers = [int(k) for k in _superusers]
# 这里提供通过对话修改数据库的方法

setup_ai = on_command("setupai")

@setup_ai.handle()
async def setup_ai_handle(event: MessageEvent,state: T_State):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send(Message("setupai begin now : url? api_key? model_name? max_length? cancel取消"))
    if event.user_id in _superusers:
        state["user_id"] = event.user_id
    else:
        await setup_ai.finish("user : {} try to run setup_ai but not SA".format(event.user_id))


@setup_ai.got("url", prompt="url：")
async def setup_ai_url(state: T_State,event: MessageEvent,url: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not url.strip():
        await setup_ai.reject("url 不能为空，请重新输入：")
    if url.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["url"] = url.strip()
    logger.debug("url : {}".format(state["url"]))

@setup_ai.got("apikey", prompt="apikey：")
async def setup_ai_apikey(state: T_State,event: MessageEvent,apikey: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not apikey.strip():
        await setup_ai.reject("apikey 不能为空，请重新输入：")
    if apikey.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["apikey"] = apikey.strip()
    logger.debug("apikey : {}".format(state["apikey"]))

@setup_ai.got("max_length", prompt="max_length：")
async def setup_ai_max_length(state: T_State,event: MessageEvent,max_length: str = ArgPlainText()):

    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not max_length.strip():
        await setup_ai.reject("max_length 不能为空，请重新输入：")
    if max_length.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["max_length"] = max_length.strip()
    logger.debug("max_length : {}".format(state["max_length"]))


@setup_ai.got("model_name", prompt="model_name：")
async def setup_ai_model_name(state: T_State, event: MessageEvent, model_name: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id, event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not model_name.strip():
        await setup_ai.reject("model_name 不能为空，请重新输入：")
    if model_name.strip() == "cancel":
        await setup_ai.finish("canceled")
    _model_list = await get_model_names(key=state["apikey"],url=state["url"])
    if model_name.strip() not in _model_list:
        await setup_ai.reject("model_list is {}, your input is not in it".format(_model_list))

    state["model_name"] = model_name.strip()
    logger.debug("model_name : {}".format(state["model_name"]))
    await setup_ai.send(f"已成功选择模型：{model_name}")

@setup_ai.got("confirm", prompt="do you confirm? y/n")
async def setup_ai_confirm(state: T_State,session: async_scoped_session,event: MessageEvent, confirm: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id, event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send("url:{},\nkey:{},\nmodel_name:{},\nmax_length:{}".format(state["url"],state["apikey"],state["model_name"],int(state["max_length"])))
    if confirm.strip() == "y":
        new_setting = Settings(url=state["url"],api_key=state["apikey"],model_name=state["model_name"],max_length=int(state["max_length"]),user_id=int(state["user_id"]))
        session.add(new_setting)
        await session.flush()
        await session.commit()

    elif confirm.strip() == "n":
        await setup_ai.finish("canceled")
    else:
        await setup_ai.reject("input should be y/n")
