import asyncio
import time
from urllib.parse import quote

import aiofiles
import httpx
from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Message
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from . import config
require("src.plugins.public_apis")
import src.plugins.public_apis as sharedFuncs


_bucket_tts = sharedFuncs.TokenBucket(rate=1 / 40, capacity=1)
_semaphore_file = asyncio.Semaphore(20)


async def built_url_tts(_text: str):
    """处理请求参数并构建url"""
    if not _text:
        return None
    await _bucket_tts.acquire()
    text = _text.strip()
    # 构建请求参数
    encode_text = quote(text, encoding="utf-8", safe="")
    encode_ref_audio_path = quote(config.self_ref_audio_path, encoding="utf-8", safe="")
    encode_prompt_text = quote(config.self_prompt_text, encoding="utf-8", safe="")

    get_request_url = (
        f"{config.self_tts_api_url}?"
        f"text={encode_text}&"
        f"text_lang={config.self_text_lang}&"
        f"ref_audio_path={encode_ref_audio_path}&"
        f"prompt_lang={config.self_prompt_lang}&"
        f"prompt_text={encode_prompt_text}&"
        f"top_k=5&"
        f"top_p=1&"
        f"temperature=1&"
        f"text_split_method=cut0&"
        f"batch_size=1&"
        f"batch_threshold=0.75&"
        f"split_bucket=true&"
        f"speed_factor=1&"
        f"fragment_interval=0.3&"
        f"seed=-1&"
        f"media_type=wav&"
        f"streaming_mode=false&"
        f"parallel_infer=true&"
        f"repetition_penalty=1.35&"
        f"sample_steps=16&"
        f"super_sampling=false"
    )

    logger.debug(f"API地址: {get_request_url}")
    logger.debug(f"请求文本: {text}")
    return get_request_url


async def download_tts_file(get_request_url: str):
    """获取url并下载音频同时进行文件管理"""
    try:
        async with _semaphore_file:
            # 1. 创建临时文件路径
            temp_path = store.get_plugin_cache_file(f"rvc_gpt_tts-{time.time()}.wav")

            # 2. 下载音频 (流式写入)
            async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=120) as client:
                async with client.stream("GET", get_request_url) as response:
                    response.raise_for_status()
                    # 校验 Content-Length 如果有的话，防止空响
                    async with aiofiles.open(temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=262144):
                            await f.write(chunk)

            # 3. 验证文件
            if not temp_path.exists():
                return None, "文件下载失败：未找到文件"

            stat = temp_path.stat()
            if stat.st_size == 0:
                return None, "文件下载失败：内容为空"

            # 4. 上传文件
            try:
                remote_path = await sharedFuncs.upload_file(path=str(temp_path))
            except Exception as e:
                logger.exception("文件上传失败")
                return None, "文件上传失败"

            if not remote_path:
                return None, "文件上传失败"

            # 5. 清理临时文件
            try:
                temp_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            return remote_path, None

        # 4. 统一的异常处理
    except httpx.HTTPStatusError as e:
        msg = f"API 返回错误: {e.response.status_code}"
        logger.error(msg)
        return None, msg
    except (httpx.RequestError, Exception) as e:  # 合并处理所有网络及其他异常
        logger.exception(f"下载过程异常: {e}")
        # 异常时尝试清理，避免残留
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        return None, f"请求异常: {str(e)}"