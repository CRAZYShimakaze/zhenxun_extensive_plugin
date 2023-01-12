# -*- coding: utf-8 -*-
import json
import os
import random
import re
import shutil
from typing import Tuple

import nonebot
from nonebot import on_command, Driver, on_regex
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER

from configs.config import Config
from services import logger
from utils.http_utils import AsyncHttpx
from utils.message_builder import image
from utils.utils import scheduler, get_bot

driver: Driver = nonebot.get_driver()

__zx_plugin_name__ = "原神攻略"
__plugin_usage__ = """
usage：
    查询原神攻略
    指令：
        角色配装/出装
        角色评级/推荐/建议
        武器推荐/适配/评级
        深渊配队/阵容
        每日/今日素材
        XX攻略
        XX图鉴
        XX素材/XX材料
""".strip()
__plugin_des__ = "查询原神攻略"
__plugin_cmd__ = ["角色配装", "角色评级", "武器推荐", "深渊配队", "每日素材"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 1.2
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
Config.add_plugin_config(
    "genshin_role_recommand",
    "CHECK_UPDATE",
    True,
    help_="定期自动检查更新",
    default_value=True,
)

common_role_equip = on_regex("^角色(配装|出装)$", priority=1, block=True)
common_role_grade = on_regex("^角色(评级|推荐|建议)$", priority=1, block=True)
common_weapon_grade = on_regex("^武器(推荐|适配|评级)$", priority=1, block=True)
common_abyss = on_regex("^深渊(配队|阵容)$", priority=1, block=True)
common_material = on_regex("^(每日|今日)素材$", priority=1, block=True)

update_info = on_command("更新原神推荐", permission=SUPERUSER, priority=3, block=True)
check_update = on_command("检查攻略插件更新", permission=SUPERUSER, priority=3, block=True)
role_guide = on_regex(r"(.*)攻略", priority=15)
genshin_info = on_regex(r"(.*)图鉴", priority=15)
break_material = on_regex(r"(.*)(素材|材料)", priority=15)
common_guide = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/common_guide/{}.jpg"
genshin_role_guide = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/genshin_role_guide/{}.png"
genshin_role_break = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/CRAZYShimakaze.github.io/main/genshin_role_break/{}.jpg"
genshin_role_info = "https://gitee.com/Ctrlcvs/xiaoyao-plus/raw/main/juese_tujian/{}.png"
genshin_weapon_info = "https://gitee.com/Ctrlcvs/xiaoyao-plus/raw/main/wuqi_tujian/{}.png"
RES_PATH = os.path.join(os.path.dirname(__file__), "res")
ROLE_GUIDE_PATH = RES_PATH + '/role_guide'
ROLE_BREAK_PATH = RES_PATH + '/role_break'
ROLE_INFO_PATH = RES_PATH + '/role_info'
COMMON_GUIDE_PATH = RES_PATH + '/common_guide'
WEAPON_INFO_PATH = RES_PATH + '/weapon_info'
alias_file = json.load(open(f'{os.path.dirname(__file__)}/alias.json', 'r', encoding='utf-8'))
role_list = alias_file['roles']
weapon_list = alias_file['weapons']


async def get_img(url, arg, save_path, ignore_exist):
    if not os.path.exists(save_path) or ignore_exist:
        await AsyncHttpx.download_file(url.format(arg), save_path, follow_redirects=True)


@common_role_equip.handle()
async def _():
    arg = '角色配装'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await common_role_equip.send(image(item))


@common_role_grade.handle()
async def _():
    arg = '角色评级'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await common_role_grade.send(image(item))


@common_weapon_grade.handle()
async def _():
    arg = '武器推荐'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await common_weapon_grade.send(image(item))


@common_abyss.handle()
async def _():
    arg = '深渊配队'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await common_abyss.send(image(item))


@common_material.handle()
async def _():
    arg = '每日素材'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}1.jpg', f'{COMMON_GUIDE_PATH}/{arg}2.jpg']
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, 0)
        await common_material.send(image(item))


