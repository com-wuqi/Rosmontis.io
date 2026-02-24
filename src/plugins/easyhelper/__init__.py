from nonebot import get_plugin_config
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
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

request_help = on_command("get-help")


@request_help.handle()
async def request_help_handle(args: Message = CommandArg()):
    # 帮助
    _string = """
    """
    _help_docs = {}
    # "命令"-"帮助" 对应
    if args.extract_plain_text() is None or len(args.extract_plain_text().strip()) == 0:
        await request_help.finish(_string)
    else:
        try:
            text = _help_docs[args.extract_plain_text().strip()]
            await request_help.finish(text)
        except KeyError:
            await request_help.finish(_string)
