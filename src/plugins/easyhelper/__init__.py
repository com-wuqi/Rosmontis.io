from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="easyHelper",
    description="[sign]gethelp 获取帮助",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

# TODO: 暂时不上传, 等待其他插件完工才能补全帮助文件