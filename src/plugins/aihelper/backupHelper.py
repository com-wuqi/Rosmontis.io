from nonebot import on_command
from nonebot import require
from nonebot.adapters import Event, Bot

from .aihelper_handles import get_comments_by_id, save_comments_to_file
from ..shared.adapter_utils import resolve_session, build_file_message

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session


backup_comments = on_command("ai cm bk")
restore_comments = on_command("ai cm rt")


@backup_comments.handle()
async def backup_comments_handle(bot: Bot, event: Event, session: async_scoped_session):
    session_id, session_type = resolve_session(event)
    _res = await get_comments_by_id(sid=session_id, session=session)

    if _res is None or not _res.message:
        await backup_comments.finish("is empty")

    _remote_path = await save_comments_to_file(
        _raw_msg=_res.message, msg_type=session_type, user_id=session_id
    )
    if _remote_path == "":
        await backup_comments.finish("fail")

    _file = await build_file_message(bot, _remote_path)
    await backup_comments.finish(_file)


@restore_comments.handle()
async def restore_comments_handle():
    await backup_comments.finish("请联系数据库维护来还原数据, 这里处于安全考虑不支持自助完成")
