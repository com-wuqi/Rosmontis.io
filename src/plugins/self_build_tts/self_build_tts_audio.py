from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent, MessageSegment
from nonebot.params import CommandArg

from . import self_build_tts_data

gpt_tts = on_command("tts ai")

@gpt_tts.handle()
async def _(event: PrivateMessageEvent,arg: Message = CommandArg()):
    text = arg.extract_plain_text().strip()
    if not text:
        await gpt_tts.finish("请输入文本")

    # 在调用API前打印
    logger.debug(f"准备调用API，文本: {text}")

    get_request_url = await self_build_tts_data.built_url_tts(text)
    if not get_request_url:
        await gpt_tts.finish(f"文本获取失败")
    _remote_path, error_msg = await self_build_tts_data.download_tts_file(get_request_url)
    if not _remote_path:
        await gpt_tts.finish(f"语音合成失败，{error_msg}")

    _file = MessageSegment("file", {"file": f"file://{_remote_path}"})
    await gpt_tts.finish(_file)

