import time
from base64 import b64encode

from nonebot import on_command
from nonebot import require
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Bot, MessageSegment

from .aihelper_handles import get_comments_by_id

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session


# 设计上, 每个人的私聊都是保存自己的对话
# 群里只要能够发送信息的人, 都可以保存
# 群聊只有管理员可以还原信息
# 配置文件不可以备份和还原

backup_comments = on_command("ai cm bk")  # 备份
restore_comments = on_command("ai cm rt")  # 还原


@backup_comments.handle()
async def backup_comments_handle(bot: Bot, event: MessageEvent, session: async_scoped_session):
    # 文件按照原样提供
    # 备份的数据就是 json 字符串, 还原只需要原样放回去应该就行
    if isinstance(event, GroupMessageEvent):
        _session_type = "group"
        _res = await get_comments_by_id(sid=event.group_id, session=session)
    else:
        _session_type = "user"
        _res = await get_comments_by_id(sid=event.user_id, session=session)

    if _res is not None and _res.message:
        try:
            encoded = b64encode(_res.message.encode()).decode('utf-8')
        except:
            await backup_comments.finish("failed")
            return
        if _session_type == "group":
            _file = MessageSegment("file", {"file": f"base64://{encoded}",
                                            "name": f"backup-{time.time()}-{event.group_id}.bak"})
        else:
            _file = MessageSegment("file",
                                   {"file": f"base64://{encoded}", "name": f"backup-{time.time()}-{event.user_id}.bak"})
        await backup_comments.finish(_file)
    else:
        await backup_comments.finish("failed")


@restore_comments.handle()
async def restore_comments_handle():
    await backup_comments.finish("请联系数据库维护来还原数据, 这里处于安全考虑不支持自助完成")
