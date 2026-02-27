from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from nonebot.params import CommandArg, Command

from .yaohud_music_handle import get_common_music

netease_music = on_command("163mu")
qq_music = on_command("qqmu")


# 用法 163mu|qqmu [搜索名称] [选择的id | null]

@netease_music.handle()
@qq_music.handle()
async def common_music_handle(cmd: tuple[str, ...] = Command(), args: Message = CommandArg()):
    cmd_name = cmd[0]
    if cmd_name == "163mu":
        api_type = "wyvip"
    elif cmd_name == "qqmu":
        api_type = "qq_plus"
    else:
        return

    args_list = args.extract_plain_text().strip().split()
    if len(args_list) != 2 and len(args_list) != 1:
        await netease_music.finish(f"参数个数不正确 : {len(args_list)}")
    if len(args_list) == 1:
        _res = await get_common_music(api_type=api_type, msg_type="search", msg=args_list[0])
        if _res == -1:
            await netease_music.finish("failed")
        await netease_music.send(_res)
        await netease_music.send("可以这样选择下载, 替换1为序号:")
        await netease_music.finish(f"*{cmd_name} {args_list[0]} 1")
    if len(args_list) == 2:
        if not args_list[1].isdigit():
            await netease_music.finish("参数不合法, 第二个参数需要是数字")
        _res = await get_common_music(api_type=api_type, msg_type="get", msg=args_list[0], n=int(args_list[1]))
        if _res == -1:
            await netease_music.finish("failed")
        else:
            _file = MessageSegment("file", {"file": f"file://{_res}"})
            await netease_music.finish(_file)

