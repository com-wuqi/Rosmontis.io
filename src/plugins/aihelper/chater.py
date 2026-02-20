import json

from nonebot import get_driver, require
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.internal.params import ArgPlainText

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_scoped_session
from .aihelper_handles import *
from . import config
import asyncio
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

_Messages_dicts = {}
# 这里应该是 {comments_id : Messages} 这里的id用于区分不同用户
# 这个池子存储所以用户的所以对话信息
_ai_switch = {}
# 记录开关状态, 群id 或者 用户id 是index
_config_settings = {}
# 记录配置 用户id 是index, 类似 {id:{}}


_locks: Dict[int, asyncio.Lock] = {}

_superusers = get_driver().config.superusers
_superusers = [int(k) for k in _superusers]

start_ai = on_command("ai load",priority=4,block=True)
stop_ai = on_command("ai save",priority=4,block=True)
remove_memory_ai = on_command("ai remove",priority=80,block=False)
zip_memory_ai = on_command("ai zp mm",priority=80,block=False) # 缩写一下
zip_db_ai = on_command("ai zp db",priority=80,block=False)

ai_chat = on_message(priority=8, block=False)
# 处理非命令消息

def get_session_lock(session_id: int) -> asyncio.Lock:
    """获取或创建指定会话的锁"""
    if session_id not in _locks:
        _locks[session_id] = asyncio.Lock()
    return _locks[session_id]

def get_comments_id(event:MessageEvent):
    if isinstance(event,GroupMessageEvent):
        return event.group_id,"GroupMessageEvent"
    elif isinstance(event,PrivateMessageEvent):
        return event.user_id,"PrivateMessageEvent"
    else:
        logger.error("fail to get comments type")
        return event.user_id,"unknown"

def generate_zip_message(raw_message:list):
    dialog_lines = []
    _system = []
    for msg in raw_message:
        role = msg.get("role", "unknown")
        if role == "system":
            _system.append(msg)
        elif role == "user":
            # 处理系统和用户信息
            content = msg.get("content",None)
            if content is None:
                content = ""
            dialog_lines.append(f"{role}: {content}")
        elif role == "assistant":
            parts = []
            if msg.get("content"):
                parts.append(f"assistant: {msg['content']}")
            tool_calls = msg.get("tool_calls")
            if tool_calls and isinstance(tool_calls, list):
                for tc in tool_calls:
                    func = tc.get("function", {})
                    # 获取function字段
                    func_name = func.get("name", "unknown")
                    func_args = func.get("arguments", "{}")
                    parts.append(f"[助手调用工具: {func_name} 参数: {func_args}]")
            if not parts:
                parts.append("assistant: (空)")
            dialog_lines.append("\n".join(parts))
        elif role == "tool" or role == "function":
            content = msg.get("content","")
            dialog_lines.append(f"工具返回: {content}")
        else:
            # 未知
            dialog_lines.append(f"{role}: {msg.get('content', '')}")

    _msg = _system + [{"role": "system", "content": "你是一个专业的对话总结助手，擅长提取核心信息，回答简洁明了。请关注助手调用了哪些工具及其作用。"},
            {"role": "user","content":f"""请用**简洁的中文**总结以下对话的主要内容，包括讨论的主题、关键问题和结论。
            如果对话中提到了具体任务或决定，请一并概括。
            对话历史 : {chr(10).join(dialog_lines)}"""}]
    return _msg,_system

def chunk_messages(messages: list, chunk_size: int = 8) -> list:
    """将消息列表分割成多个子块，每个块最多包含 chunk_size 条消息"""
    return [messages[i:i + chunk_size] for i in range(0, len(messages), chunk_size)]

async def common_zip_message(_input_msg:list,row:dict) -> list:
    # 这里无锁, 调用时候自行解决
    _chunks_zipped_messages = []  # 每一块压缩后的结果
    _system_in_chunks = []  # 每一块里面的system
    _msg_chunks = chunk_messages(_input_msg)

    for chunk in _msg_chunks:
        # 对每个块单独压缩
        _before_zip_msg, _system_in_chunk = generate_zip_message(chunk)
        _system_in_chunks.extend(_system_in_chunk)  # 展平
        _res = await send_messages_to_ai(
            key=row.api_key, url=row.url, model_name=row.model_name,
            messages=_before_zip_msg, temperature=1.0
        )
        _chunks_zipped_messages.append(_res.content)

    final_prompt = [{"role": "user",
                     "content": f"请将以下关于同一对话的多个片段摘要整合成一个连贯的总体总结：\n" + "\n".join(
                         _chunks_zipped_messages)}]
    _res = await send_messages_to_ai(
        key=row.api_key, url=row.url, model_name=row.model_name,
        messages=final_prompt, temperature=1.0
    )
    _result = _system_in_chunks + [
        {"role": "system", "content": f"以下是对之前对话的总结：{_res.content}"}]
    return _result


