from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="yaohud",
    description="妖狐数据开放API接口, 部分实现",
    usage="",
    config=Config,
)
"""
我们使用如下(分类, 从官网翻译), 来分类插件实现
AI
Image
Music
Info
Video
Tools
Data
Bilibili
Others
"""

_config = get_plugin_config(Config)
config = _config.yaohud

if config.is_enable:
    # 加载插件
    from .yaohud_image import *

    pass
