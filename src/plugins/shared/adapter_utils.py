"""
适配器抽象层 —— 抹平 OneBot V11 和 Feishu (飞书) 之间的差异。

核心设计：
  所有对具体 adapter 类型的 import 全部延迟到函数内部（lazy import），
  保证只安装其中一个 adapter 时模块也能正常 import，运行时才报对应分支的错误。

适配器检测策略：
  Event → 检查 type(event).__module__ 中是否包含 "onebot" 或 "feishu"
  Bot   → 检查 bot.type 字符串（NoneBot 注册 adapter 时的 name）
"""

import json
import os
import time
from typing import TYPE_CHECKING

import aiofiles
from nonebot import require
from nonebot.adapters import Bot, Event, MessageSegment
from nonebot.log import logger

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
from src.plugins.public_apis.shared_funcs import download_file

if TYPE_CHECKING:
    pass


# ============================================================
# 通用工具
# ============================================================


async def save_bytes_to_cache(file_data: bytes, prefix: str, file_name: str = "") -> str:
    """把 bytes 异步写入 localstore 缓存目录，返回文件路径字符串。"""
    name = f"{prefix}_{time.time()}_{file_name}" if file_name else f"{prefix}_{time.time()}"
    tmp_path = store.get_plugin_cache_file(name)
    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(file_data)
    return str(tmp_path)


def get_event_bot(event: Event) -> Bot | None:
    """根据事件所属的 adapter，从全局 bot 注册表查找正确的 bot 实例。"""
    from src.plugins.aihelper import _bots
    adapter = "onebot" if is_onebot_event(event) else ("feishu" if is_feishu_event(event) else "")
    bot = _bots.get(adapter)
    if bot is None:
        logger.warning(f"get_event_bot: adapter={adapter} not connected yet")
    return bot

# ============================================================
# 适配器检测
# ============================================================

def _event_module(event: Event) -> str:
    """返回事件来源模块路径，如 'nonebot.adapters.onebot.v11.event'"""
    return type(event).__module__


def is_onebot_event(event: Event) -> bool:
    """判断事件是否来自 OneBot V11 适配器"""
    return "adapters.onebot" in _event_module(event)


def is_feishu_event(event: Event) -> bool:
    """判断事件是否来自 Feishu（飞书）适配器"""
    return "adapters.feishu" in _event_module(event)


def get_adapter_name(bot: Bot) -> str:
    """
    获取统一适配器名：'onebot' | 'feishu' | 'unknown'
    
    基于 bot.type（注册 adapter 时填的 name，如 'OneBot V11' 或 '飞书'）。
    """
    name = getattr(bot, "type", "")
    if "OneBot" in name:
        return "onebot"
    if "Feishu" in name or "飞书" in name:
        return "feishu"
    return "unknown"


def is_onebot(bot: Bot) -> bool:
    """Bot 实例是否为 OneBot V11"""
    return get_adapter_name(bot) == "onebot"


def is_feishu(bot: Bot) -> bool:
    """Bot 实例是否为 Feishu（飞书）"""
    return get_adapter_name(bot) == "feishu"

# ============================================================
# 会话解析（替代 get_comments_id）
# ============================================================

def resolve_session(event: Event) -> tuple[str, str]:
    """
    从事件解析出 (session_id: str, session_type: str)。
    
    session_type 返回 "group"（群聊）或 "private"（私聊），不再是旧代码中的
    "GroupMessageEvent" / "PrivateMessageEvent" 字符串。

    跨平台 ID 映射：
      OneBot 私聊 → (str(user_id), "private")
      OneBot 群聊 → (str(group_id), "group")
      Feishu 私聊 → (chat_id,     "private")   ← chat_id 原生就是 str，如 "oc_xxx"
      Feishu 群聊 → (chat_id,     "group")
    """
    if is_onebot_event(event):
        from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
        if isinstance(event, GroupMessageEvent):
            return str(event.group_id), "group"
        if isinstance(event, PrivateMessageEvent):
            return str(event.user_id), "private"
        logger.warning("fail to get onebot session type")
        return str(getattr(event, "user_id", "0")), "unknown"

    if is_feishu_event(event):
        from nonebot.adapters.feishu import GroupMessageEvent, PrivateMessageEvent
        event_detail = getattr(event, "event", None)
        message = getattr(event_detail, "message", None) if event_detail else None
        chat_id = getattr(message, "chat_id", "")
        if isinstance(event, GroupMessageEvent):
            return str(chat_id), "group"
        if isinstance(event, PrivateMessageEvent):
            return str(chat_id), "private"
        return str(chat_id), "unknown"

    logger.warning("unknown adapter event: %s", _event_module(event))
    return "0", "unknown"

