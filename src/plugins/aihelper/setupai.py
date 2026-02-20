from nonebot import get_driver, require
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent, GroupMessageEvent
from nonebot.params import ArgPlainText
from nonebot.typing import T_State

require("nonebot_plugin_orm")
from .aihelper_handles import *

_superusers = get_driver().config.selfhostaiusers
_superusers = [int(k) for k in _superusers]
# 这里提供通过对话修改数据库的方法

setup_ai = on_command("ai cf add") # 增加配置文件
show_config = on_command("ai cf show")  # 列出用户配置
delete_config = on_command("ai cf delete")  # 删除用户配置
edit_config = on_command("ai cf edit")  # 编辑用户配置

@show_config.handle()
async def show_config_handle(event: MessageEvent,session: async_scoped_session):
    if isinstance(event, GroupMessageEvent):
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    configs = await get_all_config_by_id(sid=event.user_id,session=session)
    _result = []
    if configs is not None:
        _result.append("user_id: {}".format(event.user_id))
        _result.append("")
        for config in configs:
            _result.append("config:")
            _result.append("id: {}".format(config.id))
            _result.append("url: {}".format(config.url))
            _result.append("api_key: {}".format(config.api_key))
            _result.append("model_name: {}".format(config.model_name))
            _result.append("max_length: {}".format(config.max_length))
            _result.append("system: {}".format(config.system))
            _result.append("temperature: {}".format(config.temperature))
            _result.append("is_enabled: {}".format(config.is_enabled))
            _result.append("")
        await show_config.finish("\n".join(_result))
    else:
        await show_config.finish("not found")


@delete_config.handle()
async def delete_config_handle(event: MessageEvent, session: async_scoped_session, config_id: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        await delete_config.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not config_id.strip() and config_id.strip().isdigit():
        # isdigit() 判断纯数字
        await delete_config.finish("没有输入或者输入不合法: 要求提供配置id, 可以通过ai cf show获取")
    _res = await del_config_by_config_id_and_uid(session=session, config_id=int(config_id.strip()), uid=event.user_id)
    if _res == 0:
        await delete_config.finish("操作成功")
    else:
        await delete_config.finish("操作失败")


@setup_ai.handle()
async def setup_ai_handle(event: MessageEvent,state: T_State):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send(Message("setupai begin now : cancel取消"))
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
    try:
        _ = int(max_length.strip())
    except ValueError:
        await setup_ai.reject("max_length 必须是整数，请重新输入：")
    if max_length.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["max_length"] = max_length.strip()
    logger.debug("max_length : {}".format(state["max_length"]))

@setup_ai.got("temperature", prompt="temperature：")
async def setup_ai_temperature(state: T_State,event: MessageEvent,temperature: str = ArgPlainText()):

    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not temperature.strip():
        await setup_ai.reject("temperature 不能为空，请重新输入：")
    try:
        _ = float(temperature.strip())
    except ValueError:
        await setup_ai.reject("temperature 必须是小数，请重新输入：")
    if temperature.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["temperature"] = temperature.strip()
    logger.debug("temperature : {}".format(state["temperature"]))


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

@setup_ai.got("system_prompt", prompt="system_prompt：")
async def setup_ai_system_prompt(state: T_State,event: MessageEvent,system_prompt: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id,event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not system_prompt.strip():
        await setup_ai.reject("system_prompt 不能为空，请重新输入：")
    if system_prompt.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["system_prompt"] = system_prompt.strip()
    logger.debug("system_prompt : {}".format(state["system_prompt"]))

@setup_ai.got("confirm", prompt="do you confirm? y/n")
async def setup_ai_confirm(state: T_State,session: async_scoped_session,event: MessageEvent, confirm: str = ArgPlainText()):
    if isinstance(event, GroupMessageEvent):
        logger.warning("user : {} try to run setup_ai in group : {}".format(event.user_id, event.group_id))
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send("url:{},\nkey:{},\nmodel_name:{},\nmax_length:{},\ntemperature:{}\nsystem_prompt:{}".format(state["url"],state["apikey"],state["model_name"],int(state["max_length"]),float(state["temperature"]),state["system_prompt"]))
    if confirm.strip() == "y":
        new_setting = Settings(url=state["url"], api_key=state["apikey"], model_name=state["model_name"],
                               max_length=int(state["max_length"]), user_id=int(state["user_id"]),
                               system=state["system_prompt"], is_enabled=False)
        session.add(new_setting)
        await session.flush()
        await session.commit()

    elif confirm.strip() == "n":
        await setup_ai.finish("canceled")
    else:
        await setup_ai.reject("input should be y/n")
