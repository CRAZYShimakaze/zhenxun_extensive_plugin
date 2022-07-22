from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP, Bot, GroupMessageEvent, Message
from nonebot.typing import T_State
from utils.utils import is_number, get_message_at
from nonebot.params import CommandArg, Command, ArgStr
from models.group_member_info import GroupInfoUser
from utils.message_builder import at, image
from models.bag_user import BagUser
from services.log import logger
from configs.config import NICKNAME, Config
from typing import Tuple
import random
import asyncio
import time
import math

__zx_plugin_name__ = "打工"
__plugin_usage__ = """
usage：
    缺钱么朋友,那就来当社畜吧!
    指令：
        打工: 开始游戏，固定时间内计算多道数学题来获取金币
        提交 [答案1 答案2 ...]: 进行结算
        结束打工：直接结束游戏
""".strip()
__plugin_des__ = "缺钱么朋友,那就来当社畜吧!"
__plugin_cmd__ = [
    "打工",
    "提交",
    "结束打工",
]
__plugin_type__ = ("群内小游戏", )
__plugin_version__ = 0.2
__plugin_author__ = "CRAZYShimakaze、Syozhi"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
__plugin_configs__ = {
    "TIMU_NUM": {
        "value": 5,
        "help": "题目数量",
        "default_value": 5,
    },
    "DATI_TIME": {
        "value": 120,
        "help": "答题时长(秒)",
        "default_value": 120,
    },
    "MONEYS": {
        "value": [0, 50, 100, 200, 200],
        "help": "工资，对应答对题目数",
        "default_value": [0, 10, 50, 200, 200],
    },
    "QUIRKY": {
        "value": 0.8,
        "help": "快答奖励基数（剩余时长*基数=快答奖励，全作对才有快答奖励哦），设置为0则关闭快答奖励",
        "default_value": 0.8,
    }
}

# 工资，对应答对题目数
moneys = Config.get_config("work", "MONEYS", [0, 10, 50, 200, 200])
# 快答奖励基数（剩余时长*基数=快答奖励，全作对才有快答奖励哦），设置为0则关闭快答奖励
quirky = Config.get_config("work", "QUIRKY", 0.8)
# 答题数量
timu_num = Config.get_config("work", "TIMU_NUM", 5)
# 答题时长(秒)
dati_time = Config.get_config("work", "DATI_TIME", 120)

# 防止题目数量与工资数组不对应
if len(moneys)<timu_num :
    for x in range(timu_num-len(moneys)):
        moneys.append(200)

cal_player = {}

start = on_command("打工", permission=GROUP, priority=5, block=True)

submit = on_command("提交", permission=GROUP, priority=5, block=True)

stop_game = on_command("结束打工", permission=GROUP, priority=5, block=True)


@start.handle()
async def _(bot: Bot,
            event: GroupMessageEvent,
            state: T_State,
            arg: Message = CommandArg()):
    global cal_player
    if arg:
        return
    try:
        if (cal_player[event.group_id]['player'] == event.user_id
                and time.time() - cal_player[event.group_id]["time"] <= dati_time):
            await start.finish(f'你现在已经在打工了!\n认真一点啊喂...')
        elif (cal_player[event.group_id]['player']
              and time.time() - cal_player[event.group_id]["time"] <= dati_time):
            await start.finish(f'现在有人正在打工\n请稍后再开始下一轮...')
        elif (cal_player[event.group_id]['player']
              and time.time() - cal_player[event.group_id]["time"] > dati_time):
            cal_player = {}
    except KeyError:
        pass
    await start.send(f"呦吼，小真寻正在出题ing...")
    question, answer = random_question(timu_num)
    await asyncio.sleep(1)
    await start.send(f"请在{dati_time}秒内完成以下{timu_num}道题目,输入'提交 X X X'进行提交:\n" +
                     "\n".join(question),
                     at_sender=True)
    cal_player[event.group_id] = {
        "player": event.user_id,
        "time": time.time(),
        "answer": answer
    }


@submit.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global cal_player
    try:
        if event.user_id == cal_player[event.group_id]['player']:
            cost_time = int(time.time() - cal_player[event.group_id]["time"])
            if cost_time > dati_time:
                await submit.send(f"你用时{cost_time}秒,算得太慢了,请重新申请吧！",
                                  at_sender=True)
            else:
                msg = arg.extract_plain_text().strip().split()
                await submit.send(f"哼哼哼,检查结果ing...")
                await asyncio.sleep(1)
                cnt = check_result(msg, cal_player[event.group_id]['answer'])
                tax = 0
                if not cnt:
                    await bot.send(event, message=f"你太菜了,竟然一道也没做出来!")
                elif cnt > math.ceil(timu_num/3):
                    tax = random.randint(0, 2)
                    # 快答奖励
                    ex_moneys = 0
                    ex_message = ""
                    if cnt == timu_num and quirky != 0 :
                        ex_moneys = math.ceil(dati_time*quirky)
                        ex_message = f",其中快答奖励{ex_moneys}金币"
                    await BagUser.add_gold(event.user_id, event.group_id,
                                           moneys[cnt-1] + ex_moneys - tax)
                    await bot.send(
                        event,
                        message=
                        f"你{cost_time}秒做对了{cnt}道题,这是你的工资:{moneys[cnt-1] + ex_moneys}金币{ex_message},扣税后得到{(moneys[cnt-1]) + ex_moneys - tax}金币!",
                        at_sender=True)
                else:
                    await BagUser.add_gold(event.user_id, event.group_id, (moneys[cnt-1]))
                    await bot.send(
                        event,
                        message=
                        f"你{cost_time}秒做对了{cnt}道题,这是你的工资:{moneys[cnt-1]}金币,工资太低不需要交税!",
                        at_sender=True)
            cal_player[event.group_id] = {}
        else:
            await submit.finish(
                random.choice([
                    f"给我好好做好一个观众！不然{NICKNAME}就要生气了",
                    f"不要捣乱啊baka{(await GroupInfoUser.get_member_info(event.user_id, event.group_id)).user_name}！",
                ]),
                at_sender=True,
            )
    except:
        pass


@stop_game.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    global cal_player
    try:
        if cal_player[event.group_id]['player']:
            cal_player[event.group_id] = {}
            await submit.finish("游戏已结束!")
    except:
        pass


# 随机算式
def random_question(num: int):
    question_list = []
    answer = []
    for i in range(num):
        x = str(random.randint(0, 99))
        a = random.choice(['+', '-'])  #, '*', '/'])
        y = str(random.randint(0, 99))
        b = random.choice(['+', '-'])  #, '*', '/'])
        z = str(random.randint(0, 99))
        answer.append(round(eval(x + a + y)))  # + b + z)))
        question_list.append(x + a + y + '=?')  # + b + z + '=?')
    return question_list, answer


# 检查正确性
def check_result(submit: list, answer: list) -> int:
    cnt = 0
    for i in range(min(len(answer), len(submit))):
        if str(answer[i]) == str(submit[i]):
            cnt += 1
    return cnt