from nonebot import on_command
from nonebot.adapters import Event, Bot, Message
from nonebot.params import CommandArg, Command

from .yaohud_music_handle import get_common_music
from ..shared.adapter_utils import build_file_message, send_reply_with_event

netease_music = on_command("163mu")
qq_music = on_command("qqmu")
kuwo_music = on_command("kuwo")
apple_music = on_command("applemu")


@netease_music.handle()
@qq_music.handle()
@kuwo_music.handle()
@apple_music.handle()
async def common_music_handle(event: Event, bot: Bot, cmd: tuple[str, ...] = Command(), args: Message = CommandArg()):
    cmd_name = cmd[0]
    if cmd_name == "163mu":
        api_type = "wyvip"
    elif cmd_name == "qqmu":
        api_type = "qq_plus"
    elif cmd_name == "kuwo":
        api_type = "kuwo"
    elif cmd_name == "applemu":
        api_type = "applemu"
    else:
        return

    args_list = args.extract_plain_text().strip().split()
    if len(args_list) not in (1, 2):
        await send_reply_with_event(bot, event, f"参数个数不正确 : {len(args_list)}")
        return
    if len(args_list) == 1:
        _res = await get_common_music(api_type=api_type, msg_type="search", msg=args_list[0])
        if _res == -1:
            await send_reply_with_event(bot, event, "failed")
            return
        await send_reply_with_event(bot, event, str(_res))
        await send_reply_with_event(bot, event, "可以这样选择下载, 替换1为序号:")
        await send_reply_with_event(bot, event, f"*{cmd_name} {args_list[0]} 1")
        return
    if len(args_list) == 2:
        if not args_list[1].isdigit():
            await send_reply_with_event(bot, event, "参数不合法, 第二个参数需要是数字")
            return
        _res = await get_common_music(api_type=api_type, msg_type="get", msg=args_list[0], n=int(args_list[1]))
        if _res == -1:
            await send_reply_with_event(bot, event, "failed")
            return
        _file = await build_file_message(bot, _res)
        await send_reply_with_event(bot, event, _file)