# ============================================================
# 用户身份
# ============================================================

def get_sender_id(event: Event) -> str:
    """
    获取消息发送者的唯一标识（字符串）。

    OneBot → str(event.user_id)      如 "2133685523"
    Feishu → event.get_user_id()      如 "ou_xxxxxxxx"
    
    用于 AI 对话中拼接 "user: {sender_id}: {msg}" 的消息前缀，
    替代旧代码中的 event.user_id（OneBot 下是 int）。
    """
    if is_onebot_event(event):
        return str(getattr(event, "user_id", ""))

    if is_feishu_event(event):
        uid = event.get_user_id()
        return str(uid) if uid else ""

    return ""

# ============================================================
# 权限判断（替代 event.sender.role）
# ============================================================

def can_manage_session(event: Event, session_type: str) -> bool:
    """
    判断消息发送者是否有权管理当前会话（清除记忆、压缩对话等操作）。

    规则：
      OneBot 私聊 → 总是允许（会话属于自己）
      OneBot 群聊 → 仅群主/管理员（event.sender.role 为 "admin" 或 "owner"）
      Feishu 私聊 → 总是允许
      Feishu 群聊 → 仅 SUPERUSERS（飞书没有群内角色概念，降级为超管白名单）

    替代旧代码中直接访问 event.sender.role 的逻辑——Feishu 事件没有 sender.role。
    """
    if is_onebot_event(event):
        if session_type == "private":
            return True
        sender = getattr(event, "sender", None)
        role = getattr(sender, "role", "") if sender else ""
        return role in ("admin", "owner")

    if is_feishu_event(event):
        if session_type == "private":
            return True
        from nonebot import get_driver
        return get_sender_id(event) in get_driver().config.superusers

    return False

# ============================================================
# 消息内容提取
# ============================================================

def get_message_text(event: Event) -> str:
    """
    提取消息中的纯文本（去除 CQ 码/飞书格式）。

    替代旧代码中的 str(event.get_message()).strip()。
    extract_plain_text() 在两个 adapter 的行为一致：只保留 text 段的内容。
    """
    return event.get_message().extract_plain_text().strip()


def is_attachment_message(event: Event) -> bool:
    """
    消息是否包含附件（图片/文件/语音/视频）。

    替代旧代码中的 is_valid_cq_code() —— 不再检查 CQ 码字符串格式，
    而是直接遍历 MessageSegment 列表，判断是否有非文本段。
    """
    for seg in event.get_message():
        if seg.type in ("image", "file", "record", "audio", "video"):
            return True
    return False


def get_attachment_segments(event: Event) -> list[dict]:
    """
    提取消息中所有附件的跨平台统一描述。

    返回结构：
      [
        {
          "type":      "image" | "file" | "audio" | "video",
          "file_name": str,
          "file_id":   str | None,   ← OneBot 专属，NapCat 的 file_id
          "file_url":  str | None,   ← OneBot 专属，直链 URL
          "file_key":  str | None,   ← Feishu 专属，上传后返回的 key
        },
        ...
      ]

    调用方拿到这个列表后，传给 download_attachment() 即可下载文件内容。
    """
    result: list[dict] = []
    for seg in event.get_message():
        if seg.type not in ("image", "file", "record", "audio", "video"):
            continue
        entry: dict = {"type": seg.type, "file_name": seg.data.get("file", "")}
        if is_onebot_event(event):
            entry["file_id"] = seg.data.get("file_id")
            entry["file_url"] = seg.data.get("url")
            entry["file_key"] = None
        elif is_feishu_event(event):
            key = seg.data.get("file_key") or seg.data.get("image_key")
            entry["file_key"] = key
            entry["file_id"] = None
            entry["file_url"] = None
            event_detail = getattr(event, "event", None)
            entry["message_id"] = getattr(
                getattr(event_detail, "message", None), "message_id", ""
            )
            entry["file_name"] = seg.data.get("file_name", entry["file_name"])
            if not entry["file_name"]:
                if seg.type == "image":
                    entry["file_name"] = f"{key}.jpg" if key else "image.jpg"
                elif seg.type == "audio":
                    entry["file_name"] = f"{key}.ogg" if key else "audio.ogg"
                elif seg.type == "video":
                    entry["file_name"] = f"{key}.mp4" if key else "video.mp4"
        result.append(entry)
    return result

