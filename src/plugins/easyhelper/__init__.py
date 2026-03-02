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
    ai cm bk -- 备份历史对话信息
    ai cm rt -- 还原历史对话信息(仅管理员可用)
    ai cf add -- 增加配置文件
    ai cf show -- 列出用户配置
    ai cf delete -- 删除用户配置(暂时不实现)
    ai cf edit -- 编辑用户配置
    ai cf switch -- 切换用户配置
    ai load -- 启动AI选项
    ai save -- 暂停AI选项
    ai remove -- 删除历史记忆
    ai zp mm -- 压缩内存中缓存的对话
    ai zp db -- 压缩服务器中缓存的对话
    yiyan -- 输出一条一言(不是遗言！)
    """
    _help_docs = {
        "ai cm bk":"备份历史对话信息",
        "ai cm rt":"还原历史对话信息(仅管理员可用)",
        "ai cf add":"增加配置文件",
        "ai cf show":"列出用户配置",
        "ai cf delete":"删除用户配置(暂时不实现)",
        "ai cf edit":"编辑用户配置",
        "ai cf switch":"切换用户配置",
        "ai load":"启动AI选项",
        "ai save":"暂停AI选项",
        "ai remove":"删除历史记忆",
        "ai zp mm":"压缩内存中缓存的对话",
        "ai zp db":"压缩服务器中缓存的数据",
        "yiyan":"输出一条一言(不是遗言！)",
    }
    # "命令"-"帮助" 对应
    if args.extract_plain_text() is None or len(args.extract_plain_text().strip()) == 0:
        await request_help.finish(_string)
    else:
        try:
            text = _help_docs[args.extract_plain_text().strip()]
            await request_help.finish(text)
        except KeyError:
            await request_help.finish(_string)
