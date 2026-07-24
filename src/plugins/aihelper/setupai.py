from nonebot import get_driver, require
from nonebot import on_command
from nonebot.adapters import Event,Message
from nonebot.params import ArgPlainText, CommandArg
from nonebot.typing import T_State

from src.plugins.shared.adapter_utils import resolve_session, get_sender_id

require("nonebot_plugin_orm")
from .aihelper_handles import *
from nonebot_plugin_orm import async_scoped_session

_superusers = set(get_driver().config.selfhostaiusers)
# 这里提供通过对话修改数据库的方法

setup_ai = on_command("ai cf add") # 增加配置文件
show_config = on_command("ai cf show")  # 列出用户配置
delete_config = on_command("ai cf delete")  # 删除用户配置, 暂时不实现
edit_config = on_command("ai cf edit")  # 编辑用户配置
switch_config = on_command("ai cf switch")
choose_config = on_command("ai cf choose")  # 选择配置文件


# 切换用户配置, 本质上是修改一个值
# 用法 [sign]ai cf switch [config_id] bool([switch_int])

@edit_config.handle()
async def edit_config_handle():
    await edit_config.finish("不计划实现, 推荐删除配置后新建")


@choose_config.handle()
async def choose_config_handle(
    event: Event,
    session: async_scoped_session,
    config_id: Message = CommandArg(),
):
    if resolve_session(event)[1] != "private":
        await choose_config.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    _config_id = config_id.extract_plain_text().strip()
    if not _config_id.isdigit():
        await choose_config.finish("config_id 需要是纯数字")
    _res = await change_is_enable_by_id(
        config_id=int(_config_id),
        session=session,
        user_id=get_sender_id(event),
    )
    if _res == -1:
        await choose_config.finish("fail")
    else:
        await choose_config.finish(
            f"总计命中: {_res['_changed_to_true'] + _res['_changed_to_false']}\n"
            f"set :\nTrue: {_res['_changed_to_true']}"
            f" ,False: {_res['_changed_to_false']}"
        )

@show_config.handle()
async def show_config_handle(event: Event, session: async_scoped_session):
    if resolve_session(event)[1] != "private":
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    configs = await get_all_config_by_id(sid=get_sender_id(event), session=session)
    _result = []
    if configs is not None:
        _result.append(f"user_id: {get_sender_id(event)}")
        _result.append("")
        for in_config in configs:
            _result.append("config:")
            _result.append(f"id: {in_config.id}")
            _result.append(f"url: {in_config.url}")
            _result.append(f"api_key: {in_config.api_key}")
            _result.append(f"model_name: {in_config.model_name}")
            _result.append(f"max_length: {in_config.max_length}")
            _result.append(f"system: {in_config.system}")
            _result.append(f"temperature: {in_config.temperature}")
            _result.append(f"is_enabled: {in_config.is_enabled}")
            _result.append("")
        await show_config.finish("\n".join(_result))
    else:
        await show_config.finish("not found")


@switch_config.handle()
async def switch_config_handle(
    event: Event,
    session: async_scoped_session,
    switch: Message = CommandArg(),
):
    if resolve_session(event)[1] != "private":
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    switch_list = switch.extract_plain_text().strip().split()
    if len(switch_list) != 2:
        await switch_config.finish("需要两个参数: config_id:int switch:int")
    if not switch_list[1].isdigit():
        await switch_config.finish("switch:int 参数不合法")
    if switch_list[0] == "1":
        await switch_config.finish("操作失败")
    _res = await switch_is_enable_by_id(
        config_id=int(switch_list[0]),
        session=session,
        target=bool(int(switch_list[1])),
        user_id=get_sender_id(event),
    )
    if _res != 0:
        await switch_config.finish("404 not found")
    else:
        await switch_config.finish("ok")