# ============================================================
# 文件下载 / 上传
# ============================================================

async def download_to_cache(bot: Bot, attachment: dict) -> str | None:
    """
    下载附件到 localstore 缓存，一步返回文件路径。不经过 bytes 中转。
    适用于需要文件路径的场景（如 ai_file_reader）。
    """
    file_name = str(attachment.get("file_name", "unknown"))
    file_url = attachment.get("file_url")
    file_id = attachment.get("file_id")
    file_key = attachment.get("file_key")

    if file_url:
        tmp_path = store.get_plugin_cache_file(f"dl_{file_name}")
        code = await download_file(str(file_url), str(tmp_path))
        return str(tmp_path) if code == 0 else None

    if file_id and is_onebot(bot):
        info = await bot.call_api("get_private_file_url", file_id=file_id)  # 此处存疑
        tmp_path = store.get_plugin_cache_file(f"dl_{file_name}")
        code = await download_file(info["url"], str(tmp_path))
        return str(tmp_path) if code == 0 else None

    if file_key and is_feishu(bot):
        msg_id = attachment.get("message_id", "")
        if msg_id:
            resource_type = "image" if attachment.get("type") == "image" else "file"
            resp = await bot.call_api(
                f"im/v1/messages/{msg_id}/resources/{file_key}",
                method="GET",
                params={"type": resource_type},
                _return_response=True,
            )
            file_bytes = resp.content
        else:
            file_bytes = await bot.get_file(file_key)
        return await save_bytes_to_cache(file_bytes, "feishu_dl", file_name)

    return None


async def download_attachment(bot: Bot, attachment: dict) -> tuple[str, bytes] | None:
    """下载附件返回 (file_name, bytes)，委托给 download_to_cache。"""
    file_name = str(attachment.get("file_name", "unknown"))
    local_path = await download_to_cache(bot, attachment)
    if local_path is None:
        return None
    try:
        async with aiofiles.open(local_path, "rb") as f:
            return file_name, await f.read()
    finally:
        try:
            os.unlink(local_path)
        except OSError:
            pass


async def upload_file_to_platform(bot: Bot, file_name: str, file_data: bytes) -> str | None:
    """上传文件到平台，返回平台标识符（OneBot URL / Feishu file_key）。当前仅 backupHelper 使用。"""
    if is_onebot(bot):
        tmp_path = store.get_plugin_cache_file(f"up_{file_name}")
        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(file_data)
            require("src.plugins.public_apis")
            from src.plugins.public_apis import upload_file
            return await upload_file(str(tmp_path))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if is_feishu(bot):
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "stream"
        type_map = {
            "pdf": "pdf", "doc": "doc", "docx": "doc",
            "xls": "xls", "xlsx": "xls",
            "ppt": "ppt", "pptx": "ppt",
            "mp4": "mp4", "opus": "opus",
        }
        file_type = type_map.get(ext, "stream")
        resp = await bot.post_file(file_type=file_type, file_name=file_name, file=file_data)
        code = resp.get("code", -1)
        if code != 0:
            logger.warning(f"feishu upload_file failed: {resp}")
            return None
        return resp.get("data", {}).get("file_key")

    return None

# ============================================================
# 消息发送与构造
# ============================================================

