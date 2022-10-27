import re
import shlex
import asyncio
from io import BytesIO
from asyncio import TimerHandle
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, NoReturn

from configs.config import Config
from models.bag_user import BagUser

from nonebot.matcher import Matcher
from nonebot.exception import ParserExit
from nonebot.rule import ArgumentParser
from nonebot import on_command, on_shell_command
from nonebot.params import ShellCommandArgv, Command, RawCommand, CommandArg
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    Message,
    MessageSegment, Bot,
)

from .data_source import MineSweeper, GameState, OpenResult, MarkResult
from .utils import skin_list

__zx_plugin_name__ = "扫雷"
__plugin_des__ = "扫雷游戏"
__plugin_usage__ = f"""
扫雷 开始游戏；
扫雷初级 / 扫雷中级 / 扫雷高级 可开始不同难度的游戏；
可使用 -r/--row ROW 、-c/--col COL 、-n/--num NUM 自定义行列数和雷数；
可使用 -s/--skin SKIN 指定皮肤，默认为 winxp；
使用 挖开/open + 位置 来挖开方块，可同时指定多个位置；
使用 标记/mark + 位置 来标记方块，可同时指定多个位置；
位置为 字母+数字 的组合，如“A1”；
发送 查看游戏 查看当前游戏状态；
发送 结束扫雷 结束游戏；
发送 添加人员 + qq/@ 可以添加人员到游戏内，只能当前局内能进行游戏的人来进行添加；
""".strip()
__plugin_cmd__ = [
    "扫雷/open",
    "扫雷初级",
    "扫雷中级",
    "扫雷高级",
    "挖开/open",
    "标记/mark",
    "查看游戏/查看游戏盘/显示游戏/显示游戏盘",
    "结束扫雷",
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
__plugin_configs__ = {
    "gold_weight": {
        "value": 1,
        "help": "金币奖励系数,默认为1时总金币为格子数乘以地雷数",
        "default_value": 1, },
}
parser = ArgumentParser("minesweeper", description="扫雷")
parser.add_argument("-r", "--row", type=int, default=8, help="行数")
parser.add_argument("-c", "--col", type=int, default=8, help="列数")
parser.add_argument("-n", "--num", type=int, default=10, help="雷数")
parser.add_argument("-s", "--skin", default="winxp", help="皮肤")
parser.add_argument("--show", action="store_true", help="显示游戏盘")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("--open", nargs="*", default=[], help="挖开方块")
parser.add_argument("--mark", nargs="*", default=[], help="标记方块")
parser.add_argument("--add", nargs="*", default=[], help="添加游戏人员")


@dataclass
class Options:
    row: int = 0
    col: int = 0
    num: int = 0
    skin: str = ""
    show: bool = False
    stop: bool = False
    open: List[str] = field(default_factory=list)
    mark: List[str] = field(default_factory=list)
    add: List[str] = field(default_factory=list)


games: Dict[str, MineSweeper] = {}
timers: Dict[str, TimerHandle] = {}

minesweeper = on_shell_command("minesweeper", parser=parser, block=True, priority=13)


@minesweeper.handle()
async def _(
        matcher: Matcher, bot: Bot, event: MessageEvent, argv: List[str] = ShellCommandArgv()
):
    await handle_minesweeper(matcher, event, argv)


def get_cid(event: MessageEvent):
    return (
        f"group_{event.group_id}"
        if isinstance(event, GroupMessageEvent)
        else f"private_{event.user_id}"
    )


def game_running(event: MessageEvent) -> bool:
    cid = get_cid(event)
    return bool(games.get(cid, None))


# 命令前缀为空则需要to_me，否则不需要
def smart_to_me(
        event: MessageEvent, cmd: Tuple[str, ...] = Command(), raw_cmd: str = RawCommand()
) -> bool:
    return not raw_cmd.startswith(cmd[0]) or event.is_tome()


def shortcut(cmd: str, argv: List[str] = [], **kwargs):
    command = on_command(cmd, **kwargs, block=True, priority=12)

    @command.handle()
    async def _(matcher: Matcher, bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except:
            args = []
        await handle_minesweeper(matcher, bot, event, argv + args)


shortcut("扫雷", ["--row", "8", "--col", "8", "--num", "10"])
shortcut("扫雷初级", ["--row", "8", "--col", "8", "--num", "10"])
shortcut("扫雷中级", ["--row", "16", "--col", "16", "--num", "40"])
shortcut("扫雷高级", ["--row", "16", "--col", "30", "--num", "99"])
shortcut("挖开", ["--open"], aliases={"open", "wk"}, rule=game_running)
shortcut("标记", ["--mark"], aliases={"mark", "bj"}, rule=game_running)
shortcut("查看游戏", ["--show"], aliases={"查看游戏盘", "显示游戏", "显示游戏盘"}, rule=game_running)
shortcut("结束", ["--stop"], aliases={"停", "停止游戏", "结束游戏"}, rule=game_running)

add_player = on_command("添加人员", aliases={"添加玩家"}, rule=game_running)


def is_qq(msg: str):
    return msg.isdigit() and 11 >= len(msg) >= 5


@add_player.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    args = []
    for seg in msg["at"]:
        args.append(seg.data["qq"])
    try:
        texts = shlex.split(msg.extract_plain_text().strip())
        for text in texts:
            if is_qq(text):
                args.append(text)
    except:
        pass
    if args:
        await handle_minesweeper(matcher, bot, event, ["--add"] + args)


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        games.pop(cid)
        await matcher.finish("扫雷超时，游戏结束")


def set_timeout(matcher: Matcher, cid: str, timeout: float = 600):
    timer = timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(
        timeout, lambda: asyncio.ensure_future(stop_game(matcher, cid))
    )
    timers[cid] = timer


async def handle_minesweeper(matcher: Matcher, bot: Bot, event: MessageEvent, argv: List[str]):
    async def send(
            message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()
        msg = Message()
        if message:
            msg.append(message)
        if image:
            msg.append(MessageSegment.image(image))
        await matcher.finish(msg)

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__plugin_usage__)
        await send()

    help_msg = "使用 “挖开”+位置 挖开方块，使用 “标记”+位置 标记方块，可同时加多个位置，如：“挖开 A1 B2”"

    options = Options(**vars(args))

    cid = get_cid(event)
    if not games.get(cid, None):
        if options.open or options.mark or options.show or options.stop:
            await send("没有正在进行的游戏")

        if options.row < 8 or options.row > 24:
            await send("行数应在8~24之间")

        if options.col < 8 or options.col > 30:
            await send("列数应在8~30之间")

        if options.num < 10 or options.num > options.row * options.col * 3 // 4:
            await send("地雷数应不少于10且不多于行数*列数的3/4")

        if options.skin not in skin_list:
            await send("支持的皮肤：" + ", ".join(skin_list))

        game = MineSweeper(options.row, options.col, options.num, options.skin)
        games[cid] = game
        games[cid].players[str(event.user_id)] = 0
        set_timeout(matcher, cid)

        await send(help_msg, game.draw())

    game = games[cid]
    set_timeout(matcher, cid)

    if options.show:
        await send(image=game.draw())

    player_names = []
    for key, value in game.players.items():
        player_names.append(key)
    if str(event.user_id) not in player_names:
        await send("你不在本局游戏白名单中")

    if options.stop:
        games.pop(cid)
        await send("游戏已结束")

    if options.add:
        for id in options.add:
            game.players[str(id)] = 0
        await send("添加成功")

    open_positions = options.open
    mark_positions = options.mark
    if not (open_positions or mark_positions):
        await send(help_msg)

    def check_position(position: str) -> Optional[Tuple[int, int]]:
        match_obj = re.match(r"^([a-z])(\d+)$", position, re.IGNORECASE)
        if match_obj:
            x = (ord(match_obj.group(1).lower()) - ord("a")) % 32
            y = int(match_obj.group(2)) - 1
            return x, y

    msgs = []
    for position in open_positions:
        pos = check_position(position)
        if not pos:
            msgs.append(f"位置 {position} 不合法，须为 字母+数字 的组合")
            continue
        res = game.open(pos[0], pos[1])
        game.players[str(event.user_id)] += 1
        if res in [OpenResult.WIN, OpenResult.FAIL]:
            msg = ""
            if game.state == GameState.WIN:
                if isinstance(event, GroupMessageEvent):
                    msg = f"恭喜扫雷英雄们获得游戏胜利！以下为游戏战报:\n"
                    gold_weight = Config.get_config("minesweeper", "gold_weight")
                    gold_all = game.column * game.row * gold_weight
                    c_all = 0
                    for p, c in game.players.items():
                        c_all += c
                    for p, c in game.players.items():
                        p = int(p)  # 可下标对象不可await
                        name = await bot.get_group_member_info(group_id=event.group_id, user_id=p)
                        name = name["nickname"]
                        await BagUser.add_gold(p, event.group_id, gold_all * c // c_all)
                        msg = msg + f"{name}完成操作数{c},占{c / c_all * 100}%！奖励{int(gold_all * c / c_all)}金币！\n"
                else:
                    msg = "恭喜你获得游戏胜利！"
            elif game.state == GameState.FAIL:
                msg = "很遗憾，游戏失败"
            games.pop(cid)
            await send(msg, image=game.draw())
        elif res == OpenResult.OUT:
            msgs.append(f"位置 {position} 超出边界")
        elif res == OpenResult.DUP:
            msgs.append(f"位置 {position} 已经被挖过了")

    for position in mark_positions:
        pos = check_position(position)
        if not pos:
            msgs.append(f"位置 {position} 不合法，须为 字母+数字 的组合")
            continue
        res = game.mark(pos[0], pos[1])
        if res == MarkResult.WIN:
            if isinstance(event, GroupMessageEvent):
                msg = f"恭喜扫雷英雄们获得游戏胜利！以下为游戏战报:\n"
                gold_weight = Config.get_config("minesweeper", "gold_weight")
                gold_all = game.column * game.row // len(game.players) * gold_weight
                c_all = 0
                for p, c in game.players.items():
                    c_all += c
                for p, c in game.players.items():
                    p = int(p)  # 可下标对象不可await
                    name = await bot.get_group_member_info(group_id=event.group_id, user_id=p)
                    name = name["nickname"]
                    await BagUser.add_gold(p, event.group_id, gold_all * c // c_all)
                    msg = msg + f"{name}完成操作数{c},占{c / c_all * 100}%！奖励{int(gold_all * c / c_all)}金币！\n"
            else:
                msg = "恭喜你获得游戏胜利！"
            games.pop(cid)
            await send(msg, image=game.draw())
        elif res == MarkResult.OUT:
            msgs.append(f"位置 {position} 超出边界")
        elif res == MarkResult.OPENED:
            msgs.append(f"位置 {position} 已经被挖开了，不能标记")

    await send("\n".join(msgs), image=game.draw())
