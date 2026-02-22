from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment

from .yaohud_image_handle import get_acg_adaptive

acg_adaptive = on_command("acg adaptive")


@acg_adaptive.handle()
async def acg_adaptive_handle():
    url = await get_acg_adaptive()
    await acg_adaptive.finish(MessageSegment.image(url))
    pass
