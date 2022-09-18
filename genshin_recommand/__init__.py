# -*- coding: utf-8 -*-
import os
import random
import re
from typing import Tuple

import nonebot
from nonebot import on_command, Driver, on_regex
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import RawCommand, RegexGroup

from services import logger
from utils.http_utils import AsyncHttpx
from utils.message_builder import image
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
        深渊配队
        XX攻略
""".strip()
__plugin_des__ = "查询角色攻略"
__plugin_cmd__ = ["角色配装", "角色评级", "武器推荐", "深渊配队"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 0.6
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

get_guide = on_command("角色配装", aliases={"角色评级", "武器推荐", "深渊配队"}, priority=15, block=True)
role_guide = on_regex(r".*?(.*)攻略", priority=15)
common_guide = "https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/common_guide/{}.jpg"
genshin_role_guide = "https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/genshin_role_guide/{}.png"
RES_PATH = os.path.join(os.path.dirname(__file__), "res")


@get_guide.handle()
async def _(arg: Message = RawCommand()):
    save_path = f'{RES_PATH}/{arg}.jpg'
    if os.path.exists(save_path):
        await get_guide.finish(image(save_path))
    try:
        await AsyncHttpx.download_file(common_guide.format(arg), save_path, follow_redirects=True)
    except TimeoutError:
        return await get_guide.send("获取推荐超时")
    await get_guide.send(image(save_path))


@role_guide.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    save_path = f'{RES_PATH}/{role}.png'
    if os.path.exists(save_path):
        await role_guide.finish(image(save_path))
    try:
        await AsyncHttpx.download_file(genshin_role_guide.format(role), save_path, follow_redirects=True)
    except TimeoutError:
        return await role_guide.send("获取推荐超时")
    try:
        await role_guide.send(image(save_path))
    except:
        os.unlink(save_path)


@driver.on_bot_connect
@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def check_update():
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_recommand/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main" \
              "/genshin_recommand/__init__.py "
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
