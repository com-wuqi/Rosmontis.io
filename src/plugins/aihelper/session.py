import json

from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session as get_orm_session

from . import get_redis, _SESSION_TTL, _SESSION_PREFIX

_Messages_dicts: dict[str, list] = {}
_ai_switch: dict[str, bool] = {}
_config_settings: dict[str, object] = {}
_open_ids: dict[str, str] = {}


def store_open_id(session_id: str, open_id: str) -> None:
    """缓存 Feishu 私聊 chat_id → open_id 映射，供 send_reply 使用。"""
    _open_ids[session_id] = open_id


def get_open_id(session_id: str) -> str | None:
    """查询 chat_id 对应的 open_id。"""
    return _open_ids.get(session_id)


async def _session_load(sid: str) -> tuple[list, bool]:
    data = await get_redis().hgetall(f"{_SESSION_PREFIX}{sid}")
    if not data:
        return [], False
    messages = json.loads(data.get("messages", "[]"))
    active = data.get("active", "0") == "1"
    return messages, active


async def _session_save(sid: str, messages: list, active: bool) -> None:
    # 写入 redis
    key = f"{_SESSION_PREFIX}{sid}"
    await get_redis().hset(key, mapping={
        "messages": json.dumps(messages, ensure_ascii=False),
        "active": "1" if active else "0",
    })
    if active:
        await get_redis().expire(key, _SESSION_TTL)  # 这里执行延期
    else:
        await get_redis().expire(key, int(_SESSION_TTL / 2))


async def _session_delete(sid: str) -> None:
    await get_redis().delete(f"{_SESSION_PREFIX}{sid}")


async def _ensure_session_loaded(sid: str, sender_id: str = "") -> None:
    if sid in _Messages_dicts:
        return
    msgs, active = await _session_load(sid)
    if msgs != _Messages_dicts.get(sid) or active != _ai_switch.get(sid):
        logger.warning("_ensure_session_loaded use redis data to cover memory")
    _Messages_dicts[sid] = msgs
    _ai_switch[sid] = active
    if active:
        from .aihelper_handles import get_config_by_id

        async with get_orm_session() as session:
            row = await get_config_by_id(sid=sid, session=session)
            if row is None and not sender_id:
                sender_id = _open_ids.get(sid, "")
            if row is None and sender_id:
                row = await get_config_by_id(sid=sender_id, session=session)
            if row is None:
                logger.warning(f"config not found for sid={sid}, using default")
                row = await get_config_by_id(sid="1", session=session)
            _config_settings[sid] = row
        logger.debug(f"Session {sid} recovered from Redis: {len(msgs)} messages")
