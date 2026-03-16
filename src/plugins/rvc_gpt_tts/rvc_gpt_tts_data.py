import asyncio
from urllib.parse import quote

import httpx
from nonebot import logger
from . import config
from ..public_apis import TokenBucket

_bucket_tts = TokenBucket(rate=1 / 40, capacity=1)
_semaphore_file = asyncio.Semaphore(60)

# 导入配置
tts_api_url = config.tts_api_url
ref_audio_path = config.ref_audio_path
prompt_text = config.prompt_text
prompt_lang = config.prompt_lang
text_lang = config.text_lang


if not tts_api_url:
    logger.error("未检测到url")
    raise ValueError("tts_api_url 未配置!")
if not ref_audio_path:
    logger.error("未检测到参考音频路径")
    raise ValueError("ref_audio_path 未配置!")
if not prompt_text:
    logger.error("未检测到参考音频文本")
    raise ValueError("prompt_text 未配置!")

async def call_gpt_tts(_text: str):
    if not _text:
        return None, "文本为空"
    await _bucket_tts.acquire()
    text = _text
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

    logger.info(f"API地址: {get_request_url}")
    logger.info(f"请求文本: {text}")

    try:
        async with _semaphore_file:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    get_request_url,
                    timeout=30
                )
                logger.info(f"API响应状态码: {response.status_code}")

                if response.status_code != 200:
                    error_msg = f"API返回错误码: {response.status_code}, 响应内容: {response.text}"
                    logger.error(error_msg)
                    return None, error_msg

                if not response.content:
                    error_msg = "API返回空内容"
                    logger.error(error_msg)
                    return None, error_msg

                logger.success(f"成功获取返回音频，大小为 {len(response.content)} 字节")
                return response.content, None

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
        logger.error(f"完整的错误堆栈:\n{traceback.format_exc()}")
        return None, error_msg