# -*- coding: utf-8 -*-
from curses.ascii import isdigit
from utils.utils import get_bot, scheduler
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from services.log import logger
from configs.path_config import IMAGE_PATH
from .data_source import get_alc_image
from nonebot.params import CommandArg
from utils.manager import group_manager
from configs.config import Config

__zx_plugin_name__ = "原神角色卡"
__plugin_usage__ = """
usage：
    查询橱窗第一个角色的面板
    指令：
        原神角色卡 uid
""".strip()
__plugin_des__ = "查询橱窗第一个角色的面板"
__plugin_cmd__ = ["原神角色卡 [uid]"]
__plugin_type__ = ("原神相关", )
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["原神角色卡"],
}
__plugin_block_limit__ = {
    "rst": "正在查询中，请当前请求完成...",
}

char_card = on_command("原神角色卡", priority=15, block=True)

CARD_PATH = IMAGE_PATH / "genshin" / "char_card"
CARD_PATH.mkdir(parents=True, exist_ok=True)


@char_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        msg = int(msg)
    except:
        await char_card.send("请输入正确uid...")
        return
    await char_card.send("开始获取角色信息,预计需要30秒...")
    try:
        alc_img = await get_alc_image(CARD_PATH, str(msg))
    except Exception as e:
        logger.info(f"{e}")
        return
    if alc_img:
        mes = alc_img + f"\nUID({str(msg)})的角色卡片"
        await char_card.send(mes)
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
            f" 发送原神角色卡")
    else:
        await char_card.send(f"获取UID({str(msg)})角色信息失败,请检查是否已开放橱窗信息权限!")
