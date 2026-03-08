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
    用法 get-help [类型]
    类型包含:
    ai-talk : AI 对话相关
    ai-other : 其他 AI 功能
    image: 图片相关
    music: 音乐相关
    other: 其他功能
    """
    _help_docs = {
        "ai-talk": """
    ai cm bk -- 备份历史对话信息
    ai cm rt -- 还原历史对话信息(暂时不实现)
    ai cf add -- 增加配置文件
    ai cf show -- 列出用户配置
    ai cf delete -- 删除用户配置(暂时不实现)
    ai cf edit -- 编辑用户配置(暂时不实现)
    ai cf switch -- 切换用户配置
    ai load -- 启动AI
    ai save -- 暂停AI
    ai remove -- 删除历史记忆
    ai zp mm -- 压缩内存中缓存的对话
    ai zp db -- 压缩数据库中缓存的对话""",
        "ai-other": """
    tts [角色] [内容] -- 语音合成(当前仅支持中文)
    支持的角色: 原神: 希格雯/神里绫华/胡桃/可莉/芙宁娜
    星穹铁道: 阮梅
    明日方舟: 多萝西
    weijin [待检测词] -- 检查违禁词, 返回布尔值
    aidraw [提示词] -- 文生图
    """,
        "image": """
    acg adaptive -- 随机一张非AI二次元人物图片
    acg ai -- 随机一张AI二次元人物图片
    acg r18 -- 黄金肾斗士专享哦
    """,
        "music": """
    163mu [搜索名] [id | null] -- 下载音乐(网易云音乐)
    qqmu [搜索名] [id | null] -- 下载音乐(QQ音乐)
    kuwo [搜索名] [id | null] -- 下载音乐(酷我音乐)
    applemu [搜索名] [id | null] -- 下载音乐(apple音乐)
    """,
        "other": """
    yiyan -- 输出一条一言(不是遗言)
    whois [url] -- 查询 whois 信息
    """
    }
    if args.extract_plain_text() is None or len(args.extract_plain_text().strip()) == 0:
        await request_help.finish(_string)
    else:
        try:
            text = _help_docs[args.extract_plain_text().strip()]
            await request_help.finish(text)
        except KeyError:
            await request_help.finish(_string)
