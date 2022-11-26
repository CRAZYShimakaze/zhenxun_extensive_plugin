from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot
from nonebot.params import Message, CommandArg
from .game import add_game, start_game, call_card, stop_card, get_game_ls, check_game_point
from typing import Dict, List
from models.bag_user import BagUser

__zx_plugin_name__ = "21点"
__plugin_usage__ = """
usage：
    21点游戏,和庄家比谁手中的牌点大，但如果牌点超过21点就爆牌，爆牌就输了这场游戏。
    指令：
        21点+游戏底分:发起21点游戏
        接受+游戏id:加入21点游戏
        叫牌+游戏id:进行叫牌
        停牌+游戏id:进行停牌
        游戏列表:查看21点游戏列表
""".strip()
__plugin_des__ = "21点"
__plugin_cmd__ = [
    "21点/发起21点",
    "接受游戏/接受",
    "叫牌/call",
    "停牌/stop",
    "对战列表",
]
__plugin_type__ = ("群内小游戏", )
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

blackjack = on_command("21点", aliases={"发起21点"}, priority=21, block=True)
accept_blackjack = on_command("接受游戏", aliases={'接受'}, priority=21, block=True)
blackjack_list = on_command("游戏列表", aliases={'列表'}, priority=21, block=True)
call = on_command("叫牌", aliases={'call'}, priority=21, block=True)
stop = on_command("停牌", aliases={'stop'}, priority=21, block=True)


@blackjack.handle()
async def start_blackjack(event: GroupMessageEvent,
                          msg: Message = CommandArg()):
    group_id = event.group_id
    user_id = event.user_id
    point = msg.extract_plain_text().strip()
    player1_name = event.sender.card or event.sender.nickname
    if not point.isdigit():
        await blackjack.finish("请输入正确的金币数！")
    point = int(point)
    user_point = await BagUser.get_gold(user_id, group_id)
    if (user_point - await check_game_point(group_id, user_id, player1_name)) < point:  # type: ignore
        await blackjack.finish("你的金币不够！")
    deck_id = await add_game(group_id, user_id, point, player1_name)
    if deck_id >= 0:
        await blackjack.finish(f"游戏添加成功 游戏id为{deck_id}")
    else:
        await blackjack.finish("出错了QwQ 对战添加失败")


@accept_blackjack.handle()
async def accept(event: GroupMessageEvent, msg: Message = CommandArg()):
    group_id = event.group_id
    user_id = event.user_id
    battle_id = msg.extract_plain_text().strip()
    player2_name = event.sender.card or event.sender.nickname
    user_point = await BagUser.get_gold(user_id, group_id)
    if not battle_id.isdigit():
        await accept_blackjack.finish("请输入正确的游戏id！", at_sender=True)
    words = await start_game(int(battle_id), user_id, player2_name, group_id,
                             user_point)
    await accept_blackjack.finish(words, at_sender=True)


@call.handle()
async def _call(event: GroupMessageEvent, msg: Message = CommandArg()):
    user_id = event.user_id
    deck_id = msg.extract_plain_text().strip()
    if not deck_id.isdigit():
        await call.finish("请输入正确的游戏id！", at_sender=True)
    words = await call_card(int(deck_id), user_id)
    await call.finish(words, at_sender=True)


@stop.handle()
async def _stop(event: GroupMessageEvent, msg: Message = CommandArg()):
    user_id = event.user_id
    deck_id = msg.extract_plain_text().strip()
    if not deck_id.isdigit():
        await call.finish("请输入正确的游戏id！", at_sender=True)
    words = await stop_card(int(deck_id), user_id)
    await stop.finish(words, at_sender=True)


@blackjack_list.handle()
async def accept(event: GroupMessageEvent):
    group_id = event.group_id
    words = await get_game_ls(group_id)
    await blackjack.finish(words)