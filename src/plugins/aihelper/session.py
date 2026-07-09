import json

from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session as get_orm_session

from . import get_redis, _SESSION_TTL, _SESSION_PREFIX

_Messages_dicts: dict[str, list] = {}
_ai_switch: dict[str, bool] = {}
_config_settings: dict[str, object] = {}


async def _session_load(sid: str) -> tuple[list, bool]:
    data = await get_redis().hgetall(f"{_SESSION_PREFIX}{sid}")
    if not data:
        return [], False
    messages = json.loads(data.get("messages", "[]"))
    active = data.get("active", "0") == "1"
    return messages, active


async def _session_save(sid: str, messages: list, active: bool) -> None:
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


async def _ensure_session_loaded(sid: str) -> None:
    # 这里确保正确加载（包括从redis里面恢复）
    if sid in _Messages_dicts:
        return
    msgs, active = await _session_load(sid)
    _Messages_dicts[sid] = msgs
    _ai_switch[sid] = active
    if active:
        from .aihelper_handles import get_config_by_id

        async with get_orm_session() as session:
            row = await get_config_by_id(sid=sid, session=session)
            _config_settings[sid] = row
        logger.debug(f"Session {sid} recovered from Redis: {len(msgs)} messages")
