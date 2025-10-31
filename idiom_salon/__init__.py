import asyncio
from asyncio import TimerHandle
import os
import time
from typing import Dict

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from pypinyin import lazy_pinyin

from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import PluginType

from ..plugin_utils.auth_utils import add_gold, get_gold, spend_gold

__plugin_meta__ = PluginMetadata(
    name="成语接龙",
    description="成语接龙",
    usage="""
    接尾字同音字开头的成语(之前说过的不能再说),1v1 solo,不是你死就是我活!
    指令：
        成语接龙 [成语] [金币数]: 开始游戏,下注金币
        接 [成语]：接龙成语
        接龙结算: 认输,或超时强行结算
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.3",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)

vs_player = {}
dati_time = 40
timers: dict[str, TimerHandle] = {}

start = on_command("成语接龙", permission=GROUP, priority=5, block=True)

submit = on_command("接", permission=GROUP, priority=5, block=True)

stop_game = on_command("接龙结算", permission=GROUP, priority=5, block=True)
# 可切换为使用api验证成语合法性
# check_url = 'https://api.vore.top/api/idiom?q={}'
dirname, _ = os.path.split(os.path.abspath(__file__))
work_dir = os.getcwd()
rel_path = dirname.replace(work_dir + "/", "")
idiom_data = open(f"{rel_path}/idiom.txt", encoding="utf-8")
idiom_list = idiom_data.read()


@start.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State, arg: Message = CommandArg()):
    global vs_player
    try:
        if vs_player[event.group_id]["player1"] == event.user_id or vs_player[event.group_id]["player2"] == event.user_id:
            await start.finish("你现在已经在游戏中了!\n认真一点啊喂...", at_sender=True)
        elif (vs_player[event.group_id]["player1"] and vs_player[event.group_id]["player2"]) and time.time() - vs_player[event.group_id]["time"] <= dati_time:
            await start.finish("对局正在进行\n请稍后再开始下一轮...")
        elif vs_player[event.group_id]["player1"] and 0 == vs_player[event.group_id]["player2"]:
            await start.send("上局流局！新开局！\n")
            vs_player = {}
        elif (vs_player[event.group_id]["player1"] and vs_player[event.group_id]["player2"]) and time.time() - vs_player[event.group_id]["time"] >= dati_time:
            winner = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2"]
            loser = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2"]
            winner_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2_name"]
            loser_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2_name"]
            coin = vs_player[event.group_id]["coin"]
            await add_gold(winner, coin)
            await spend_gold(loser, coin)
            await start.send(f"上局超时，强行结算！\n{winner_name}胜利，赚取{coin}金币！\n{loser_name}失败，扣除{coin}金币！\n")
            vs_player = {}
    except KeyError:
        pass

    msg = arg.extract_plain_text().strip().split()
    if len(msg) != 2:
        await start.finish("请输入正确成语和金币数(空格隔开)...")
    if not check_result(msg[0]):
        await start.finish(f"你确定{msg[0]}是成语？？？")
    if not msg[1].isdigit():
        await start.finish("请输入正确的金币数！")
    idiom = msg[0]
    coin = int(msg[1])
    user_coin = await get_gold(event.user_id)
    if user_coin < coin:
        await start.finish("你的金币不够！", at_sender=True)
    # await start.send(
    #    f"已发起对局，请挑战者在{dati_time}秒内发送'接'+以{lazy_pinyin(idiom)[-1]}开头的成语，赌注{coin}金币！(之前说过的不能再说)",
    #    at_sender=True)
    await start.send(
        f"已发起对局，请挑战者在{dati_time}秒内轮流发送'接'+以上一个成语尾字拼音开头的成语，赌注{coin}金币！(之前说过的不能再说)",
        at_sender=True,
    )
    vs_player[event.group_id] = {
        "player1": event.user_id,
        "player1_name": event.sender.card or event.sender.nickname,
        "player2": 0,
        "player2_name": "",
        "time": time.time(),
        "next_idiom": lazy_pinyin(idiom)[-1],
        "next_player": 0,
        "coin": coin,
        "log": [idiom],
    }
    set_timeout(bot, event, dati_time)


@submit.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global vs_player
    try:
        if (event.user_id == vs_player[event.group_id]["player1"] and 2 == vs_player[event.group_id]["next_player"]) or (
            event.user_id == vs_player[event.group_id]["player2"] and 1 == vs_player[event.group_id]["next_player"]
        ):
            await submit.finish("你搁这自己跟自己玩呢，大聪明？", at_sender=True)
        elif event.user_id != vs_player[event.group_id]["player1"] and 0 == vs_player[event.group_id]["player2"]:
            user_coin = await get_gold(event.user_id)
            if user_coin < vs_player[event.group_id]["coin"]:
                await submit.finish("你的金币不够！", at_sender=True)
            msg = arg.extract_plain_text().strip().split()
            if (not check_result(msg[0])) or len(msg) != 1:
                await submit.finish(f"你确定{msg[0]}是成语？？？", at_sender=True)
            if lazy_pinyin(msg[0])[0] != vs_player[event.group_id]["next_idiom"]:
                start_idiom = vs_player[event.group_id]["next_idiom"]
                await submit.finish(f"成语要以{start_idiom}开头啊喂！", at_sender=True)
            log_list = vs_player[event.group_id]["log"]
            if msg[0] in log_list:
                await submit.finish(f"{msg[0]}已经被说过了！", at_sender=True)
            vs_player[event.group_id]["player2"] = event.user_id
            vs_player[event.group_id]["player2_name"] = event.sender.card or event.sender.nickname
            vs_player[event.group_id]["time"] = time.time()
            vs_player[event.group_id]["next_player"] = 1
            vs_player[event.group_id]["next_idiom"] = lazy_pinyin(msg[0])[-1]
            vs_player[event.group_id]["log"].append(msg[0])
            p2 = vs_player[event.group_id]["player2_name"]
            p1 = vs_player[event.group_id]["player1"]
            set_timeout(bot, event, dati_time)
            await submit.send(Message(f"{p2}接受对局！请{MessageSegment.at(p1)}在{dati_time}秒内接以{lazy_pinyin(msg[0])[-1]}开头的成语！"))
        elif event.user_id != vs_player[event.group_id]["player1"] and event.user_id != vs_player[event.group_id]["player2"]:
            p2 = vs_player[event.group_id]["player2_name"]
            p1 = vs_player[event.group_id]["player1_name"]
            await submit.finish(f"别搁这捣乱，这是{p1}和{p2}的对局！", at_sender=True)
        elif (event.user_id == vs_player[event.group_id]["player1"] and 1 == vs_player[event.group_id]["next_player"]) or (
            event.user_id == vs_player[event.group_id]["player2"] and 2 == vs_player[event.group_id]["next_player"]
        ):
            cost_time = int(time.time() - vs_player[event.group_id]["time"])
            if cost_time > dati_time:
                await submit.send(f"你用时{cost_time}秒,超时了！\n", at_sender=True)
                winner = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2"]
                loser = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2"]
                winner_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2_name"]
                loser_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2_name"]
                coin = vs_player[event.group_id]["coin"]
                await add_gold(winner, coin)
                await spend_gold(loser, coin)
                log_idiom = "->".join(vs_player[event.group_id]["log"])
                await submit.send(f"答题超时，进行结算！对局详情:\n{log_idiom}\n{winner_name}胜利，赚取{coin}金币！\n{loser_name}失败，扣除{coin}金币！\n")
                vs_player[event.group_id] = {}
            else:
                msg = arg.extract_plain_text().strip().split()
                if (not check_result(msg[0])) or len(msg) != 1:
                    await submit.finish(f"你确定{msg[0]}是成语？？？", at_sender=True)
                if lazy_pinyin(msg[0])[0] != vs_player[event.group_id]["next_idiom"]:
                    start_idiom = vs_player[event.group_id]["next_idiom"]
                    await submit.finish(f"成语要以{start_idiom}开头啊喂！", at_sender=True)
                log_list = vs_player[event.group_id]["log"]
                if msg[0] in log_list:
                    await submit.finish(f"{msg[0]}已经被说过了！", at_sender=True)
                vs_player[event.group_id]["next_idiom"] = lazy_pinyin(msg[0])[-1]
                vs_player[event.group_id]["next_player"] = 1 if vs_player[event.group_id]["next_player"] == 2 else 2
                vs_player[event.group_id]["time"] = time.time()
                next_one = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2"]
                vs_player[event.group_id]["log"].append(msg[0])
                set_timeout(bot, event, dati_time)
                # await submit.send(
                #    Message(
                #        f"请{at(next_one)}在{dati_time}秒内接以{lazy_pinyin(msg[0])[-1]}开头的成语！"
                #    ))
    except Exception as e:
        print(e)
        pass


@stop_game.handle()
async def stop(bot: Bot, event: GroupMessageEvent):
    global vs_player
    try:
        if 0 == vs_player[event.group_id]["player1"] or 0 == vs_player[event.group_id]["player2"]:
            await stop_game.send("对局超时，自动清零！")
            vs_player[event.group_id] = {}
        elif vs_player[event.group_id]["player1"] and vs_player[event.group_id]["player2"]:  # and time.time() - vs_player[event.group_id]["time"] > dati_time):
            winner = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2"]
            loser = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2"]
            winner_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2_name"]
            loser_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2_name"]
            coin = vs_player[event.group_id]["coin"]
            await add_gold(winner, coin)
            await spend_gold(loser, coin)
            log_idiom = "->".join(vs_player[event.group_id]["log"])
            await stop_game.send(f"{loser_name}回答超时，强行结算！对局详情:\n{log_idiom}\n{winner_name}胜利，赚取{coin}金币！\n{loser_name}失败，扣除{coin}金币！\n")
            vs_player[event.group_id] = {}
        elif (vs_player[event.group_id]["player1"] and vs_player[event.group_id]["player2"]) and event.user_id == vs_player[event.group_id]["next_player"]:
            winner = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2"]
            loser = vs_player[event.group_id]["player1"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2"]
            winner_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 2 else vs_player[event.group_id]["player2_name"]
            loser_name = vs_player[event.group_id]["player1_name"] if vs_player[event.group_id]["next_player"] == 1 else vs_player[event.group_id]["player2_name"]
            coin = vs_player[event.group_id]["coin"]
            await add_gold(winner, coin)
            await spend_gold(loser, coin)
            log_idiom = "->".join(vs_player[event.group_id]["log"])
            await stop_game.send(f"{loser_name}认输，进行结算！对局详情:\n{log_idiom}\n{winner_name}胜利，赚取{coin}金币！\n{loser_name}失败，扣除{coin}金币！\n")
            vs_player[event.group_id] = {}
    except:
        pass


def set_timeout(bot: Bot, event: GroupMessageEvent, timeout: float = 300):
    global timers
    timer = timers.get(event.group_id, None)
    if timer:
        timers.pop(event.group_id)
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(timeout, lambda: asyncio.ensure_future(stop(bot, event)))
    timers[event.group_id] = timer


# 检查正确性
def check_result(answer: str) -> int:
    for item in answer:
        if not "\u4e00" <= item <= "\u9fa5":
            return False
    # 使用本地词库验证成语合法性
    return True if answer in idiom_list else False
    # 以下为使用api验证成语合法性
    # resp = requests.get(check_url.format(answer))
    # resp = resp.text

    # retdata = json.loads(resp)
    # code = retdata['code']
    # return True if code == 200 else Falsed
