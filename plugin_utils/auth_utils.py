import nonebot
from nonebot.adapters.onebot.v11 import Message
from nonebot.exception import FinishedException

from zhenxun.models.user_console import UserConsole
from zhenxun.utils.enum import GoldHandle


async def check_gold(event, coin: int, percent: int = 0):
    user = await UserConsole.get_user(event.user_id)
    user_coin = user.gold
    if percent:
        coin = coin if user_coin * percent // 100 < coin else user_coin * percent // 100
    if user_coin < coin:
        if str(event.user_id) == "674015283" or str(event.group_id) in ["217496217", "929291130"]:
            return
        bot = nonebot.get_bot()
        await bot.send_group_msg(
            group_id=event.group_id,
            message=Message(f"该功能需要{coin}金币,你的金币不够！(请发送'签到'获取金币.)"),
        )
        raise FinishedException
    else:
        await UserConsole.reduce_gold(event.user_id, coin, GoldHandle.BUY, "auth_utils")


async def spend_gold(user_id, coin: int):
    await UserConsole.reduce_gold(user_id, coin, GoldHandle.BUY, "auth_utils")


async def add_gold(user_id, coin: int):
    await UserConsole.add_gold(user_id, coin, GoldHandle.GET, "auth_utils")


async def get_gold(user_id):
    user = await UserConsole.get_user(user_id)
    user_coin = user.gold
    return user_coin
