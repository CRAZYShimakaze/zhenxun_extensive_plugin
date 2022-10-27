from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP, Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg

from models.bag_user import BagUser
from .data_source import Draw_Handle
from .utils import random_question, check_result

__zx_plugin_name__ = "24点"
__plugin_usage__ = """
usage：
    24点游戏,使用给出的四个数字，利用+-*/算出24(可使用括号)!
    指令：
        24点: 开始游戏
        解答 a+b+c+d: 提交答案
        结束24点：直接结束游戏
""".strip()
__plugin_des__ = "24点"
__plugin_cmd__ = [
    "24点",
    "解答",
    "结束24点",
]
__plugin_type__ = ("群内小游戏",)
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

start = on_command("24点", permission=GROUP, priority=5, block=True)

submit = on_command("解答", permission=GROUP, priority=5, block=True)

stop_game = on_command("结束24点", permission=GROUP, priority=5, block=True)
answer = {}
question = {}


@start.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global answer, question
    msg = arg.extract_plain_text().strip()
    if msg:
        return
    if event.group_id in answer:
        if answer[event.group_id]:
            await bot.send(event, "上一局游戏还未结束!")
    else:
        question[event.group_id], answer[event.group_id] = random_question()
        handle = Draw_Handle()
        await handle.get_tff()
        handle.question = question[event.group_id]
        pic = MessageSegment.image(handle.draw())
        await bot.send(event, f"发送'解答'+答案,使用+-*/算出24(可使用括号):\n" + pic)


@submit.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    global answer
    if event.group_id in answer:
        if answer[event.group_id]:
            msg = arg.extract_plain_text().strip()
            msg = msg.replace('（', '(').replace('）', ')').replace('×', '*').replace('x', '*').replace('×', '*').replace(
                '÷', '/')
            mark = check_result(msg, question[event.group_id])
            bounce = 10
            if not mark:
                await bot.send(event,
                               "答案不对或输入格式有误!(仅可使用+-*/和括号)",
                               at_sender=True)
            else:
                await BagUser.add_gold(event.user_id, event.group_id, bounce)
                await bot.send(event,
                               f"恭喜你回答正确,奖励你{bounce}金币!",
                               at_sender=True)
                del answer[event.group_id]
        else:
            await bot.send(event, "现在没有开局哦,请输入24点来开始游戏!")
    else:
        await bot.send(event, "现在没有开局哦,请输入24点来开始游戏!")


@stop_game.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    global answer
    if event.group_id in answer:
        if answer[event.group_id]:
            answer_list = ''.join(answer[event.group_id])
            await submit.send(f"参考答案:\n{answer_list}\n本轮游戏已结束!")
            del answer[event.group_id]
    else:
        await submit.send("当前没有正在进行的24点游戏哦!")
