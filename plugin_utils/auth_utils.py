from functools import wraps

import nonebot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.exception import FinishedException

from zhenxun.models.user_console import UserConsole
from zhenxun.services.log import logger
from zhenxun.utils.enum import GoldHandle

driver = nonebot.get_driver()


async def check_gold(event, coin: int, percent: int = 0):
    user = await UserConsole.get_user(event.user_id)
    user_coin = user.gold
    if percent:
        coin = coin if user_coin * percent // 1000 < coin else user_coin * percent // 1000
    if user_coin < coin:
        if str(event.user_id) == "674015283" or str(event.group_id) in ["217496217", "929291130"]:
            return
        bot = nonebot.get_bot()
        await bot.send_group_msg(
            group_id=event.group_id,
            message=Message(MessageSegment.reply(event.message_id) + f"该功能需要{coin}金币,你的金币不够！(请发送'签到'获取金币.)"),
        )
        raise FinishedException
    else:
        await UserConsole.reduce_gold(event.user_id, coin, GoldHandle.BUY, "auth_utils")


async def spend_gold(user_id: str, coin: int, percent: int = 0):
    if str(user_id) == "2020693819":
        return 0
    user = await UserConsole.get_user(user_id)
    user_coin = user.gold
    if percent:
        coin = coin if user_coin * percent // 1000 < coin else user_coin * percent // 1000
    await UserConsole.reduce_gold(user_id, coin, GoldHandle.BUY, "auth_utils")
    return coin


async def add_gold(user_id: str, coin: int):
    await UserConsole.add_gold(user_id, coin, GoldHandle.GET, "auth_utils")


async def get_gold(user_id: str):
    user = await UserConsole.get_user(user_id)
    user_coin = user.gold
    return user_coin


def gold_cost(coin: int = 10, percent: int = 1):
    """
    coin    - 需要扣多少金币
    percent - 触发概率（0~100）
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # NoneBot 会传进来 bot/event，所以从 args 里提取
            # try:
            # bot: Bot = kwargs.get("bot") or args[0]
            # except:
            bot = nonebot.get_bot()
            # 先从 kwargs 找
            for v in kwargs.values():
                if isinstance(v, MessageEvent) or isinstance(v, GroupMessageEvent):
                    event = v

            # 再从 args 里找
            for v in args:
                if isinstance(v, MessageEvent) or isinstance(v, GroupMessageEvent):
                    event = v

            uid = event.user_id
            user_coin = await get_gold(uid)
            
            # 概率判断
            if percent:
                cost = coin if user_coin * percent // 1000 < coin else user_coin * percent // 1000

            # 金币不足
            if user_coin < cost:
                if (
                    str(event.user_id) == "674015283"
                    or str(event.user_id) == "2020693819"
                    or str(event.group_id)
                    in [
                        "217496217",
                        "929291130",
                    ]
                ):
                    return await func(*args, **kwargs)
                await bot.send(event, MessageSegment.reply(event.message_id) + f"该功能需要{coin}金币,你只有{user_coin}金币！(请发送'签到'获取金币.)")
                return

            # 扣金币
            
            s_coin = await spend_gold(uid, cost, percent)
            try:
                await func(*args, **kwargs)
            except FinishedException:
                await add_gold(uid, s_coin)
                return

            except Exception as e:
                await add_gold(uid, s_coin)
                import traceback

                tb = traceback.extract_tb(e.__traceback__)[-1]
                filename = tb.filename
                lineno = tb.lineno
                return logger.error(f"执行出错！{e}\n文件: {filename}\n行号: {lineno}")
            return
            # return await spend_gold(uid, cost, percent)

        return wrapper

    return decorator
