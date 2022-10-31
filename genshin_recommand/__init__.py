# -*- coding: utf-8 -*-
import json
import os
import random
import re
from typing import Tuple

import nonebot
from PIL import Image, ImageDraw, ImageFont
from nonebot import on_command, Driver, on_regex
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import RawCommand, RegexGroup

from configs.path_config import FONT_PATH
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
        每日素材
        XX攻略
        XX素材
""".strip()
__plugin_des__ = "查询角色攻略"
__plugin_cmd__ = ["角色配装", "角色评级", "武器推荐", "深渊配队", "每日素材"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 0.9
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
__plugin_cd_limit__ = {
    "rst": "正在查询中，请等待当前请求完成...",
}

get_guide = on_command("角色配装", aliases={"角色评级", "武器推荐", "深渊配队", "每日素材"}, priority=14, block=True)
role_guide = on_regex(r"(.*)攻略", priority=15)
role_break = on_regex(r"(.*)素材", priority=15)
common_guide = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/common_guide/{}.jpg"
genshin_role_guide = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/genshin_role_guide/{}.png"
genshin_role_break = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/genshin_role_break/{}.jpg"
RES_PATH = os.path.join(os.path.dirname(__file__), "res")
alias_file = json.load(open(f'{RES_PATH}/../alias.json', 'r', encoding='utf-8'))
name_list = alias_file['roles']


async def get_img(url, arg, save_path, ignore_exist):
    if not os.path.exists(save_path) or ignore_exist:
        await AsyncHttpx.download_file(url.format(arg), save_path, follow_redirects=True)


@get_guide.handle()
async def _(arg: Message = RawCommand()):
    if arg != '每日素材':
        save_path = [f'{RES_PATH}/{arg}.jpg']
    else:
        save_path = [f'{RES_PATH}/{arg}1.jpg', f'{RES_PATH}/{arg}2.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await get_guide.send(image(item))


@role_guide.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in name_list:
        if role in name_list.get(item):
            role = name_list.get(item)[0]
            break
    else:
        return
    save_path = f'{RES_PATH}/{role}.png'
    await get_img(genshin_role_guide, role, save_path, 0)
    await role_guide.send(image(save_path))


@role_break.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in name_list:
        if role in name_list.get(item):
            role = name_list.get(item)[0]
            break
    else:
        return
    save_path = f'{RES_PATH}/{role}.jpg'
    await get_img(genshin_role_break, role, save_path, 0)
    img = Image.open(save_path)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((200, 1823),
                  "数据来源于米游社'再无四月的友人A.'",
                  fill='white',
                  font=ImageFont.truetype(f'{FONT_PATH}/HYWenHei-85W.ttf', 45))
    img.save(save_path)
    await role_break.send(image(save_path))


@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def guide_update():
    arg = ['角色配装', '角色评级', '武器推荐', '深渊配队', '每日素材1', '每日素材2']
    try:
        for item in arg:
            save_path = f'{RES_PATH}/{item}.jpg'
            await get_img(common_guide, item, save_path, 1)
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件更新攻略信息失败，请检查github连接性是否良好!: {e}")


@driver.on_bot_connect
@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def check_update():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_recommand/__init__.py"
    bot = get_bot()
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
