from nonebot import on_notice
from nonebot.adapters.onebot.v11 import (
    Bot
)

__zx_plugin_name__ = "昵称检测 [Hidden]"
__plugin_version__ = 0.1
__plugin_author__ = 'CRAZYSHIMAKAZE'

from configs.config import NICKNAME

nickname_handle = on_notice(priority=1, block=False)


@nickname_handle.handle()
async def _(bot: Bot, event):
    if event.notice_type == 'group_card':
        if event.user_id != int(bot.self_id):
            if event.card_old:
                old = event.card_old
            else:
                old = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
                old = old["nickname"]
            if event.card_new:
                new = event.card_new
            else:
                new = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
                new = new["nickname"]
            await nickname_handle.send(f'啊嘞?{NICKNAME}检测到{old}的群名片改为{new}了呢!')
