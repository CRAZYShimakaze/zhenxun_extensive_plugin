# -*- coding: utf-8 -*-
from nonebot import on_command
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import Event
from utils.http_utils import AsyncHttpx

__zx_plugin_name__ = "角色评级和配装"
__plugin_usage__ = """
usage：
    查询角色配装或角色评级推荐
    指令：
        原神角色配装
        原神角色评级
""".strip()
__plugin_des__ = "查询角色配装或角色评级推荐"
__plugin_cmd__ = ["原神角色配装", "原神角色评级"]
__plugin_type__ = ("原神相关", )
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["原神角色配装", "原神角色评级"],
}
__plugin_cd_limit__ = {
    "rst": "正在查询中，请当前请求完成...",
}

equip = on_command("原神角色配装", priority=15, block=True)
grade = on_command("原神角色评级", priority=15, block=True)


@equip.handle()
async def hf(bot: Bot, ev: Event):
    address_list = "https://s3.bmp.ovh/imgs/2022/06/04/14c1872b9c991383.png"
    try:
        choose = address_list
        img = await AsyncHttpx().get(choose)
    except:
        return await bot.send(event=ev, message="获取装备推荐超时")
    await bot.send(event=ev, message=MessageSegment.image(img.content))


@grade.handle()
async def hf(bot: Bot, ev: Event):
    address_list = "https://s3.bmp.ovh/imgs/2022/06/04/4cfe79ce21237663.png"
    try:
        choose = address_list
        img = await AsyncHttpx().get(choose)
    except:
        return await bot.send(event=ev, message="获取角色评级超时")
    await bot.send(event=ev, message=MessageSegment.image(img.content))
