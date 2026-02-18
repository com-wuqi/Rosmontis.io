import json
from nonebot import on_command,on_message
from nonebot import get_driver,require
from nonebot.adapters.onebot.v11 import Message, MessageEvent, GroupMessageEvent, PrivateMessageEvent
require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_scoped_session
from .aihelper_handles import *
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

        logger.debug(f"id : {session_id} | _raw_message : {_Messages_dicts[session_id]}")
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
                raw.message = json.dumps(_Messages_dicts[session_id])
            else:
                raw = AIHelperComments(comment_id=session_id,message=json.dumps(_Messages_dicts[session_id]))
                session.add(raw)
            await session.commit()

        else:
            pass

    await stop_ai.finish("会话结束~ 再见喵~")


@ai_chat.handle()
async def ai_chat_handle(event: MessageEvent):
    session_id,session_type = get_comments_id(event)
    if not _ai_switch.get(session_id, False):
        await ai_chat.finish()  # 直接结束，不回复
    msg = str(event.get_message()).strip()
    if not msg:
        await ai_chat.finish()
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
                await ai_chat.send("system hook auth failed : user: {}".format(event.user_id))
                if session_type == "PrivateMessageEvent":
                    _raw_message.append({"role": "user", "content": f"{msg}"})
                else:
                    _raw_message.append({"role": "user", "content": f"用户{event.user_id}: {msg}"})
        else:
            # 常规对话
            if session_type == "PrivateMessageEvent":
                _raw_message.append({"role": "user", "content": f"{msg}"})
            else:
                _raw_message.append({"role": "user", "content": f"用户{event.user_id}: {msg}"})

        _event_setting = _config_settings[session_id]
        _res = await send_messages_to_ai(
            key=_event_setting.api_key,url=_event_setting.url,
            model_name=_event_setting.model_name,
            messages=_raw_message,
            temperature=_event_setting.temperature
        )
        _raw_message.append({"role": "assistant", "content": f"{_res.content}"})

    await ai_chat.finish(_res.content)


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

# 自动压缩逻辑(内存中, 缺少测试)
@scheduler.scheduled_job("interval", seconds=60,id="auto_zip_chat_in_memory")
async def auto_zip_chat_in_memory():
    session = get_scoped_session()
    session_ids = list(_ai_switch.keys())
    for session_id in session_ids:

        if _ai_switch.get(session_id, True):
            continue
        lock = get_session_lock(session_id)
        try:
            await asyncio.wait_for(lock.acquire(), timeout=0)
        except asyncio.TimeoutError:
            continue  # 锁被占用，跳过

        try:
            _raw_message:list = _Messages_dicts[session_id]
            if len(_raw_message)<=1:
                continue
        except KeyError:
            continue
        # 内存中过小或不存在的不需要压缩

        row = await get_config_by_id(sid=session_id, session=session)
        # 自动清理的token由session发起者承担, 或者是 id=1 承担

        async with lock:
            _system_lists = [k for k in _Messages_dicts[session_id] if k["role"] == "system"]
            # 正确保留system提示词, 提取交互信息
            _prompt = _system_lists + [{"role": "user", "content": f"请用**简洁的**中文总结以下对话的主要内容: {[k for k in _Messages_dicts[session_id] if k["role"] != "system"]}"}]
            _res = await send_messages_to_ai(key=row.api_key,url=row.url,model_name=row.model_name,messages=_prompt,temperature=1.0)
            _Messages_dicts[session_id] = [{"role": "system", "content": f"以下是对之前对话的总结：{_res.content}"}]

    await session.close()

# TODO: 增加 自动 压缩数据库内会话 ( 不取代 auto_zip_chat_in_memory() )
# TODO: 增加 手动 压缩数据库内会话
# TODO: (自动) 压缩数据库内容 需要: session_id + _locks 锁的持有 + _ai_switch开关不存在 或者为 False
