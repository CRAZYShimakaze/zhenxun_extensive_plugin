from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.exception import FinishedException

from models.bag_user import BagUser


async def check_gold(event, coin: int, percent: int = 0):
    if isinstance(event, GroupMessageEvent):
        user_coin = await BagUser.get_gold(event.user_id, event.group_id)
        if percent:
            coin = coin if user_coin * percent // 100 < coin else user_coin * percent // 100
        if user_coin < coin:
            bot = nonebot.get_bot()
            await bot.send_group_msg(group_id=event.group_id, message=Message(
                f"该功能需要{coin}金币,你的金币不够！(请发送'签到'获取金币.)"))
            raise FinishedException
        else:
            await BagUser.spend_gold(event.user_id, event.group_id, coin)
