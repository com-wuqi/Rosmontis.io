import asyncio
import functools
import os
import re
import time

from PIL import Image
from nonebot import require
from nonebot.log import logger

from . import config

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

require("src.plugins.public_apis")
from src.plugins.public_apis import TokenBucket, download_file

_token_bucket = TokenBucket(rate=config.image_ai_rate_limit, capacity=config.image_ai_rate_limit)

def is_supported_image(s: str) -> bool:
    """
    判断文件后缀名是否是 openai 支持的图片
    :param s: 图片名称，包含后缀
    :return: bool, 是否匹配
    """
    pattern = r"\.(png|jpe?g|webp|gif)(\?.*)?$"
    return bool(re.search(pattern, s.strip(), re.IGNORECASE))


def compress_image(
        input_path: str,
        output_path: str,
        quality: int = 85,  # 用于有损格式 (JPEG/WebP)
        lossless: bool = False,  # PNG/WebP 无损模式
        max_width: int = None,  # 限制最大宽度（等比缩放）
        max_height: int = None,
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


async def compress_image_async(input_path, output_path, **kwargs):
    loop = asyncio.get_running_loop()
    func = functools.partial(compress_image, input_path, output_path, **kwargs)
    result = await loop.run_in_executor(None, func)
    return result


async def read_image(file_name: str, file_url: str) -> str | None:
    await _token_bucket.acquire()
    image_path = store.get_plugin_cache_file(f"{time.time()}-{file_name}")
    compressed_image_path = store.get_plugin_cache_file(f"compressed-{time.time()}-{file_name}")
    _return = None
    try:
        _try_download = await download_file(file_url, str(image_path))
        assert _try_download == 0, "download failed"
        await asyncio.gather(compress_image_async(input_path=str(image_path), output_path=str(compressed_image_path)))
    except Exception as e:
        logger.error(e)
    finally:
        image_path.unlink(missing_ok=True)
        compressed_image_path.unlink(missing_ok=True)

    return _return
