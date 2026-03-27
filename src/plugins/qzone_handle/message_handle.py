from nonebot import on_command, get_driver
from nonebot import require
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message
from nonebot.log import logger
from nonebot.params import CommandArg

require("src.plugins.Qzone_toolkit")
import src.plugins.Qzone_toolkit as qzone

_super_users = get_driver().config.superusers
send_a_text_qzone = on_command("qzone txt")


@send_a_text_qzone.handle()
async def send_a_text_qzone_handle(event: MessageEvent, args: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent):
        await send_a_text_qzone.finish("it is a group message")
    if str(event.user_id) not in _super_users:
        logger.warning("user : {} tried to send_a_text_qzone".format(event.user_id))
        await send_a_text_qzone.finish("failed")
    _lists = args.extract_plain_text().strip().split()
    _msg = "\n".join(_lists)
    logger.debug("self_id is {}".format(event.self_id))
    try:
        _res = await qzone.send(message=_msg, qq=str(event.self_id))
    except Exception as e:
        logger.warning("send_a_text_qzone failed : {}".format(e))

    await send_a_text_qzone.finish("finished")