@start_ai.handle()
async def start_ai_handle(event: MessageEvent,session: async_scoped_session):
    session_id,session_type = get_comments_id(event)
    lock = get_session_lock(session_id)
    async with lock:
        _ai_switch[session_id] = True

        row = await get_config_by_id(sid=session_id,session=session)
        _config_settings[session_id] = row
        logger.debug(f"配置: {row.id}")

        raw = await get_comments_by_id(sid=session_id,session=session)

        if raw is not None and raw.message:
            try:
                _Messages_dicts[session_id] = json.loads(raw.message)
            except json.JSONDecodeError:
                logger.error(f"解析历史消息失败，comment_id: {session_id} 将重置为空")
                await start_ai.send(f"解析历史消息失败，comment_id: {session_id} 将重置为空")
                _Messages_dicts[session_id] = []

        try:
            _raw_message:list = _Messages_dicts[session_id]
            if len(_raw_message)>0:
                # 执行 HOOK, 仅仅排除一种情况
                if _raw_message[0]["role"] != "system":
                    _raw_message.insert(0,{"role": "system", "content": f"{_config_settings[session_id].system}"})
                else:
                    pass
            else:
                _raw_message.append({"role": "system", "content": f"{_config_settings[session_id].system}"})
        except KeyError:
            _Messages_dicts[session_id] = []
            _raw_message: list = _Messages_dicts[session_id]
            _raw_message.append({"role": "system", "content": f"{_config_settings[session_id].system}"})

        # logger.debug(f"id : {session_id} | _raw_message : {_Messages_dicts[session_id]}")
    await start_ai.finish("收到喵~ 会话建立")

@stop_ai.handle()
async def stop_ai_handle(event: MessageEvent,session: async_scoped_session):
    session_id,_ = get_comments_id(event)
    lock = get_session_lock(session_id)
    async with lock:
        _ai_switch[session_id] = False
        # 这里不回收加载的配置文件
        raw = await get_comments_by_id(sid=session_id,session=session)
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            await stop_ai.finish("会话结束~ 再见喵~")
        if len(_Messages_dicts[session_id])>=0:
            #
            if raw is not None:
                # 存在记录
                res = await update_comments_by_id(sid=session_id,session=session,msg=json.dumps(_Messages_dicts[session_id]))
                if res == -1:
                    logger.error("fail to update comments")
            else:
                # 不存在记录
                _ = await save_comments_by_id(sid=session_id,session=session,msg=json.dumps(_Messages_dicts[session_id]))

        else:
            pass

    await stop_ai.finish("会话结束~ 再见喵~")


@ai_chat.handle()
async def ai_chat_handle(event: MessageEvent):
    session_id,session_type = get_comments_id(event)
    if not _ai_switch.get(session_id, False):
        return  # 直接结束，不回复
    msg = str(event.get_message()).strip()
    if not msg:
        return
    lock = get_session_lock(session_id)
    async with lock:  # 加锁保护消息列表和配置的读写
        try:
            _raw_message:list = _Messages_dicts[session_id]
        except KeyError:
            logger.info("empty message_list")
            _Messages_dicts[session_id] = []
            _raw_message: list = _Messages_dicts[session_id]

        if msg.split()[0] == "system":
            # 判断: 是system提示词+(私聊/群聊(管理员/所有者))
            if session_type == "PrivateMessageEvent":
                await ai_chat.send("system hook by user: {}".format(event.user_id))
                _raw_message.append({"role": "system", "content": f"{msg}"})
            elif event.sender.role == "admin" or event.sender.role == "owner":
                await ai_chat.send("system hook by user: {}".format(event.user_id))
                _raw_message.append({"role": "system", "content": f"{msg}"})
            else:
                await ai_chat.finish("system hook auth failed : user: {}".format(event.user_id))

        else:
            # 常规对话
            if session_type == "PrivateMessageEvent":
                _raw_message.append({"role": "user", "content": f"{msg}"})
            else:
                _raw_message.append({"role": "user", "content": f"用户{event.user_id}: {msg}"})

        _event_setting = _config_settings[session_id]
        # 指定配置文件

        _counts = 0
        while _counts < config.websearch_max_once_calls:
            _res = await send_messages_to_ai(
                key=_event_setting.api_key,url=_event_setting.url,
                model_name=_event_setting.model_name,
                messages=_raw_message,
                temperature=_event_setting.temperature
            )
            # 此处, ai可能尝试了调用工具
            if not _res.tool_calls:
                _raw_message.append({"role": "assistant", "content": f"{_res.content}"})
                break

            _assistant_message = {
                "role": "assistant",
                "content": _res.content,  # 可能为 None，保留即可
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in _res.tool_calls
                ]
            }
            _raw_message.append(_assistant_message)
            for tool_call in _res.tool_calls:
                # 保存 工具调用请求的上下文
                if tool_call.function.name == "web_search":
                    # 处理工具
                    args = json.loads(tool_call.function.arguments)
                    query = args.get("query")
                    freshness = args.get("freshness","noLimit")
                    count = args.get("count", 10)
                    _searched = await call_web_search(query=query,freshness=freshness,count=count)
                    _raw_message.append({"tool_call_id": tool_call.id,"role": "tool","content": str(_searched)})

                else:
                    pass

            _counts +=1
    # 锁释放
    if _res.tool_calls:
        _reply = "已执行多次工具调用，但未生成完整回答"
    else:
        _reply = _res.content or "已执行多次工具调用，但未生成完整回答"
    await ai_chat.finish(_reply)


