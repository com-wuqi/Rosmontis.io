from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from nonebot.params import CommandArg

from .yaohud_music_handle import get_common_music

netease_music = on_command("163mu")
qq_music = on_command("qqmu")


# 用法 163mu|qqmu [搜索名称] [选择的id | null]

@netease_music.handle()
async def netease_music_handle(args: Message = CommandArg()):
    args_list = args.extract_plain_text().strip().split()
    if len(args_list) != 2 and len(args_list) != 1:
        await netease_music.finish(f"参数个数不正确 : {len(args_list)}")
    if len(args_list) == 1:
        _res = await get_common_music(api_type="wyvip", msg_type="search", msg=args_list[0])
        await netease_music.send(_res)
        await netease_music.send("可以这样选择下载, 替换1为序号:")
        await netease_music.finish(f"*163mu {args_list[0]} 1")
    if len(args_list) == 2:
        if not args_list[1].isdigit():
            await netease_music.finish("参数不合法, 第二个参数需要是数字")
        _res = await get_common_music(api_type="wyvip", msg_type="get", msg=args_list[0], n=int(args_list[1]))
        if _res == -1:
            await netease_music.finish("failed")
        else:
            _file = MessageSegment("file", {"file": f"file://{_res}"})
            await netease_music.finish(_file)


@qq_music.handle()
async def qq_music_handle(args: Message = CommandArg()):
    args_list = args.extract_plain_text().strip().split()
    if len(args_list) != 2 and len(args_list) != 1:
        await qq_music.finish(f"参数个数不正确 : {len(args_list)}")
    if len(args_list) == 1:
        _res = await get_common_music(api_type="qq_plus", msg_type="search", msg=args_list[0])
        await qq_music.send(_res)
        await qq_music.send("可以这样选择下载, 替换1为序号:")
        await qq_music.finish(f"*qqmu {args_list[0]} 1")
    if len(args_list) == 2:
        if not args_list[1].isdigit():
            await qq_music.finish("参数不合法, 第二个参数需要是数字")
        _res = await get_common_music(api_type="qq_plus", msg_type="get", msg=args_list[0], n=int(args_list[1]))
        if _res == -1:
            await qq_music.finish("failed")
        else:
            _file = MessageSegment("file", {"file": f"file://{_res}"})
            await qq_music.finish(_file)
