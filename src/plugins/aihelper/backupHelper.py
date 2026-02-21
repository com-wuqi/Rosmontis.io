import time
from base64 import b64encode

from nonebot import on_command
from nonebot import require
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Bot

from .aihelper_handles import get_comments_by_id

require("nonebot_plugin_orm")
require("nonebot_plugin_localstore")
from nonebot_plugin_orm import async_scoped_session
import nonebot_plugin_localstore as store

# 设计上, 每个人的私聊都是保存自己的对话
# 群里只要能够发送信息的人, 都可以保存
# 群聊只有管理员可以还愿信息
# 配置文件不可以备份和还原

backup_comments = on_command("ai cm bk")  # 备份
restore_comments = on_command("ai cm rt")  # 还原


@backup_comments.handle()
async def backup_comments_handle(bot: Bot, event: MessageEvent, session: async_scoped_session):
    # 文件按照原样提供
    # 备份的数据就是 json 字符串, 还原只需要原样放回去应该就行
    if isinstance(event, GroupMessageEvent):
        _msg_type = "group"
        _res = await get_comments_by_id(sid=event.group_id, session=session)
    else:
        _msg_type = "private"
        _res = await get_comments_by_id(sid=event.user_id, session=session)

    if _res is not None and _res.message:
        try:
            encoded = b64encode(_res.message.encode()).decode('utf-8')
        except:
            await backup_comments.finish("failed")
            return
        _file_store = store.get_plugin_cache_file(f"aiComments-backup-{event.user_id}-{time.time()}.bak")
        _file_store.write_text(encoded, encoding="utf-8")
        try:
            if _msg_type == "group":
                await bot.call_api(
                    "upload_group_file",
                    group_id=event.group_id,
                    file=f"base64://{_file_store.read_text()}",
                    name=f"aiComments-backup-{event.group_id}-{time.time()}.bak"
                )
            else:
                await bot.call_api(
                    "upload_private_file",
                    user_id=event.user_id,
                    file=f"base64://{_file_store.read_text()}",
                    name=f"aiComments-backup-{event.user_id}-{time.time()}.bak"
                )
        except Exception as e:
            await backup_comments.send("failed: {}".format(e))
        _file_store.unlink()
        # 删除连接
        await backup_comments.finish("success")
    else:
        await backup_comments.finish("not found")


@restore_comments.handle()
async def restore_comments_handle():
    await backup_comments.finish("请联系数据库维护来还原数据, 这里处于安全考虑不支持自助完成")
