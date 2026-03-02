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
    yiyan -- 输出一条一言(不是遗言)
    tts -- 语音合成(当前仅支持中文)
    aidraw -- 文生图
    acg adaptive -- 生成一张非AI二次元人物图片
    acg ai -- 绘制一张AI二次元人物图片
    acg r18 -- 黄金肾斗士专享哦
    163mu -- 播放音乐(网易云音乐)
    qqmu -- 播放音乐(QQ音乐)
    kuwo -- 播放音乐(酷我音乐)
    """
    _help_docs = {
        "ai":"ai cm bk:备份历史对话信息\n"
             "ai cm rt:还原历史对话信息(仅管理员可用)\n"
             "ai cf add:增加配置文件\n"
             "ai cf show:列出用户配置\n"
             "ai cf delete:删除用户配置(暂时不实现)\n"
             "ai cf edit:编辑用户配置\n"
             "ai cf switch:切换用户配置\n"
             "ai load:启动AI选项\n"
             "ai save:暂停AI选项\n"
             "ai remove:删除历史记忆\n"
             "ai zp mm:压缩内存中缓存的对话\n"
             "ai zp db:压缩服务器中缓存的对话",
        "yiyan":"输出一条一言(不是遗言)",
        "tts":"语音合成(当前仅支持中文)",
        "aidraw":"文生图",
        "acg adaptive":"生成一张非AI二次元人物图片",
        "acg ai":"绘制一张AI二次元人物图片",
        "acg r18":"黄金肾斗士专享哦",
        "163mu":"用法:163mu [搜索名称] [选择的id | null],播放音乐(网易云音乐)",
        "qqmu":"用法:qqmu [搜索名称] [选择的id | null],播放音乐(QQ音乐)",
        "kuwo":"用法:kuwo [搜索名称] [选择的id | null],播放音乐(酷我音乐)",
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
