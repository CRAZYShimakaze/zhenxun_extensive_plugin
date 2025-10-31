from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot
from nonebot.plugin import PluginMetadata
from zhenxun.configs.config import BotConfig
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.utils.enum import PluginType

__plugin_meta__ = PluginMetadata(
    name="昵称检测",
    description="昵称检测",
    usage="""
    群友修改昵称后发言时会检测改动
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.3",
        plugin_type=PluginType.HIDDEN,
    ).to_dict(),
)

nickname_handle = on_notice(priority=1, block=False)


@nickname_handle.handle()
async def _(bot: Bot, event):
    if event.notice_type == "group_card":
        if event.user_id != int(bot.self_id):
            if event.card_old:
                old = event.card_old
            else:
                old = await bot.get_group_member_info(
                    group_id=event.group_id, user_id=event.user_id
                )
                old = old["nickname"]
            if event.card_new:
                new = event.card_new
            else:
                new = await bot.get_group_member_info(
                    group_id=event.group_id, user_id=event.user_id
                )
                new = new["nickname"]
            await nickname_handle.send(
                f"啊嘞?{BotConfig.self_nickname}检测到{old}的群名片改为{new}了呢!"
            )
