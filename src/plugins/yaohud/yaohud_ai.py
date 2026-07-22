from nonebot import on_command
from nonebot.adapters import Event, Bot, Message
from nonebot.params import CommandArg

from .yaohud_ai_handle import get_index_tts2, get_weijin, get_yaohu_picture
from ..shared.adapter_utils import resolve_session, build_file_message, send_reply_with_event

index_tts2 = on_command("yaohud-tts")
weijin_check = on_command("weijin")
yaohu_picture_ai = on_command("aidraw")


@index_tts2.handle()
async def index_tts2_handle(event: Event, bot: Bot, args: Message = CommandArg()):
    """
    IndexTTS2-语音合成 , 当前支持角色, 英文支持不行
    用法  [角色] [内容]
    """
    _, session_type = resolve_session(event)
    if session_type != "private":
        await index_tts2.finish("403")
    data = args.extract_plain_text().strip().split()
    if len(data) != 2:
        await index_tts2.finish("参数数量不正确")
    _res = await get_index_tts2(voice_from=data[0], voice_txt=data[1])
    if _res == -1:
        await index_tts2.finish("fail")
    _file = await build_file_message(bot, _res)
    await send_reply_with_event(bot, event, _file)


@weijin_check.handle()
async def weijin_check_handle(args: Message = CommandArg()):
    string = args.extract_plain_text().strip()
    if string == "" or string is None:
        await weijin_check.finish(str(True))
        return
    _res = await get_weijin(txt=string)
    await weijin_check.finish(str(bool(_res)))


@yaohu_picture_ai.handle()
async def yaohu_picture_ai_handle(event: Event, bot: Bot, args: Message = CommandArg()):
    string = args.extract_plain_text().strip()
    if string == "" or string is None:
        await send_reply_with_event(bot, event, "need txt")
        return
    _check = await get_weijin(txt=string)
    if not _check:
        await send_reply_with_event(bot, event, "failed before check")
        return
    _res = await get_yaohu_picture(txt=string)
    if _res == -1:
        await send_reply_with_event(bot, event, "fail")
        return
    _file = await build_file_message(bot, _res)
    await send_reply_with_event(bot, event, _file)
