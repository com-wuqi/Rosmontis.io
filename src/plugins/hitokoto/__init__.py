from nonebot import get_plugin_config,on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, Message, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.log import logger
from nonebot import require
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
import asyncio
from .config import Config
from .getHitokoto import get_a_yiyan
from random import choice
# from nonebot import get_driver


__plugin_meta__ = PluginMetadata(
    name="hitokoto",
    description="一个简单的一言插件",
    usage="[sign]yiyan 1 # 输出一条一言(1可以省略)",
    config=Config,
)

# _superusers = get_driver().config.superusers

config = get_plugin_config(Config)
_is_debug = config.is_debug
_is_enable = config.is_enable and (config.is_allow_user or config.is_allow_group)
_is_enable_blacklist = config.is_enable_blacklist and (len(config.blacklist_groups)>0 or len(config.blacklist_users)>0)
_is_enable_whitelist = config.is_enable_whitelist and (len(config.whitelist_groups)>0 or len(config.whitelist_users)>0)

if _is_enable_whitelist and not _is_enable_blacklist:
    _control_type = "whitelist"
elif _is_enable_blacklist and not _is_enable_whitelist:
    _control_type = "blacklist"
elif not _is_enable_whitelist and not _is_enable_blacklist:
    _control_type = "null"
    logger.warning("_control_type is null, be careful")
else:
    raise RuntimeError("hitokoto config error")
_control_list_group = config.whitelist_groups if _is_enable_whitelist else config.blacklist_groups
_control_list_user = config.whitelist_users if _is_enable_whitelist else config.blacklist_users

_cache = [] # 缓存列表
_cache_lock = asyncio.Lock()
_cache_length_limit = config.cache_length_limit
_cache_timeout = config.cache_timeout


@scheduler.scheduled_job("interval", seconds=_cache_timeout,id="handle_yiyan_cache")
async def handle_yiyan_cache():
    global _cache
    if _is_debug:
        logger.debug("_cache now is : {}".format(_cache))
    async with _cache_lock:
        _new = get_a_yiyan()
        if len(_cache)<_cache_length_limit:
            _cache.append(_new)
        else:
            _cache = _cache[:_cache_length_limit]

get_yiyan = on_command("yiyan", priority=5)

@get_yiyan.handle()
async def handle_yiyan(bot: Bot,event: MessageEvent, args: Message = CommandArg()):
    if not _is_enable:
        await get_yiyan.finish("is disabled")
        return
    _message_type = "Group" if isinstance(event, GroupMessageEvent) else "User"
    if isinstance(event, PrivateMessageEvent) and not config.is_allow_user:
        return
    if isinstance(event, GroupMessageEvent) and not config.is_allow_group:
        return
    _uid = event.user_id if _message_type == "User" else event.group_id
    if _control_type == "blacklist":
        if (_uid in _control_list_user) or (_uid in _control_list_group):
            return
    elif _control_type == "whitelist":
        if (_uid not in _control_list_user) and (_uid not in _control_list_group):
            return
    # 过滤逻辑

    if _is_debug:
        logger.debug("handle_yiyan CommandArg(): {}, user_id is : {}".format(args,event.user_id))
        # logger.debug("handle_yiyan CommandArg(): {}, group_id is : {}".format(args, event.group_id))

    _sentences = []
    try:
        _length = int(args.extract_plain_text())
    except ValueError:
        _length = 1
    if _length > 1:
        await get_yiyan.finish("yiyan_lenth: {} is not support now !".format(_length))
    async with _cache_lock:
        global _cache

        if len(_cache)<_cache_length_limit:
            _sentence = await get_a_yiyan()
            if _sentence != "":
                _cache.append(_sentence)
            else:
                _sentence = choice(_cache)
        else:
            _sentence = choice(_cache)

        _sentences.append(_sentence)

    await get_yiyan.finish("yiyan: {}".format(_sentences))