@delete_config.handle()
async def delete_config_handle(
    event: Event,
    session: async_scoped_session,
    config_id: Message = CommandArg(),
):
    if resolve_session(event)[1] != "private":
        await delete_config.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    config_id = config_id.extract_plain_text().strip()
    if config_id == "1":
        await delete_config.finish("操作失败")
    if not config_id.strip() or not config_id.strip().isdigit():
        await delete_config.finish(
            "没有输入或者输入不合法: 要求提供配置id, 可以通过ai cf show获取"
        )
    _res = await del_config_by_config_id_and_uid(
        session=session,
        config_id=int(config_id.strip()),
        uid=get_sender_id(event),
    )
    if _res == 0:
        await delete_config.finish("操作成功")
    else:
        await delete_config.finish("操作失败")


@setup_ai.handle()
async def setup_ai_handle(event: Event, state: T_State):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send("setupai begin now : cancel取消")
    if get_sender_id(event) in _superusers:
        state["user_id"] = get_sender_id(event)
    else:
        await setup_ai.finish(
            f"user : {get_sender_id(event)} try to run setup_ai but not SA"
        )


@setup_ai.got("url", prompt="url：")
async def setup_ai_url(state: T_State, event: Event, url: str = ArgPlainText()):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not url.strip():
        await setup_ai.reject("url 不能为空，请重新输入：")
    if url.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["url"] = url.strip()
    logger.debug("url : {}".format(state["url"]))

@setup_ai.got("apikey", prompt="apikey：")
async def setup_ai_apikey(state: T_State, event: Event, apikey: str = ArgPlainText()):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not apikey.strip():
        await setup_ai.reject("apikey 不能为空，请重新输入：")
    if apikey.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["apikey"] = apikey.strip()
    logger.debug("apikey : {}".format(state["apikey"]))

@setup_ai.got("max_length", prompt="max_length：")
async def setup_ai_max_length(
    state: T_State, event: Event, max_length: str = ArgPlainText()
):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
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
async def setup_ai_temperature(
    state: T_State, event: Event, temperature: str = ArgPlainText()
):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
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
async def setup_ai_model_name(
    state: T_State, event: Event, model_name: str = ArgPlainText()
):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not model_name.strip():
        await setup_ai.reject("model_name 不能为空，请重新输入：")
    if model_name.strip() == "cancel":
        await setup_ai.finish("canceled")
    _model_list = await get_model_names(key=state["apikey"],url=state["url"])
    if model_name.strip() not in _model_list:
        await setup_ai.reject(f"model_list is {_model_list}, your input is not in it")

    state["model_name"] = model_name.strip()
    logger.debug("model_name : {}".format(state["model_name"]))
    await setup_ai.send(f"已成功选择模型：{model_name}")

@setup_ai.got("system_prompt", prompt="system_prompt：")
async def setup_ai_system_prompt(
    state: T_State, event: Event, system_prompt: str = ArgPlainText()
):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    if not system_prompt.strip():
        await setup_ai.reject("system_prompt 不能为空，请重新输入：")
    if system_prompt.strip() == "cancel":
        await setup_ai.finish("canceled")

    state["system_prompt"] = system_prompt.strip()
    logger.debug("system_prompt : {}".format(state["system_prompt"]))

@setup_ai.got("confirm", prompt="do you confirm? y/n")
async def setup_ai_confirm(
    state: T_State,
    session: async_scoped_session,
    event: Event,
    confirm: str = ArgPlainText(),
):
    if resolve_session(event)[1] != "private":
        logger.warning("user tried to run setup_ai in group")
        await setup_ai.finish("处于安全考虑, 这个操作不允许在群聊中进行")
    await setup_ai.send(
        f"url:{state['url']},\n"
        f"key:{state['apikey']},\n"
        f"model_name:{state['model_name']},\n"
        f"max_length:{int(state['max_length'])},\n"
        f"temperature:{float(state['temperature'])}\n"
        f"system_prompt:{state['system_prompt']}"
    )
    if confirm.strip() == "y":
        new_setting = Settings(
            url=state["url"],
            api_key=state["apikey"],
            model_name=state["model_name"],
            max_length=int(state["max_length"]),
            user_id=str(state["user_id"]),
            system=state["system_prompt"],
            is_enabled=False,
        )
        session.add(new_setting)
        await session.flush()
        await session.commit()

    elif confirm.strip() == "n":
        await setup_ai.finish("canceled")
    else:
        await setup_ai.reject("input should be y/n")
