from typing import Tuple

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, Bot, GroupMessageEvent
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.models.user_console import UserConsole
from zhenxun.utils.enum import GoldHandle, PluginType

from ..genshin_role_info.utils.json_utils import get_message_at

__plugin_meta__ = PluginMetadata(
    name="金币转账",
    description="金币转账",
    usage="""
    转账 [金币数] @CRAZYSHIMAKAZE
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.2",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)


trans = on_regex(r"转账\s*(\d+)", permission=GROUP, priority=5, block=True)


@trans.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Tuple[str, ...] = RegexGroup()):
    src_user = event.user_id
    tar_user = get_message_at(event.json())[0]
    coin = int(args[0].strip())
    print(args[0], args)
    user = await UserConsole.get_user(src_user)
    user_coin = user.gold
    if user_coin <= coin:
        await trans.send(f"你拥有{user_coin}金币,不足转账数目！", at_sender=True)
    else:
        await UserConsole.reduce_gold(src_user, coin, GoldHandle.BUY, "gold_trans")
        await UserConsole.add_gold(tar_user, coin, GoldHandle.BUY, "gold_trans")
        await trans.send("转账成功！", at_sender=True)
