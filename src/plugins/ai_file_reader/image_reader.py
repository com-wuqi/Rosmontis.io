import re

from nonebot import require

require("src.plugins.public_apis")


# from src.plugins.public_apis import TokenBucket

def is_supported_image(s: str) -> bool:
    """
    判断文件后缀名是否是 openai 支持的图片
    :param s: 图片名称，包含后缀，不允许路径
    :return: bool, 是否匹配
    """
    pattern = r"\.(png|jpe?g|webp|gif)(\?.*)?$"
    return bool(re.fullmatch(pattern, s.strip(), re.IGNORECASE))


async def read_image(file_name: str, file_id: str | None = None, file_url: str | None = None) -> str:
    pass
