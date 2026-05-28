import json
import re
import traceback

from nonebot import get_driver, require
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, PrivateMessageEvent, Bot
from nonebot.internal.params import ArgPlainText

from .system_prompts import tool_system_prompts_list
from ..ai_file_reader import get_file_from_event

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session
from . import config
# require("nonebot_plugin_apscheduler")
from .aihelper_handles import *

_Messages_dicts = {}
# 这里应该是 {comments_id : Messages} 这里的id用于区分不同用户
# 这个池子存储所有用户的所有对话信息
_ai_switch = {}
# 记录开关状态, 群id 或者 用户id 是index
_config_settings = {}
# 记录配置 用户id 是index, 类似 {id:{}}


_locks: Dict[int, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()  # 元数据锁

_message_queue: asyncio.Queue = asyncio.Queue(maxsize=60)
# 待处理的信息队列

_superusers = get_driver().config.superusers
_superusers = [int(k) for k in _superusers]

start_ai = on_command("ai load",priority=4,block=True)
stop_ai = on_command("ai save",priority=4,block=True)
remove_memory_ai = on_command("ai remove",priority=80,block=False)
zip_memory_ai = on_command("ai zp mm",priority=80,block=False) # 缩写一下
zip_db_ai = on_command("ai zp db",priority=80,block=False)

ai_chat = on_message(priority=8, block=False)
# 处理非命令消息

# _debug_message = on_message(priority=1, block=False)
# 捕获所有信息，备用|调试用途

def is_valid_cq_code(s: str) -> bool:
    """
    判断字符串是否为合规的 CQ 码
    """
    pattern = r"\[CQ:(?P<type>[a-zA-Z0-9-_.]+)" + r"(?P<params>" + r"(?:,[a-zA-Z0-9-_.]+=[^,\]]*)*" + r"),?\]"
    return bool(re.fullmatch(pattern, s.strip()))


async def get_session_lock(session_id: int) -> asyncio.Lock:
    """获取或创建指定会话的锁"""
    async with _locks_lock:
        if session_id not in _locks:
            _locks[session_id] = asyncio.Lock()
        return _locks[session_id]

def get_comments_id(event:MessageEvent):
    if isinstance(event,GroupMessageEvent):
        return event.group_id,"GroupMessageEvent"
    elif isinstance(event,PrivateMessageEvent):
        return event.user_id,"PrivateMessageEvent"
    else:
        logger.error("fail to get comments type : 信息类型获取失败")
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

    _msg = _system + [{"role": "system",
                       "content": "不要调用任何工具。你是一个专业的对话总结助手，擅长提取核心信息，回答简洁明了。请关注助手调用了哪些工具及其作用。"},
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
                     "content": f"不要调用任何工具。请将以下关于同一对话的多个片段摘要整合成一个连贯的总体总结：\n" + "\n".join(
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
    if config.is_enable_tool_prompt:
        _tool_prompts = tool_system_prompts_list
    else:
        _tool_prompts = []

    session_id,session_type = get_comments_id(event)
    lock = await get_session_lock(session_id)
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
                    _raw_message[:0] = [{"role": "system", "content": _config_settings[session_id].system}]
                    _raw_message[1:1] = _tool_prompts
                else:
                    pass
            else:
                # 此处长度为 0
                _raw_message.append({"role": "system", "content": f"{_config_settings[session_id].system}"})
                _raw_message.extend(_tool_prompts)
        except KeyError:
            # 处理不存在
            _Messages_dicts[session_id] = []
            _raw_message: list = _Messages_dicts[session_id]
            _raw_message.append({"role": "system", "content": f"{_config_settings[session_id].system}"})
            _raw_message.extend(_tool_prompts)

    # logger.debug(f"id : {session_id} | _raw_message : {_Messages_dicts[session_id]}")
    await start_ai.finish("收到~")

@stop_ai.handle()
async def stop_ai_handle(event: MessageEvent,session: async_scoped_session):
    session_id,_ = get_comments_id(event)
    lock = await get_session_lock(session_id)
    async with lock:
        _ai_switch[session_id] = False
        # 这里不回收加载的配置文件
        raw = await get_comments_by_id(sid=session_id,session=session)
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            # 这不是异常，为空时也可能被调用
            await stop_ai.finish("拜拜~")
        if len(_Messages_dicts[session_id])>=0:
            #
            if raw is not None:
                # 存在记录
                res = await update_comments_by_id(sid=session_id,session=session,msg=json.dumps(_Messages_dicts[session_id]))
                if res == -1:
                    logger.error("fail to update comments : 信息更新失败")
            else:
                # 不存在记录
                _ = await save_comments_by_id(sid=session_id,session=session,msg=json.dumps(_Messages_dicts[session_id]))
        else:
            pass

    await stop_ai.finish("拜拜~")


@ai_chat.handle()
async def ai_chat_handle(event: MessageEvent, bot: Bot):
    # 信息预处理，包含文件部分
    # 将所有的信息加入上下文，但是不处理
    # 可以在信息被AI处理之前，就是此处，注入向量检索的结果
    # _raw_message.append 实现

    session_id,session_type = get_comments_id(event)
    if not _ai_switch.get(session_id, False):
        return  # 直接结束，不回复
    msg = str(event.get_message()).strip()
    if not msg:
        return
    if msg.startswith("debug"):
        return

    _raw_message: list = _Messages_dicts[session_id]
    is_a_block = False
    image_message_index = -1
    lock = await get_session_lock(session_id)

    if is_valid_cq_code(msg):
        _counter, _msg = await get_file_from_event(event=event, bot=bot)
        if _counter != 0:
            # 信息是cq_code, 而且有文件读取成功或不支持
            await _message_queue.put({"type": "file", "session": (session_id, session_type), "extra": True})
            logger.debug(f"put \"extra\": True")
            is_a_block = True
            async with lock:
                image_message_index = len(_raw_message)  # 当前信息的下一个位置
                _raw_message.append({"role": "user", "content": f"{event.user_id}: image is processing"})  # 留空，占位
            logger.debug("is_valid_cq_code matched, is it a file ?")
            msg = _msg
        else:
            logger.warning(f"read a cq code {msg} , but not find a file")

    async with lock:  # 加锁保护消息列表的读写
        # start_ai 确保存在
        _raw_message: list = _Messages_dicts[session_id]
        first_word = msg.split()[0] if msg.split() else ""
        if first_word == "system" and not is_a_block:
            # 判断: 是system提示词+(私聊/群聊(管理员/所有者))
            if session_type == "PrivateMessageEvent":
                _raw_message.append({"role": "system", "content": f"{msg}"})
                await ai_chat.finish("system hook by user: {}".format(event.user_id))
            elif event.sender.role == "admin" or event.sender.role == "owner":
                _raw_message.append({"role": "system", "content": f"{msg}"})
                await ai_chat.finish("system hook by user: {}".format(event.user_id))
            else:
                await ai_chat.finish("system hook auth failed : user: {}".format(event.user_id))
        else:
            if is_a_block:
                # 含有文件
                _raw_message[image_message_index] = {"role": "user", "content": f"{event.user_id}: {msg}"}
                await _message_queue.put({"type": "msg", "session": (session_id, session_type)})
                await _message_queue.put({"type": "file", "session": (session_id, session_type), "extra": False})
                logger.debug(f"put \"extra\": False")
            else:
                # 常规对话:
                _raw_message.append({"role": "user", "content": f"{event.user_id}: {msg}"})
                await _message_queue.put({"type": "msg", "session": (session_id, session_type)})
    return

@remove_memory_ai.handle()
async def remove_memory_ai_handle(event: MessageEvent):
    session_id,session_type= get_comments_id(event)
    lock = await get_session_lock(session_id)
    async with lock:
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            await remove_memory_ai.finish("清理已取消: 首先关闭已有的会话, 然后 ai load 再次 ai save 最后再清理")
        if session_type == "GroupMessageEvent":
            if event.sender.role == "admin" or event.sender.role == "owner":
                _Messages_dicts[session_id] = []
            else:
                await remove_memory_ai.finish("sorry, you are not admin or owner : 抱歉，你不是管理员或群主")
        else:
            _Messages_dicts[session_id] = []
        await remove_memory_ai.finish("清理已完成: 一定要运行 ai save 否则视为放弃删除")

@zip_memory_ai.handle()
async def zip_memory_ai_handle(event: MessageEvent,session: async_scoped_session):
    session_id, session_type = get_comments_id(event)
    lock = await get_session_lock(session_id)
    row = await get_config_by_id(sid=session_id, session=session)
    # 这里使用的时候内存中应该有配置信息, 但是压缩需要 token , 还是由发起者承担
    async with lock:
        try:
            _ = _Messages_dicts[session_id]
        except KeyError:
            await zip_memory_ai.finish("压缩已取消: 首先关闭已有的会话, 然后运行指令 ai load 再次运行指令 ai save 最后再压缩")

        # 只要正常加载, 都会至少有一条system对话, 不需要其他异常处理
        if session_type == "GroupMessageEvent" and (event.sender.role != "admin" and event.sender.role != "owner"):
            # 权限不足
            await zip_memory_ai.finish("sorry, you are not admin or owner : 抱歉，你不是管理员或群主")

        # 执行
        _return_msg = await common_zip_message(row=row,_input_msg=_Messages_dicts[session_id])
        _Messages_dicts[session_id] = _return_msg

        await zip_memory_ai.finish("压缩已完成: 一定要运行 ai save 否则不会被保存到数据库")


@zip_db_ai.handle()
async def zip_db_ai_handle():
    await zip_db_ai.send("zip_db_ai.handle run...")


@zip_db_ai.got("session_id",prompt="session_id：(默认值为当前会话id)")
async def zip_db_ai_got_id(event: MessageEvent,session: async_scoped_session,db_session_id : str = ArgPlainText("session_id")):
    try:
        session_id = int(db_session_id.strip())
    except ValueError:
        await zip_db_ai.send("session_id 必须是合法的数字, 您的输入 {}".format(db_session_id))
        session_id, session_type = get_comments_id(event)
        await zip_db_ai.send("session_id 未提供, 使用 {}".format(session_id))

    lock = await get_session_lock(session_id)
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


async def single_user_event_handle(_session_id: int, _session_type: str, bot: Bot) -> None:
    logger.debug("single_user_event_handle")
    lock = await get_session_lock(_session_id)
    _event_setting = _config_settings[_session_id]
    # 指定配置文件
    _raw_message: list = _Messages_dicts[_session_id]
    _res = None
    async with lock:  #
        try:
            _counts = 0
            while _counts < config.tools_max_once_calls:
                _res = await send_messages_to_ai(
                    key=_event_setting.api_key, url=_event_setting.url,
                    model_name=_event_setting.model_name,
                    messages=_raw_message,
                    temperature=_event_setting.temperature
                )
                # 此处, ai可能没有尝试调用工具
                if not _res.tool_calls:
                    _raw_message.append({"role": "assistant", "content": f"{_res.content}"})
                    break

                # 保存 工具调用请求的上下文
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
                    # 处理所有调用
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except Exception as e:
                        logger.warning("fail to load tool_call function_args: {}".format(e))
                        _raw_message.append(
                            {"tool_call_id": tool_call.id, "role": "tool", "content": "fail: invalid arguments"})
                        continue

                    try:
                        logger.debug(f"MCP : function_name:{function_name} function_args:{function_args}")
                        if function_name in checked_hooked_mcp_tools.keys():
                            _result = await checked_hooked_mcp_tools[function_name](**function_args)
                        else:
                            _result = await mcp_manger.call_tool(tool_name=function_name, arguments=function_args)
                        logger.debug(f"MCP : function_name:{function_name} function_result:{_result}")
                        _raw_message.append({"tool_call_id": tool_call.id, "role": "tool", "content": str(_result)})
                    except Exception as e:
                        logger.warning("fail to call tool : {}".format(e))
                        _raw_message.append({"tool_call_id": tool_call.id, "role": "tool", "content": "fail"})
                _counts += 1
            if _counts >= config.tools_max_once_calls:
                logger.warning("Too many tool calls :(")
        except Exception as e:
            logger.error("failed : {}".format(e))
            traceback.print_exc()

    # 不再持有锁
    if _res is None:
        logger.error("未完成一次完整的对话")
        _reply = "None"
    else:
        _reply = _res.content or "已执行多次工具调用，但未生成完整回答"

    if _session_type == "GroupMessageEvent":
        logger.debug("bot.send_group_msg")
        await bot.send_group_msg(group_id=_session_id, message=_reply)
    elif _session_type == "PrivateMessageEvent":
        logger.debug("bot.send_private_msg")
        await bot.send_private_msg(user_id=_session_id, message=_reply)
    else:
        logger.warning("unknown session type")
    return


class MessageHandleWorkers:
    def __init__(self, bot):
        self._last_active_time: dict[int, float] = dict()  # id-上次信息的时间 asyncio.get_running_loop().time()
        self._messages_counter: dict[int, int] = dict()  # id-当前信息数目
        self._message_type: dict[int, str] = dict()  # id-会话类型
        self._is_force_wait: dict[int, int] = dict()  # id-当前信息是否强制等待，不处理
        self._is_force_wait_lock: dict[int, asyncio.Lock] = dict()
        self._is_force_wait_lock_lock = asyncio.Lock()  # 元数据锁
        self.need_to_handle_queue: asyncio.Queue = asyncio.Queue(maxsize=config.message_queue_max_size)
        self.bot = bot  # bot 实例
        self._workers: list[asyncio.Task] = []
        self._stop_signal: asyncio.Event = asyncio.Event()

    async def get_is_force_wait_lock(self, session_id: int) -> asyncio.Lock:
        async with self._is_force_wait_lock_lock:
            if session_id in self._is_force_wait_lock:
                return self._is_force_wait_lock[session_id]
            self._is_force_wait_lock[session_id] = asyncio.Lock()
            return self._is_force_wait_lock[session_id]

    async def handle_merge(self):
        _res = None
        for s_id, s_type in list(self._message_type.items()):
            if self._messages_counter.get(s_id) is None or self._last_active_time.get(s_id) is None:
                continue
            number_of_msg = self._messages_counter.get(s_id, 0)
            delt_time = asyncio.get_running_loop().time() - self._last_active_time[s_id]
            if number_of_msg > 0:
                if delt_time >= config.message_queue_timeout or number_of_msg >= config.message_queue_max_size:
                    try:
                        lock = await self.get_is_force_wait_lock(s_id)
                        async with lock:
                            # 检查是否已经在等待处理（防止重复入队）
                            if self._is_force_wait.get(s_id, 0) > 0:
                                continue
                            self._is_force_wait[s_id] = self._is_force_wait.get(s_id, 0) + 1
                            self.need_to_handle_queue.put_nowait((s_id, s_type))
                            self._messages_counter[s_id] = 0
                            self._last_active_time[s_id] = asyncio.get_running_loop().time()
                    except asyncio.QueueFull as e:
                        logger.warning("fail to handle message : {}".format(e))
                        logger.warning("过多未处理的会话，自动丢弃最新的会话，被丢弃的会话会在下一个循环时被重新考虑")
                    except asyncio.QueueShutDown as e:
                        logger.warning("fail to handle message : {}".format(e))
                    except Exception as e:
                        logger.warning("fail to handle message : {}".format(e))
                        traceback.print_exc()

        if not self.need_to_handle_queue.empty():
            logger.debug(f"need to handle: {self.need_to_handle_queue.qsize()}")

    async def _single_worker(self):
        while not self._stop_signal.is_set():
            is_event_handled = False
            try:
                s_id, s_type = await self.need_to_handle_queue.get()
                lock = await self.get_is_force_wait_lock(s_id)
                try:
                    await single_user_event_handle(_session_id=s_id, _session_type=s_type, bot=self.bot)
                    is_event_handled = True
                except Exception as e:
                    logger.error("fail to handle message: {}".format(e))
                    traceback.print_exc()
                finally:
                    async with lock:
                        current = self._is_force_wait.get(s_id, 0)
                        self._is_force_wait[s_id] = max(0, current - 1)
            except asyncio.CancelledError:
                # logger.debug("_single_worker cancelled")
                pass
            except Exception as e:
                logger.error("fail to handle message: {}".format(e))
                traceback.print_exc()
            finally:
                if is_event_handled:
                    self.need_to_handle_queue.task_done()

    async def init_workers(self):
        self._workers.clear()
        self._workers = [asyncio.create_task(self._single_worker()) for _ in range(config.max_workers)]

    async def close_workers(self):
        self._stop_signal.set()
        for _worker in self._workers:
            _worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def main_loop(self):
        while True:
            if self._stop_signal.is_set():
                return
            data_list = []
            while not _message_queue.empty():
                try:
                    _data = _message_queue.get_nowait()
                    data_list.append(_data)
                    _message_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if len(data_list) == 0:
                try:
                    await self.handle_merge()
                except Exception as e:
                    logger.error("fail to handle message: {}".format(e))

                    traceback.print_exc()
                await asyncio.sleep(1 / 2)
                continue

            try:
                for data in data_list:
                    logger.debug("_message_queue.get() : {}".format(data))
                    _s_id, _s_type = data["session"]
                    self._message_type[_s_id] = _s_type
                    self._last_active_time[_s_id] = asyncio.get_running_loop().time()
                    if data["type"] == "msg":
                        self._messages_counter[_s_id] = self._messages_counter.get(_s_id, 0) + 1
                    elif data["type"] == "file":
                        lock = await self.get_is_force_wait_lock(_s_id)
                        async with lock:
                            if data["extra"]:
                                self._is_force_wait[_s_id] = self._is_force_wait.get(_s_id, 0) + 1  # 当前有文件
                            else:
                                current = self._is_force_wait.get(_s_id, 0)
                                self._is_force_wait[_s_id] = max(0, current - 1)  # 当前没有文件，防止负数
                    else:
                        logger.warning(f"unknown message type: {data['type']}")
                await self.handle_merge()
            except Exception as e:
                logger.error("fail to handle message : {}".format(e))
                traceback.print_exc()