@remove_memory_ai.handle()
async def remove_memory_ai_handle(event: MessageEvent):
    session_id,session_type= get_comments_id(event)
    lock = get_session_lock(session_id)
    async with lock:
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            await remove_memory_ai.finish("清理已取消: 首先关闭已有的会话, 然后 ai load 再次 ai save 最后再清理")
        if session_type == "GroupMessageEvent":
            if event.sender.role == "admin" or event.sender.role == "owner":
                _Messages_dicts[session_id] = []
            else:
                await remove_memory_ai.finish("sorry, you are not admin or owner")
        else:
            _Messages_dicts[session_id] = []
        await remove_memory_ai.finish("清理已完成: 一定要运行 ai save 否则视为放弃删除")

@zip_memory_ai.handle()
async def zip_memory_ai_handle(event: MessageEvent,session: async_scoped_session):
    session_id, session_type = get_comments_id(event)
    lock = get_session_lock(session_id)
    row = await get_config_by_id(sid=session_id, session=session)
    # 这里使用的时候内存中应该有配置信息, 但是压缩需要 token , 还是由发起者承担
    async with lock:
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            await zip_memory_ai.finish("压缩已取消: 首先关闭已有的会话, 然后 ai load 再次 ai save 最后再压缩")

        # 只要正常加载, 都会至少有一条system对话, 不需要其他异常处理
        if session_type == "GroupMessageEvent" and (event.sender.role != "admin" and event.sender.role != "owner"):
            # 权限不足
            await zip_memory_ai.finish("sorry, you are not admin or owner")

        # 执行
        _return_msg = await common_zip_message(row=row,_input_msg=_Messages_dicts[session_id])
        _Messages_dicts[session_id] = _return_msg

        await zip_memory_ai.finish("压缩已完成: 一定要运行 ai save 否则视为放弃删除")


@zip_db_ai.handle()
async def zip_db_ai_handle():
    await zip_db_ai.send("zip_db_ai.handle run...")


@zip_db_ai.got("session_id",prompt="session_id：(默认值为当前会话id)")
async def zip_db_ai_got_id(event: MessageEvent,session: async_scoped_session,db_session_id : str = ArgPlainText("session_id")):
    session_id=-1
    if not db_session_id.strip():
        session_id, session_type = get_comments_id(event)
        await zip_db_ai.send("session_id 未提供, 使用 {}".format(session_id))
    else:
        try:
            session_id = int(db_session_id.strip())
        except ValueError:
            await zip_db_ai.reject("session_id 必须是合法的数字, 您的输入 {}".format(db_session_id))
    lock = get_session_lock(session_id)
    row = await get_config_by_id(sid=session_id, session=session)
    # 这里使用的时候内存中没有有配置信息, 但是压缩需要 token , 还是由发起者承担
    # 如果按照这个思路处理, 群聊信息将无法被手动压缩, 必须引入参数: 会话id
    # 这里的会话id就是数据库保存的id, 参考 get_comments_id , 群聊为群号, 私聊为个人qq号
    # 此处同理, 由于优先级, 不需要判断开关 (自动任务需要)
    async with lock:
        _ai_switch[session_id] = False # 再覆写一下开关
        raw_msg = await get_comments_by_id(sid=session_id, session=session)
        if raw_msg is not None and raw_msg.message:
            await zip_db_ai.send("开始处理...")
            _raw_messages:list = json.loads(raw_msg.message)
            _res = await common_zip_message(_input_msg=_raw_messages,row=row)
            # 然后回写
            _try_write = await update_comments_by_id(sid=session_id,session=session,msg=json.dumps(_res))
            await zip_db_ai.finish("zip_db_ai. success")
        else:
            await zip_db_ai.finish("db is empty, finished")


# 自动压缩逻辑(内存中, 缺少测试)
@scheduler.scheduled_job("interval", seconds=60,id="auto_zip_chat_in_memory")
async def auto_zip_chat_in_memory():
    session = get_scoped_session()
    session_ids = list(_ai_switch.keys())
    for session_id in session_ids:

        if _ai_switch.get(session_id, False):
            continue
        lock = get_session_lock(session_id)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=0)
        except asyncio.TimeoutError:
            continue  # 锁被占用，跳过

        row = await get_config_by_id(sid=session_id, session=session)
        # 自动清理的token由session发起者承担, 或者是 id=1 承担
        # 但是在群聊信息中, 这里一定会是 id=1 承担 token

        try:
            _raw_message:list = _Messages_dicts[session_id]
            if len(_raw_message)<=row.max_length:
                continue
        except KeyError:
            continue
        # 内存中过小或不存在的不需要压缩

        async with lock:
            _return_msg = await common_zip_message(row=row, _input_msg=_Messages_dicts[session_id])
            _Messages_dicts[session_id] = _return_msg

    await session.close()

