from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent, GroupMessageEvent, Message
from nonebot.params import CommandArg

from .yaohud_ai_handle import get_index_tts2

index_tts2 = on_command("tts")


@index_tts2.handle()
async def index_tts2_handle(event: MessageEvent, args: Message = CommandArg()):
    """
    IndexTTS2-语音合成 , 当前支持角色, 英文支持不行
    原神: 希格雯/神里绫华/胡桃/可莉/芙宁娜
    星穹铁道: 阮梅
    明日方舟: 多萝西
    用法  [角色] [内容]
    """
    if isinstance(event, GroupMessageEvent):
        await index_tts2.finish("403")
    data = args.extract_plain_text().strip().split()
    if len(data) != 2:
        await index_tts2.finish("参数数量不正确")
    _res = await get_index_tts2(voice_from=data[0], voice_txt=data[1])
    if _res == -1:
        await index_tts2.finish("fail")
    else:
        _file = MessageSegment("file", {"file": f"file://{_res}"})
        await index_tts2.finish(_file)