async def send_reply(bot: Bot, session_id: str, session_type: str, content) -> None:
    """跨平台发送消息（str 或 MessageSegment）。Feishu 私聊自动用 open_id。"""
    if is_onebot(bot):
        if session_type == "group":
            await bot.send_group_msg(group_id=int(session_id), message=content)
        else:
            await bot.send_private_msg(user_id=int(session_id), message=content)
    elif is_feishu(bot):
        if session_type == "private":
            from src.plugins.aihelper.session import get_open_id
            open_id = get_open_id(session_id)
            if open_id:
                receive_id = open_id
                receive_id_type = "open_id"
            else:
                receive_id = session_id
                receive_id_type = "chat_id"
        else:
            receive_id = session_id
            receive_id_type = "chat_id"

        if isinstance(content, str):
            payload = json.dumps({"text": content})
            msg_type = "text"
        else:
            payload = json.dumps(content.data)
            msg_type = getattr(content, "type", "post") or "post"
        await bot.send_msg(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            content=payload,
            msg_type=msg_type,
        )
    else:
        logger.warning(f"send_reply: unknown adapter {bot.type}")


async def send_reply_with_event(bot: Bot, event: Event, content,
                                 session_id: str = "", session_type: str = "") -> None:
    """send_reply 的便捷包装，从 event 自动解析 session 并存储 Feishu open_id。"""
    if not session_id:
        session_id, session_type = resolve_session(event)
    if is_feishu(bot) and session_type == "private":
        uid = getattr(event, "get_user_id", lambda: None)()
        if uid:
            from src.plugins.aihelper.session import store_open_id
            store_open_id(session_id, str(uid) if uid else session_id)
    await send_reply(bot, session_id, session_type, content)


async def build_file_message(bot: Bot, file_ref: str, file_name: str = "") -> MessageSegment:
    """构造文件消息段。file_ref 为本地路径或远程 URL。Feishu 自动完成上传。"""
    if is_onebot(bot):
        from nonebot.adapters.onebot.v11 import MessageSegment as OB11MS
        return OB11MS("file", {"file": f"file://{file_ref}"})
    if is_feishu(bot):
        if not file_name:
            file_name = os.path.basename(file_ref)
        if file_ref.startswith(("http://", "https://")):
            tmp = store.get_plugin_cache_file(f"bfm_{file_name}")
            code = await download_file(file_ref, str(tmp))
            if code != 0:
                logger.warning(f"build_file_message download failed: {file_ref}")
                return MessageSegment.text("[file]")
            local = str(tmp)
        else:
            local = file_ref
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "stream"
        type_map = {
            "pdf": "pdf", "doc": "doc", "docx": "doc",
            "xls": "xls", "xlsx": "xls", "ppt": "ppt", "pptx": "ppt",
            "mp4": "mp4", "opus": "opus",
        }
        async with aiofiles.open(local, "rb") as f:
            file_data = await f.read()
        resp = await bot.post_file(
            file_type=type_map.get(ext, "stream"),
            file_name=file_name, file=file_data,
        )
        if local != file_ref:
            try:
                os.unlink(local)
            except OSError:
                pass
        code = resp.get("code", -1)
        if code != 0:
            logger.warning(f"build_file_message feishu upload failed: {resp}")
            return MessageSegment.text("[file]")
        file_key = resp.get("data", {}).get("file_key")
        from nonebot.adapters.feishu import MessageSegment as FeishuMS
        return FeishuMS.file(file_key=file_key, file_name=file_name)
    return MessageSegment.text("[file]")


def build_text_message(bot: Bot, text: str) -> MessageSegment:
    """构造文本消息段（平台无关，但返回对应类型的 MessageSegment）。"""
    if is_onebot(bot):
        from nonebot.adapters.onebot.v11 import MessageSegment as OB11MS
        return OB11MS.text(text)
    if is_feishu(bot):
        from nonebot.adapters.feishu import MessageSegment as FeishuMS
        return FeishuMS.text(text)
    return MessageSegment.text(text)


def build_at_message(bot: Bot, user_id: str) -> MessageSegment:
    """
    构造 @ 消息段。

    OneBot → MessageSegment.at(qq号)
    Feishu → MessageSegment.at(open_id)
    user_id 参数在不同平台下的语义不同，调用方需传正确的 ID。
    """
    if is_onebot(bot):
        from nonebot.adapters.onebot.v11 import MessageSegment as OB11MS
        return OB11MS.at(user_id)
    if is_feishu(bot):
        from nonebot.adapters.feishu import MessageSegment as FeishuMS
        return FeishuMS.at(user_id)
    return MessageSegment.text("")
