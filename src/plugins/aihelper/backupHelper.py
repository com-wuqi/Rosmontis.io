import time

import aiofiles
from nonebot import on_command, require
from nonebot.adapters import Event, Bot

require("nonebot_plugin_orm")
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store
from nonebot_plugin_orm import async_scoped_session

from .aihelper_handles import get_comments_by_id
from ..shared.adapter_utils import resolve_session, build_file_message


backup_comments = on_command("ai cm bk")
restore_comments = on_command("ai cm rt")


@backup_comments.handle()
async def backup_comments_handle(bot: Bot, event: Event, session: async_scoped_session):
    session_id, session_type = resolve_session(event)
    _res = await get_comments_by_id(sid=session_id, session=session)

    if _res is None or not _res.message:
        await backup_comments.finish("is empty")

    local_path = store.get_plugin_cache_file(
        f"{session_id}_{session_type}_{time.time()}.txt"
    )
    async with aiofiles.open(local_path, "w", encoding="utf-8") as f:
        await f.write(_res.message)

    _file = await build_file_message(bot, str(local_path))
    await backup_comments.finish(_file)


@restore_comments.handle()
async def restore_comments_handle():
    await backup_comments.finish(
        "请联系数据库维护来还原数据, 这里处于安全考虑不支持自助完成"
    )
