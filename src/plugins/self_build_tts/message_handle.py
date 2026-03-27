from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent, MessageSegment, Message, Bot
from nonebot.params import CommandArg, Arg
from nonebot.typing import T_State

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
    async def qwen3_customvoice_handle(event: MessageEvent, arg: Message = CommandArg()):
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
        await qwen3_voice_design.finish(_file)

if config.is_enable_qwen3_base:
    # 很奇怪的问题: 在使用 got 的信息中, CommandArg 似乎有问题,
    # Arg() 和 ArgPlainText() 正常, 注意需要传入和 key 相同的字符串

    qwen3_clone = on_command("qwen3_clone")


    @qwen3_clone.handle()
    async def qwen3_clone_handle(event: MessageEvent, state: T_State):
        if not isinstance(event, PrivateMessageEvent):
            await qwen3_clone.finish("it is not a PrivateMessageEvent")
        state["user_id"] = event.user_id
        await qwen3_clone.send("非文件信息视为取消")


    @qwen3_clone.got("ref_aud", prompt="上传参考音频")
    async def qwen3_clone_got_ref_aud(bot: Bot, event: MessageEvent, state: T_State):
        for segment in event.message:
            if segment.type == "file":
                logger.debug("file: {}".format(segment.data))
                file_id = segment.data.get("file_id")  # 文件的唯一ID
                file_name = segment.data.get("file")  # 文件名
                # file_size = segment.data.get("size")  # 文件大小 (字节)
                msg_detail = await bot.call_api("get_private_file_url", file_id=file_id)
                logger.debug(f"msg_detail[\"url\"]: {msg_detail["url"]}")
                logger.debug("file_name: {}".format(file_name))
                _files = await tts_api_handle.get_private_file_from_url(
                    url=msg_detail["url"], file_name=file_name, user_id=state["user_id"]
                )
                logger.debug("_files: {}".format(_files))
                state["ref_aud"] = _files
                return
        await qwen3_clone.finish("cancled")


    @qwen3_clone.got("qwen3_clone_ref_txt", prompt="参考音频文本")
    async def qwen3_clone_get_ref_txt(state: T_State, arg: Message = Arg("qwen3_clone_ref_txt")):
        _str_ref_txt = arg.extract_plain_text().strip()
        if not _str_ref_txt:
            await qwen3_clone.reject("需要 参考音频文本")
        state["qwen3_clone_ref_txt"] = _str_ref_txt


    @qwen3_clone.got("confirm", prompt="是否确定? y/n")
    async def qwen3_clone_confirm(state: T_State, arg: Message = Arg("confirm")):
        if arg.extract_plain_text().strip() not in ["y", "n"]:
            await qwen3_clone.reject("输入需要是 y 或者 n")
        if arg.extract_plain_text().strip() == "n":
            await qwen3_clone.finish("canceled")
        # logger.debug(f"ref_aud type: {type(state['ref_aud'])}")
        # logger.debug(f"ref_aud value: {state['ref_aud']}")
        # logger.debug(f"ref_txt type: {type(state["qwen3_clone_ref_txt"])}")
        # logger.debug(f"ref_txt value: {state["qwen3_clone_ref_txt"]}")
        _res = await tts_api_handle.qwen3_tts_base_save_prompt(
            ref_aud=state["ref_aud"], ref_txt=state["qwen3_clone_ref_txt"]
        )
        _file = MessageSegment("file", {"file": f"file://{_res}"})
        await qwen3_clone.finish(_file)


    qwen3_generate = on_command("qwen3_gen")


    @qwen3_generate.handle()
    async def qwen3_gen_handle(event: MessageEvent, state: T_State):
        if not isinstance(event, PrivateMessageEvent):
            await qwen3_generate.finish("it is not a PrivateMessageEvent")
        state["user_id"] = event.user_id
        await qwen3_generate.send("非文件信息视为取消")


    @qwen3_generate.got("file_obj", prompt="模型文件?")
    async def qwen3_gen_got_file_obj(event: MessageEvent, state: T_State, bot: Bot):
        for segment in event.message:
            if segment.type == "file":
                logger.debug("file: {}".format(segment.data))
                file_id = segment.data.get("file_id")  # 文件的唯一ID
                file_name = segment.data.get("file")  # 文件名

                msg_detail = await bot.call_api("get_private_file_url", file_id=file_id)
                _files = await tts_api_handle.get_private_file_from_url(
                    url=msg_detail["url"], file_name=file_name, user_id=state["user_id"]
                )
                logger.debug("_files: {}".format(_files))
                state["file_obj"] = _files
                return
        await qwen3_generate.finish("cancled")


    @qwen3_generate.got("qwen3_gen_text", prompt="待合成文本")
    async def qwen3_gen_got_text(state: T_State, arg: Message = Arg("qwen3_gen_text")):
        _text = arg.extract_plain_text().strip()
        if not _text:
            await qwen3_generate.finish("需要 待合成文本")
        state["qwen3_gen_text"] = _text


    @qwen3_generate.got("confirm", prompt="是否确定? y/n")
    async def qwen3_gen_confirm(state: T_State, arg: Message = Arg("confirm")):
        if arg.extract_plain_text().strip() not in ["y", "n"]:
            await qwen3_generate.reject("输入需要是 y 或者 n")
        if arg.extract_plain_text().strip() == "n":
            await qwen3_generate.finish("canceled")
        _res = await tts_api_handle.qwen3_tts_base_gen(
            file_path=state["file_obj"],
            text=state["qwen3_gen_text"],
        )
        _file = MessageSegment("file", {"file": f"file://{_res}"})
        await qwen3_generate.finish(_file)
