from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment

from .yaohud_image_handle import get_acg_adaptive

acg_adaptive = on_command("acg adaptive")


@acg_adaptive.handle()
async def acg_adaptive_handle():
    path_jpg = await get_acg_adaptive()

    if path_jpg == -1:
        await acg_adaptive.finish("failed")
    else:
        await acg_adaptive.finish(MessageSegment.image(path_jpg))