@role_guide.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in role_list:
        if role in role_list.get(item):
            role = role_list.get(item)[0]
            break
    else:
        return
    save_path = f'{ROLE_GUIDE_PATH}/{role}.png'
    await get_img(genshin_role_guide, role, save_path, 0)
    try:
        await role_guide.send(image(save_path))
    except:
        os.unlink(save_path)


@genshin_info.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in role_list:
        if role in role_list.get(item):
            role = role_list.get(item)[0]
            break
    else:
        for item in weapon_list:
            if role in weapon_list.get(item) or role == item:
                role = item
                break
        else:
            return
        save_path = f'{WEAPON_INFO_PATH}/{role}.png'
        await get_img(genshin_weapon_info, role, save_path, 0)
        try:
            await genshin_info.send(image(save_path))
        except:
            os.unlink(save_path)
        return
    save_path = f'{ROLE_INFO_PATH}/{role}.png'
    await get_img(genshin_role_info, role, save_path, 0)
    try:
        await genshin_info.send(image(save_path))
    except:
        os.unlink(save_path)


@break_material.handle()
async def _(args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in role_list:
        if role in role_list.get(item):
            role = role_list.get(item)[0]
            break
    save_path = f'{ROLE_BREAK_PATH}/{role}.jpg'
    await get_img(genshin_role_break, role, save_path, 0)
    try:
        await break_material.send(image(save_path))
    except:
        os.unlink(save_path)


@update_info.handle()
async def _():
    await update_info.send('开始更新原神推荐信息,请耐心等待...')
    shutil.rmtree(RES_PATH)
    arg = ['角色配装', '角色评级', '武器推荐', '深渊配队', '每日素材1', '每日素材2']
    for item in arg:
        save_path = f'{COMMON_GUIDE_PATH}/{item}.jpg'
        try:
            await get_img(common_guide, item, save_path, 1)
        except:
            continue
    for item in role_list:
        role = role_list.get(item)[0]
        try:
            save_path = f'{ROLE_BREAK_PATH}/{role}.jpg'
            await get_img(genshin_role_break, role, save_path, 1)
            save_path = f'{ROLE_GUIDE_PATH}/{role}.png'
            await get_img(genshin_role_guide, role, save_path, 1)
            save_path = f'{ROLE_INFO_PATH}/{role}.png'
            await get_img(genshin_role_info, role, save_path, 1)
        except:
            continue
    for item in weapon_list:
        save_path = f'{WEAPON_INFO_PATH}/{item}.png'
        try:
            await get_img(genshin_weapon_info, item, save_path, 1)
        except:
            continue
    await update_info.send('更新原神推荐完成！')


async def get_update_info():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_recommand/README.md"
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"\*\*\[v\d.\d]((?:.|\n)*?)\*\*", str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件获取更新内容失败，请检查github连接性是否良好!: {e}")
        return ''
    return version.group(1).strip()


@check_update.handle()
async def _check_update():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_recommand/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        return
    if float(version.group(1)) > __plugin_version__:
        modify_info = await get_update_info()
        try:
            await check_update.send(
                f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{modify_info}")
        except Exception:
            for admin in bot.config.superusers:
                await bot.send_private_msg(user_id=int(admin),
                                           message=f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{modify_info}")
            logger.warning(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
    else:
        try:
            modify_info = await get_update_info()
            await check_update.send(
                f"{__zx_plugin_name__}插件已经是最新V{__plugin_version__}！最近一次的更新内容如下:\n{modify_info}")
        except Exception:
            pass


@driver.on_startup
async def _():
    if Config.get_config("genshin_role_recommand", "CHECK_UPDATE"):
        scheduler.add_job(_check_update, "cron", hour=random.randint(9, 22), minute=random.randint(0, 59),
                          id='genshin_role_recommand')
