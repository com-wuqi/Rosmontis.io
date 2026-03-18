from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent, MessageSegment, Message
from nonebot.params import CommandArg

from . import tts_api_handle

gpt_tts = on_command("gpt-tts")

@gpt_tts.handle()
async def gpt_tts_handle(event: MessageEvent, arg: Message = CommandArg()):
    if not isinstance(event, PrivateMessageEvent):
        await gpt_tts.finish("it is not a PrivateMessageEvent")

    text = arg.extract_plain_text().strip()
    if not text:
        await gpt_tts.finish("gpt_sovits 需要 tts 文本")

    # 在调用API前打印
    logger.debug(f"gpt_tts_handle.text : {text}")

    get_request_url = await tts_api_handle.built_gpt_sovits_url_tts(text)
    if not get_request_url:
        logger.warning(f"gpt_sovits failed to get_request_url")
        await gpt_tts.finish(f"gpt_sovits gpt_tts_handle : {get_request_url}")
    _remote_path, _msg = await tts_api_handle.download_gpt_sovits_tts_file(get_request_url)
    if not _remote_path:
        logger.warning(f"gpt_sovits failed: {_msg}")
        await gpt_tts.finish(f"gpt_sovit failed: {_msg}")

    _file = MessageSegment("file", {"file": f"file://{_remote_path}"})
    await gpt_tts.finish(_file)

