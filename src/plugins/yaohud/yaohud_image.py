from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent, GroupMessageEvent

from .yaohud_image_handle import get_acg

acg_adaptive = on_command("acg adaptive")
acg_ai = on_command("acg ai")
acg_r18 = on_command("acg r18")

@acg_adaptive.handle()
async def acg_adaptive_handle():
    path_jpg = await get_acg("adaptive")

    if path_jpg == -1:
        await acg_adaptive.finish("failed")
    else:
        await acg_adaptive.finish(MessageSegment.image(path_jpg))


@acg_ai.handle()
async def acg_ai_handle():
    path_jpg = await get_acg("ai")

    if path_jpg == -1:
        await acg_ai.finish("failed")
    else:
        await acg_ai.finish(MessageSegment.image(path_jpg))


@acg_r18.handle()
async def acg_ai_handle(event: MessageEvent):
    if isinstance(event, GroupMessageEvent):
        await acg_ai.finish("403")
    path_jpg = await get_acg("r18")
    if path_jpg == -1:
        await acg_r18.finish("failed")
    else:
        await acg_r18.finish(MessageSegment.image(path_jpg))
