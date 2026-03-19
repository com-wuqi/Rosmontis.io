from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent, MessageSegment, Message
from nonebot.params import CommandArg

from . import tts_api_handle, config

if config.is_enable_gpt_sovits:
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

if config.is_enable_qwen3_customvoice:
    qwen3_customvoice = on_command("qwen3-cvoice")


    @qwen3_customvoice.handle()
    async def qwen3_customvoice_handleer(event: MessageEvent, arg: Message = CommandArg()):
        if not isinstance(event, PrivateMessageEvent):
            await qwen3_customvoice.finish("it is not a PrivateMessageEvent")
        text = arg.extract_plain_text().strip()
        if not text:
            await qwen3_customvoice.finish("qwen3_customvoice 需要文本")
        _res = await tts_api_handle.qwen3_tts_customvoice(text)
        _file = MessageSegment("file", {"file": f"file://{_res}"})
        await qwen3_customvoice.finish(_file)

if config.is_enable_qwen3_voice_design:
    qwen3_voice_design = on_command("qwen3-vdesign")


    @qwen3_voice_design.handle()
    async def qwen3_voice_design_handle(event: MessageEvent, arg: Message = CommandArg()):
        if not isinstance(event, PrivateMessageEvent):
            await qwen3_voice_design.finish("it is not a PrivateMessageEvent")
        if config.qwen3_tts_voice_design_design == "":
            await qwen3_voice_design.finish("qwen3_voice_design need 'design' in config")
        text = arg.extract_plain_text().strip()
        if not text:
            await qwen3_voice_design.finish("qwen3_voice_design 需要文本")
        _res = await tts_api_handle.qwen3_tts_voice_design(text)
        _file = MessageSegment("file", {"file": f"file://{_res}"})
        await qwen3_customvoice.finish(_file)
