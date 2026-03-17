import asyncio
import time
from urllib.parse import quote

import httpx
from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Message
import nonebot_plugin_localstore as store

from . import config
require("src.plugins.public_apis")
import src.plugins.public_apis as sharedFuncs


_bucket_tts = sharedFuncs.TokenBucket(rate=1 / 40, capacity=1)
_semaphore_file = asyncio.Semaphore(60)

# 导入配置
tts_api_url = config.gpt_tts_api_url
ref_audio_path = config.gpt_ref_audio_path
prompt_text = config.gpt_prompt_text
prompt_lang = config.gpt_prompt_lang
text_lang = config.gpt_text_lang


if not tts_api_url:
    logger.error("未检测到url")
    raise ValueError("tts_api_url 未配置!")
if not ref_audio_path:
    logger.error("未检测到参考音频路径")
    raise ValueError("ref_audio_path 未配置!")
if not prompt_text:
    logger.error("未检测到参考音频文本")
    raise ValueError("prompt_text 未配置!")


async def built_gpt_tts(_text: str):
    """处理请求参数并构建url"""
    if not _text:
        return None
    await _bucket_tts.acquire()
    text = _text.strip()
    # 构建请求参数
    encode_text = quote(text, encoding="utf-8", safe="")
    encode_ref_audio_path = quote(ref_audio_path, encoding="utf-8", safe="")
    encode_prompt_text = quote(prompt_text, encoding="utf-8", safe="")

    get_request_url = (
        f"{tts_api_url}?"
        f"text={encode_text}&"
        f"text_lang={text_lang}&"
        f"ref_audio_path={encode_ref_audio_path}&"
        f"prompt_lang={prompt_lang}&"
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
            # 1. 创建临时文件
            temp_path = store.get_plugin_cache_file(f"rvc_gpt_tts-{time.time()}.wav")

            # 2. 下载音频
            async with httpx.AsyncClient(timeout=60.0, max_redirects=5) as client:
                try:
                    async with client.stream("GET", get_request_url) as response:
                        response.raise_for_status()

                        # 确保父目录存在（store 可能不会自动创建）
                        temp_path.parent.mkdir(parents=True, exist_ok=True)

                        with open(temp_path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                if chunk:  # 防止空块
                                    f.write(chunk)

                except httpx.HTTPStatusError as e:
                    return None, f"API返回错误状态: {e.response.status_code}"
                except httpx.RequestError as e:
                    return None, f"网络请求错误: {str(e)}"

            # 3. 验证文件
            if not temp_path.exists():
                return None, "文件下载失败：未找到文件"

            file_size = temp_path.stat().st_size
            if file_size == 0:
                temp_path.unlink(missing_ok=True)  # 清理空文件
                return None, "文件下载失败：内容为空"

            # 4. 上传文件
            if not sharedFuncs:
                return None, "共享模块未加载"

            remote_path = await sharedFuncs.upload_file(path=str(temp_path))

            if not remote_path:
                return None, "文件上传失败"

            # 5. 清理临时文件（放在最后，无论成功失败都清理）
            try:
                temp_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            return remote_path, None

    except httpx.ConnectTimeout as e:
        error_msg = f"连接API超时: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

    except httpx.TimeoutException as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

    except httpx.ConnectError as e:
        error_msg = f"无法连接到API服务器: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

    except Exception as e:
        import traceback
        error_msg = f"请求异常: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
