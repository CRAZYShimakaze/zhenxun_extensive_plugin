# -*- coding: utf-8 -*-
import random
import re

import nonebot
from nonebot import on_command, Driver
from nonebot.adapters.onebot.v11 import MessageSegment

from services import logger
from utils.http_utils import AsyncHttpx
from utils.utils import scheduler, get_bot

driver: Driver = nonebot.get_driver()

__zx_plugin_name__ = "原神角色攻略"
__plugin_usage__ = """
usage：
    查询角色攻略
    指令：
        角色配装
        角色评级
        武器推荐
""".strip()
__plugin_des__ = "查询角色攻略"
__plugin_cmd__ = ["角色配装", "角色评级", "武器推荐"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 0.5
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
__plugin_cd_limit__ = {
    "rst": "正在查询中，请当前请求完成...",
}

equip = on_command("角色配装", priority=15, block=True)
grade = on_command("角色评级", priority=15, block=True)
weapon = on_command("武器推荐", priority=15, block=True)

address_list = {"equip": "https://s3.bmp.ovh/imgs/2022/09/01/2211532ef945c055.jpg",
                "grade": "https://s3.bmp.ovh/imgs/2022/09/01/f00c4edb99eac50c.jpg",
                "weapon": "https://s3.bmp.ovh/imgs/2022/09/05/cfd3ef62ed42ddad.jpg"}


@equip.handle()
async def _():
    try:
        img = await AsyncHttpx().get(address_list["equip"])
    except:
        return await equip.send("获取装备推荐超时")
    await equip.send(MessageSegment.image(img.content))


@grade.handle()
async def _():
    try:
        img = await AsyncHttpx().get(address_list["grade"])
    except:
        return await grade.send("获取角色评级超时")
    await grade.send(MessageSegment.image(img.content))


@weapon.handle()
async def _():
    try:
        img = await AsyncHttpx().get(address_list["weapon"])
    except:
        return await weapon.send("获取装备推荐超时")
    await weapon.send(MessageSegment.image(img.content))


@driver.on_bot_connect
@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def check_update():
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_info/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main" \
              "/genshin_role_info/__init__.py "
        try:
            version = await AsyncHttpx.get(url)
            version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                                str(version.text))
        except Exception as e:
            for admin in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(admin),
                    message=f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!")
            logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
            return
    if float(version.group(1)) > __plugin_version__:
        for admin in bot.config.superusers:
            await bot.send_private_msg(user_id=int(admin),
                                       message=f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
        logger.warning(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
