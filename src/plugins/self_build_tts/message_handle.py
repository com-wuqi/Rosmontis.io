from nonebot import on_command, logger
from nonebot.adapters import Bot, Event, Message
from nonebot.params import CommandArg, Arg
from nonebot.typing import T_State

from . import tts_api_handle, config
from ..shared.adapter_utils import (
    resolve_session,
    get_sender_id,
    get_attachment_segments,
    download_attachment,
    build_file_message,
    save_bytes_to_cache,
    send_reply_with_event,
    get_event_bot,
)


if config.is_enable_gpt_sovits:
    gpt_tts = on_command("gpt-tts")


    @gpt_tts.handle()
    async def gpt_tts_handle(event: Event, bot: Bot, arg: Message = CommandArg()):
        session_id, session_type = resolve_session(event)
        if session_type != "private":
            await gpt_tts.finish("it is not a private session")
        text = arg.extract_plain_text().strip()
        if not text:
            await gpt_tts.finish("gpt_sovits 需要 tts 文本")

        logger.debug(f"gpt_tts_handle.text : {text}")

        get_request_url = await tts_api_handle.built_gpt_sovits_url_tts(text)
        if not get_request_url:
            logger.warning("gpt_sovits failed to get_request_url")
            await gpt_tts.finish(f"gpt_sovits gpt_tts_handle : {get_request_url}")
        _remote_path, _msg = await tts_api_handle.download_gpt_sovits_tts_file(
            get_request_url
        )
        if not _remote_path:
            logger.warning(f"gpt_sovits failed: {_msg}")
            await gpt_tts.finish(f"gpt_sovit failed: {_msg}")

        _file = await build_file_message(bot, _remote_path)
        await send_reply_with_event(bot, event, _file,
                                     session_id=session_id, session_type=session_type)


if config.is_enable_qwen3_customvoice:
    qwen3_customvoice = on_command("qwen3-cvoice")


    @qwen3_customvoice.handle()
    async def qwen3_customvoice_handle(
        event: Event, bot: Bot, arg: Message = CommandArg()
    ):
        _, session_type = resolve_session(event)
        if session_type != "private":
            await qwen3_customvoice.finish("it is not a private session")
        text = arg.extract_plain_text().strip()
        if not text:
            await qwen3_customvoice.finish("qwen3_customvoice 需要文本")
        _res = await tts_api_handle.qwen3_tts_customvoice(text)
        _file = await build_file_message(bot, _res)
        await qwen3_customvoice.finish(_file)


if config.is_enable_qwen3_voice_design:
    qwen3_voice_design = on_command("qwen3-vdesign")

    @qwen3_voice_design.handle()
    async def qwen3_voice_design_handle(
        event: Event, bot: Bot, arg: Message = CommandArg()
    ):
        _, session_type = resolve_session(event)
        if session_type != "private":
            await qwen3_voice_design.finish("it is not a private session")
        if config.qwen3_tts_voice_design_design == "":
            await qwen3_voice_design.finish(
                "qwen3_voice_design need 'design' in config"
            )
        text = arg.extract_plain_text().strip()
        if not text:
            await qwen3_voice_design.finish("qwen3_voice_design 需要文本")
        _res = await tts_api_handle.qwen3_tts_voice_design(text)
        _file = await build_file_message(bot, _res)
        await qwen3_voice_design.finish(_file)


if config.is_enable_qwen3_base:
    # 很奇怪的问题: 在使用 got 的信息中, CommandArg 似乎有问题,
    # Arg() 和 ArgPlainText() 正常, 注意需要传入和 key 相同的字符串

    qwen3_clone = on_command("qwen3_clone")

    @qwen3_clone.handle()
    async def qwen3_clone_handle(event: Event, bot: Bot, state: T_State):
        session_id, session_type = resolve_session(event)
        if session_type != "private":
            await send_reply_with_event(
                bot,
                event,
                "it is not a private session",
                session_id=session_id,
                session_type=session_type,
            )
            return
        state["user_id"] = get_sender_id(event)
        state["_event"] = event
        await qwen3_clone.send("非文件信息视为取消")

    @qwen3_clone.got("ref_aud", prompt="上传参考音频")
    async def qwen3_clone_got_ref_aud(event: Event, bot: Bot, state: T_State):
        attachments = get_attachment_segments(event)
        for att in attachments:
            if att["type"] != "file":
                continue
            file_name = att["file_name"]
            downloaded = await download_attachment(bot, att)
            if downloaded is None:
                logger.warning(f"failed to download {file_name}")
                continue
            _, file_bytes = downloaded
            user_id = str(state.get("user_id", ""))
            local_path = await save_bytes_to_cache(file_bytes, user_id, file_name)
            if local_path:
                state["ref_aud"] = local_path
                logger.debug(f"ref_aud saved to {local_path}")
                return
        await qwen3_clone.finish("cancled")

    @qwen3_clone.got("qwen3_clone_ref_txt", prompt="参考音频文本")
    async def qwen3_clone_get_ref_txt(
        state: T_State, arg: Message = Arg("qwen3_clone_ref_txt")
    ):
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
            return
        event = state.get("_event")
        bot = get_event_bot(event) if event else None
        if bot is None:
            return
        _res = await tts_api_handle.qwen3_tts_base_save_prompt(
            ref_aud=state["ref_aud"], ref_txt=state["qwen3_clone_ref_txt"]
        )
        _file = await build_file_message(bot, _res)
        await send_reply_with_event(bot, event, _file)

    qwen3_generate = on_command("qwen3_gen")

    @qwen3_generate.handle()
    async def qwen3_gen_handle(event: Event, bot: Bot, state: T_State):
        session_id, session_type = resolve_session(event)
        if session_type != "private":
            await send_reply_with_event(
                bot,
                event,
                "it is not a private session",
                session_id=session_id,
                session_type=session_type,
            )
            return
        state["user_id"] = get_sender_id(event)
        state["_event"] = event
        await qwen3_generate.send("非文件信息视为取消")

    @qwen3_generate.got("file_obj", prompt="模型文件?")
    async def qwen3_gen_got_file_obj(event: Event, bot: Bot, state: T_State):
        attachments = get_attachment_segments(event)
        for att in attachments:
            if att["type"] != "file":
                continue
            file_name = att["file_name"]
            downloaded = await download_attachment(bot, att)
            if downloaded is None:
                logger.warning(f"failed to download {file_name}")
                continue
            _, file_bytes = downloaded
            user_id = str(state.get("user_id", ""))
            local_path = await save_bytes_to_cache(file_bytes, user_id, file_name)
            if local_path:
                state["file_obj"] = local_path
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
            return
        event = state.get("_event")
        bot = get_event_bot(event) if event else None
        if bot is None:
            return
        _res = await tts_api_handle.qwen3_tts_base_gen(
            file_path=state["file_obj"],
            text=state["qwen3_gen_text"],
        )
        _file = await build_file_message(bot, _res)
        await send_reply_with_event(bot, event, _file)
