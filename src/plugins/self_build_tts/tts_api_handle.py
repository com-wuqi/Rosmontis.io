import asyncio
import time
from urllib.parse import quote

import aiofiles
import httpx
from nonebot import logger, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from . import config
require("src.plugins.public_apis")
import src.plugins.public_apis as public_apis
from gradio_client import Client, handle_file

_bucket_gpt_sovits = public_apis.TokenBucket(rate=1 / 40, capacity=1)
_bucket_qwen3_customvoice = public_apis.TokenBucket(rate=1 / 40, capacity=1)
_bucket_qwen3_voice_design = public_apis.TokenBucket(rate=1 / 40, capacity=1)
_bucket_qwen3_base = public_apis.TokenBucket(rate=1 / 40, capacity=1)
_bucket_qwen3_base_downloadfile = public_apis.TokenBucket(rate=1, capacity=20)
_bucket_qwen3_base_gen = public_apis.TokenBucket(rate=1, capacity=20)

async def built_gpt_sovits_url_tts(_text: str):
    """处理请求参数并构建url"""
    if not _text:
        return None
    await _bucket_gpt_sovits.acquire()
    text = _text.strip()
    # 构建请求参数
    encode_text = quote(text, encoding="utf-8", safe="")
    encode_ref_audio_path = quote(config.gpt_sovits_ref_audio_path, encoding="utf-8", safe="")
    encode_prompt_text = quote(config.gpt_sovits_prompt_text, encoding="utf-8", safe="")

    get_request_url = (
        f"{config.gpt_sovits_tts_api_url}?"
        f"text={encode_text}&"
        f"text_lang={config.gpt_sovits_text_lang}&"
        f"ref_audio_path={encode_ref_audio_path}&"
        f"prompt_lang={config.gpt_sovits_prompt_lang}&"
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

    logger.debug(f"gpt_sovits url: {get_request_url}")
    logger.debug(f"gpt_sovits text: {text}")
    return get_request_url


async def download_gpt_sovits_tts_file(get_request_url: str):
    """获取url并下载音频同时进行文件管理"""
    temp_path = store.get_plugin_cache_file(f"rvc_gpt_tts-{time.time()}.wav")
    try:

        async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=120) as client:
            async with client.stream("GET", get_request_url) as response:
                response.raise_for_status()
                # 校验 Content-Length 如果有的话，防止空响
                async with aiofiles.open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=262144):
                        await f.write(chunk)

        if not temp_path.exists():
            return None, "文件下载失败：未找到文件"

        stat = temp_path.stat()
        if stat.st_size == 0:
            return None, "文件下载失败：内容为空"

        try:
            remote_path = await public_apis.upload_file(path=str(temp_path))
        except Exception as e:
            logger.exception("文件上传失败")
            return None, "文件上传失败"

        if not remote_path:
            return None, "文件上传失败"

        try:
            temp_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

        return remote_path, None

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


async def wait_for_job(job):
    """
    在线程池中等待 job.result()，实现异步非阻塞等待
    """
    result = await asyncio.to_thread(job.result)  # 将阻塞调用放到线程中
    return result


async def qwen3_tts_customvoice(text: str):
    await _bucket_qwen3_customvoice.acquire()

    client = Client(config.qwen3_tts_customvoice_api_url, verbose=False)
    job = client.submit(
        text=text,
        lang_disp=config.qwen3_tts_customvoice_lang_disp,
        spk_disp=config.qwen3_tts_customvoice_spk_disp,
        instruct=config.qwen3_tts_customvoice_instruct,
        api_name="/run_instruct"
    )
    logger.debug(f"qwen3_tts_customvoice job started")
    file_path, _ = await wait_for_job(job)
    logger.debug(f"qwen3_tts_customvoice local {file_path}")
    _remote_path = await public_apis.upload_file(file_path)
    logger.debug(f"qwen3_tts_customvoice remote {_remote_path}")
    return _remote_path


async def qwen3_tts_voice_design(text: str):
    await _bucket_qwen3_voice_design.acquire()
    client = Client(config.qwen3_tts_voice_design_api_url, verbose=False)
    job = client.submit(
        text=text,
        lang_disp=config.qwen3_tts_voice_design_lang_disp,
        design=config.qwen3_tts_voice_design_design,
        api_name="/run_voice_design",
    )
    logger.debug(f"qwen3_tts_voice_design job started")
    file_path, _ = await wait_for_job(job)
    logger.debug(f"qwen3_tts_voice_design local {file_path}")
    _remote_path = await public_apis.upload_file(file_path)
    logger.debug(f"qwen3_tts_voice_design remote {_remote_path}")
    return _remote_path


async def qwen3_tts_base_save_prompt(ref_txt: str, ref_aud: str):
    await _bucket_qwen3_base.acquire()
    client = Client(config.qwen3_tts_base_api_url, verbose=False)
    job = client.submit(
        ref_aud=handle_file(ref_aud),
        ref_txt=ref_txt,
        use_xvec=config.qwen3_tts_base_use_xvec,
        api_name="/save_prompt"
    )
    logger.debug(f"qwen3_tts_base_save_prompt job started")
    file_path, _ = await wait_for_job(job)
    logger.debug(f"qwen3_tts_base_save_prompt local {file_path}")
    _remote_path = await public_apis.upload_file(file_path)
    logger.debug(f"qwen3_tts_base_save_prompt remote {_remote_path}")
    return _remote_path


async def qwen3_tts_base_gen(file_path: str, text: str):
    await _bucket_qwen3_base_gen.acquire()
    client = Client(config.qwen3_tts_base_api_url, verbose=False)
    job = client.submit(
        file_obj=handle_file(file_path),
        text=text,
        lang_disp=config.qwen3_tts_base_lang_disp,
        api_name="/load_prompt_and_gen",
    )
    logger.debug(f"qwen3_tts_base_gen job started")
    file_path, _ = await wait_for_job(job)
    logger.debug(f"qwen3_tts_base_gen local {file_path}")
    _remote_path = await public_apis.upload_file(file_path)
    logger.debug(f"qwen3_tts_base_gen remote {_remote_path}")
    return _remote_path


async def get_private_file_from_url(url: str, file_name: str, user_id: int):
    await _bucket_qwen3_base_downloadfile.acquire()
    temp_path = store.get_plugin_cache_file(f"{user_id}_{time.time()}_{file_name}")
    _header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",  # 包含所有现代压缩算法
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(http2=True, headers=_header, follow_redirects=True, timeout=120) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                async with aiofiles.open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=262144):
                        await f.write(chunk)
        return str(temp_path)
    except httpx.HTTPStatusError as e:
        logger.warning("get_private_file_from_url httpx.HTTPStatusError: {}".format(e))
        return ""
    except Exception as e:
        logger.warning("get_private_file_from_url Exception: {}".format(e))
        return ""
