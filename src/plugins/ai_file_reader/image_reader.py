import asyncio
import base64
import functools
import mimetypes
import os
import time
import traceback
from pathlib import Path

from PIL import Image
from nonebot import require
from nonebot.log import logger
from openai import AsyncOpenAI

from . import config

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
import src.plugins.public_apis as public_api

_token_bucket = public_api.TokenBucket(rate=config.image_ai_rate_limit, capacity=config.image_ai_rate_limit)

_IMAGE_SUPPORTED_EXT = {
    ".png", ".jpg", ".jpeg",
    ".webp", ".gif"
}

def is_supported_image(s: str) -> bool:
    """
    判断文件后缀名是否是 openai 支持的图片
    :param s: 图片名称，包含后缀
    :return: bool, 是否匹配
    """
    return Path(s).suffix.lower() in _IMAGE_SUPPORTED_EXT


def compress_image(
        input_path: str,
        output_path: str,
        quality: int = config.image_zip_quality,  # 用于有损格式 (JPEG/WebP)
        lossless: bool = config.image_zip_lossless,  # PNG/WebP 无损模式
        max_width: int = config.image_zip_max_width,  # 限制最大宽度（等比缩放）
        max_height: int = config.image_zip_max_height,  # 限制最大高度（等比缩放）
):
    """
    压缩图片
    """
    img = Image.open(input_path)
    if max_width or max_height:
        w, h = img.size

        if max_width and w > max_width:
            ratio = max_width / w
            h = int(h * ratio)
            w = max_width
        if max_height and h > max_height:
            ratio = max_height / h
            w = int(w * ratio)
            h = max_height
        img = img.resize((w, h), Image.Resampling.LANCZOS)
    ext = os.path.splitext(output_path)[1].lower()
    if not ext:
        ext = os.path.splitext(input_path)[1].lower()
        output_path += ext  # 根据input推断
    if ext in ('.jpg', '.jpeg'):
        img = img.convert('RGB')  # JPEG 不能有透明通道
        img.save(output_path, format='JPEG', quality=quality, optimize=True)
    elif ext == '.png':
        # PNG 压缩：optimize 会尝试更好的编码，也可用 quantize 减少颜色
        if not lossless and img.mode in ('RGBA', 'RGB'):
            # 将有透明通道的图片减少颜色至 256 色（仍保留透明）
            img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            # quantize 后模式变为 P，如有透明需保存 transparency 信息
            img.save(output_path, format='PNG', optimize=True)
        else:
            img.save(output_path, format='PNG', optimize=True)
    elif ext == '.webp':
        img.save(output_path, format='WEBP', quality=quality, lossless=lossless)
    elif ext == '.gif':
        # GIF 不支持 quality 参数；尽量减小调色板
        img = img.convert('P', palette=Image.Palette.ADAPTIVE)
        img.save(output_path, format='GIF', optimize=True)
    else:
        # 其他格式用默认保存
        img.save(output_path, optimize=True)

    # debug
    original_size = os.path.getsize(input_path)
    compressed_size = os.path.getsize(output_path)
    logger.debug(f"compress_image path: {input_path} -> {output_path}")
    logger.debug(f"compress_image success：{original_size // 1024}KB -> {compressed_size // 1024}KB ")


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def encode_image_async(image_path):
    loop = asyncio.get_event_loop()
    func = functools.partial(encode_image, image_path)
    result = await loop.run_in_executor(public_api.global_progress_pool, func)
    return result


async def compress_image_async(input_path, output_path, **kwargs):
    loop = asyncio.get_running_loop()
    func = functools.partial(compress_image, input_path, output_path, **kwargs)
    result = await loop.run_in_executor(public_api.global_progress_pool, func)
    return result


async def read_image(file_name: str, file_url: str) -> str | None:
    await _token_bucket.acquire()
    image_path = store.get_plugin_cache_file(f"{time.time()}-{file_name}")
    compressed_image_path = store.get_plugin_cache_file(f"compressed-{time.time()}-{file_name}")
    _return = None
    mime_type, _ = mimetypes.guess_type(file_name)
    try:
        if mime_type is None:
            raise RuntimeError("guess type error")
        # 图片下载，压缩
        _try_download = await public_api.download_file(file_url, str(image_path))
        if _try_download != 0:
            raise RuntimeError("download failed")
        await asyncio.gather(compress_image_async(input_path=str(image_path), output_path=str(compressed_image_path)))
        if not os.path.exists(str(compressed_image_path)):
            raise RuntimeError("compress image failed")
        base64_image = await encode_image_async(str(compressed_image_path))
        client = AsyncOpenAI(base_url=config.image_ai_api_url, api_key=config.image_ai_api_key,
                             timeout=config.image_ai_api_timeout)
        chat_completion = await client.chat.completions.create(
            model=config.image_ai_model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请准确，详细，客观的描述图片里的所有内容"},
                        {"type": "text", "text": "要求：直接输出最终描述结果，不要输出任何思考过程或解释。"},
                        {"type": "text", "text": "输出格式：纯文本，无需分段标题。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}",
                                "detail": "auto"
                            }
                        }
                    ]

                }
            ],
            temperature=1.0,
        )
        _return = chat_completion.choices[0].message
        if not _return or not _return.content:
            logger.warning(
                f"返回空内容，"
                f"finish_reason: {getattr(chat_completion.choices[0], 'finish_reason', 'unknown')} | "
                f"完整响应: {chat_completion.model_dump()}")
            raise RuntimeError("模型未返回有效描述内容")
        _msg = _return.content
        logger.debug(f"read_image: {_msg}")
        return _msg

    except Exception as e:
        logger.error(e)
        traceback.print_exc()
    finally:
        image_path.unlink(missing_ok=True)
        compressed_image_path.unlink(missing_ok=True)
    return None
