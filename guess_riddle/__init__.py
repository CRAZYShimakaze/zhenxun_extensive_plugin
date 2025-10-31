import asyncio
import re
import shlex
from asyncio import TimerHandle
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, NoReturn, Optional

from nonebot import on_command, on_message, on_shell_command
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText, ShellCommandArgv
from nonebot.plugin import PluginMetadata
from nonebot.rule import ArgumentParser, Rule
from nonebot.typing import T_State
from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import PluginType

from ..plugin_utils.auth_utils import add_gold, get_gold, spend_gold
from .data_source import GuessResult, Handle
from .utils import load_font, random_idiom

__plugin_meta__ = PluginMetadata(
    name="猜成语",
    description="猜成语",
    usage="""
    汉字 猜成语
    你有十次的机会猜一个四字词语；
    每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；
    青色 表示其出现在答案中且在正确的位置；
    橙色 表示其出现在答案中但不在正确的位置；
    当四个格子都为青色时，你便赢得了游戏！
    指令：
        猜成语：开始游戏；
        可发送“结束猜成语”结束游戏；可发送“提示”查看提示。
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.3",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)


parser = ArgumentParser("handle", description="猜成语")
parser.add_argument("--hint", action="store_true", help="提示")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("idiom", nargs="?", help="成语")


@dataclass
class Options:
    hint: bool = False
    stop: bool = False
    idiom: str = ""


games: dict[str, Handle] = {}
timers: dict[str, TimerHandle] = {}

handle = on_shell_command("handle", parser=parser, block=True, priority=6)
bounce_coin = [10, 10, 10, 10, 10, 10, 9, 8, 7, 2, 1]
hint_cost = [9, 8, 7, 6, 5, 4, 3, 2, 0, 0]


@handle.handle()
async def _(matcher: Matcher, event: MessageEvent, argv: list[str] = ShellCommandArgv()):
    await handle_handle(matcher, event, argv)


def get_cid(event: MessageEvent):
    return f"group_{event.group_id}" if isinstance(event, GroupMessageEvent) else f"private_{event.user_id}"


def game_running(event: MessageEvent) -> bool:
    cid = get_cid(event)
    return bool(games.get(cid, None))


def match_idiom(msg: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fa5]{4}", msg))


def get_idiom_input(state: T_State, msg: str = EventPlainText()) -> bool:
    if match_idiom(msg):
        state["idiom"] = msg
        return True
    return False


def shortcut(cmd: str, argv: list[str] = [], **kwargs):
    command = on_command(cmd, **kwargs, block=True, priority=5)

    @command.handle()
    async def _(matcher: Matcher, event: MessageEvent, msg: Message = CommandArg()):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except:
            args = []
        await handle_handle(matcher, event, argv + args)


shortcut("猜成语")
shortcut("提示", ["--hint"], aliases={"给个提示"}, rule=game_running)
shortcut("结束猜成语", ["--stop"], rule=game_running)

idiom_matcher = on_message(Rule(game_running) & get_idiom_input, block=True, priority=7)


@idiom_matcher.handle()
async def _(matcher: Matcher, event: MessageEvent, state: T_State):
    idiom: str = state["idiom"]
    await handle_handle(matcher, event, [idiom])


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        msg = "猜成语超时，游戏结束"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await matcher.finish(msg)


def set_timeout(matcher: Matcher, cid: str, timeout: float = 300):
    timer = timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(timeout, lambda: asyncio.ensure_future(stop_game(matcher, cid)))
    timers[cid] = timer


async def handle_handle(matcher: Matcher, event: MessageEvent, argv: list[str]):
    async def send(message: str | None = None, image: BytesIO | None = None) -> NoReturn:
        if not (message or image):
            await matcher.finish()
        msg = Message()
        if image:
            msg.append(MessageSegment.image(image))
        if message:
            msg.append(message)
        await matcher.finish(msg)

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__plugin_usage__)
        await send()

    options = Options(**vars(args))

    cid = get_cid(event)
    if not games.get(cid, None):
        game = Handle(await random_idiom())
        await game.get_tff()
        games[cid] = game
        set_timeout(matcher, cid)
        await send(f"你有{game.times}次机会猜一个四字成语，请发送成语", game.draw())

    if options.stop:
        game = games.pop(cid)
        msg = "游戏已结束"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await send(msg)

    game = games[cid]
    set_timeout(matcher, cid)

    if options.hint:
        # if len(game.guessed_idiom) > 6:
        #     await send(image=game.draw_hint())
        # else:
        #     await send("猜错7次后才可以提示哦!")
        image = game.draw_hint()
        if isinstance(event, GroupMessageEvent):
            cost_coin = hint_cost[len(game.guessed_idiom)]
            have_gold = await get_gold(event.user_id)
            if have_gold < cost_coin:
                await send(f"当前提示需要{cost_coin}金币,你的金币不够!")
                return
            else:
                await spend_gold(event.user_id, cost_coin)
                await send(f"扣除{cost_coin}金币获取提示...", image)
        else:
            await send(image)
    idiom = options.idiom
    if not match_idiom(idiom):
        await send()

    result = game.guess(idiom)
    if result in [GuessResult.WIN, GuessResult.LOSS]:
        games.pop(cid)
        # await send(
        #     ("恭喜你猜出了成语!" if result == GuessResult.WIN else "很遗憾，没有人猜出来呢")
        #     + f"\n{game.result}",
        #     game.draw(),
        # )
        if result == GuessResult.WIN:
            await add_gold(event.user_id, bounce_coin[len(game.guessed_idiom)])
        await send(
            (f"恭喜你猜出了成语！奖励你{bounce_coin[len(game.guessed_idiom)]}金币!" if result == GuessResult.WIN else "很遗憾，没有人猜出来呢") + f"\n{game.result}",
            game.draw(),
        )
    elif result == GuessResult.DUPLICATE:
        await send("你已经猜过这个成语了呢")
    else:
        await send(image=game.draw())
