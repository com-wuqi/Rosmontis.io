from nonebot import on_command
from nonebot.adapters import Event, Bot

from .yaohud_image_handle import get_acg
from ..shared.adapter_utils import (
    resolve_session,
    build_file_message,
    send_reply_with_event,
)

acg_adaptive = on_command("acg adaptive")
acg_ai = on_command("acg ai")
acg_r18 = on_command("acg r18")


@acg_adaptive.handle()
async def acg_adaptive_handle(event: Event, bot: Bot):
    path_jpg = await get_acg("adaptive")
    if path_jpg == -1:
        await send_reply_with_event(bot, event, "failed")
        return
    _msg = await build_file_message(bot, path_jpg)
    await send_reply_with_event(bot, event, _msg)


@acg_ai.handle()
async def acg_ai_handle(event: Event, bot: Bot):
    path_jpg = await get_acg("ai")
    if path_jpg == -1:
        await send_reply_with_event(bot, event, "failed")
        return
    _msg = await build_file_message(bot, path_jpg)
    await send_reply_with_event(bot, event, _msg)


@acg_r18.handle()
async def acg_r18_handle(event: Event, bot: Bot):
    _, session_type = resolve_session(event)
    if session_type != "private":
        await send_reply_with_event(bot, event, "403")
        return
    path_jpg = await get_acg("r18")
    if path_jpg == -1:
        await send_reply_with_event(bot, event, "failed")
        return
    _msg = await build_file_message(bot, path_jpg)
    await send_reply_with_event(bot, event, _msg)
