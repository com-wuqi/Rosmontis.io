from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from .yaohud_other_handle import whois

whois_run = on_command("whois")


@whois_run.handle()
async def whois_run_handle(args: Message = CommandArg()):
    data = args.extract_plain_text().strip().split()
    if len(data) != 1:
        await whois_run.finish("参数个数不正确")
    _res = await whois(url=data[0])
    if _res == -1:
        await whois_run.finish("whois error")
    else:
        await whois_run.finish(f"whois : {str(_res)}")
