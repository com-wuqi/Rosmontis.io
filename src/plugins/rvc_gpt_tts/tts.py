import asyncio
import time

import aiofiles
from nonebot import on_command, logger, Bot, require
from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
from nonebot.params import CommandArg
import traceback

from ..public_apis import upload_file

require("src.plugins.public_apis")
from . import rvc_gpt_tts_data
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

"""
## 请先去你的整合包里运行命令:

## python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

## 执行参数:
    `-a` - `绑定地址, 默认"127.0.0.1"`
    `-p` - `绑定端口, 默认9880`
    `-c` - `TTS配置文件路径, 默认"GPT_SoVITS/configs/tts_infer.yaml"`
"""

gpt_tts = on_command("tts ai", block=True)
_semaphore_file = asyncio.Semaphore(60)


# 下载音频文件
async def download_file(audio_data):
    async with _semaphore_file:
        try:
            # 下载文件
            temp_path = store.get_plugin_cache_file(f"rvc_gpt_tts-{time.time()}.wav")
            logger.info(f"临时音频文件: {temp_path}")
            async with aiofiles.open(temp_path, mode="wb") as f:
                await f.write(audio_data)
            # 校验文件是否写入成功，提前拦截空文件问题
            if not temp_path.exists() or temp_path.stat().st_size == 0:
                logger.error("音频文件写入失败，文件不存在或为空")
                return -1
            # 上传音频文件
            _remote_path = await upload_file(path=str(temp_path))
            logger.debug(f"_remote_path:{_remote_path}")
            if not _remote_path:
                logger.error("未找到文件路径")
                return -1
            file_path = _remote_path
            voice_msg = Message(f"[CQ:record,file={file_path}]")
            # 删除音频文件
            temp_path.unlink()
            return voice_msg
        except Exception as e:
            logger.error(f"在发送语音时出错: {traceback.format_exc()}")
            return -1


@gpt_tts.handle()
async def _(bot: Bot, event: PrivateMessageEvent, arg: Message = CommandArg()):
    # ===== 调试信息 =====
    logger.info(f"=== TTS调试信息 ===")
    logger.info(f"原始arg: {arg}")
    logger.info(f"arg类型: {type(arg)}")

    # 获取用户输入的文本
    text = arg.extract_plain_text().strip()
    logger.info(f"提取后的文本: '{text}'")
    logger.info(f"文本长度: {len(text)}")
    # ============================
    text = arg.extract_plain_text().strip()
    if not text:
        await gpt_tts.finish("请输入文本")

    # 在调用API前打印
    logger.info(f"准备调用API，文本: {text}")

    audio_data, error_msg = await rvc_gpt_tts_data.call_gpt_tts(text)
    if not audio_data:
        await gpt_tts.finish(f"语音合成失败，{error_msg}")

    tts_result = await download_file(audio_data)
    if tts_result==-1:
        await gpt_tts.finish("语音发送失败")
    else:
        await gpt_tts.send(tts_result)










