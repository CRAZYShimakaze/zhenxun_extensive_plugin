from typing import Tuple

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, GROUP
from nonebot.params import RegexGroup

from models.bag_user import BagUser
from utils.utils import get_message_at

__zx_plugin_name__ = "金币转账"
__plugin_usage__ = """
usage：
转账 [金币数] @CRAZYSHIMAKAZE
""".strip()

__plugin_des__ = "金币转账"
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"

__plugin_settings__ = {"level": 5, "default_status": True, "limit_superuser": False, "cmd": ["转账"], }

trans = on_regex(r'转账(\d+)', permission=GROUP, priority=5, block=True)


@trans.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Tuple[str, ...] = RegexGroup()):
    src_user = event.user_id
    tar_user = get_message_at(event.json())[0]
    coin = int(args[0].strip())
    print(args[0], args)
    user_coin = await BagUser.get_gold(event.user_id, event.group_id)
    if user_coin <= coin:
        await trans.send(f'你拥有{user_coin}金币,不足转账数目！', at_sender=True)
    else:
        await BagUser.spend_gold(src_user, event.group_id, coin)
        await BagUser.add_gold(tar_user, event.group_id, coin)
        await trans.send(f'转账成功！', at_sender=True)
