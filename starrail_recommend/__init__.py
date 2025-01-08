# -*- coding: utf-8 -*-
import hashlib
import json
import os
import random
import re
from pathlib import Path
from typing import Tuple

import nonebot
from nonebot import on_command, Driver, on_regex
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER
from nonebot_plugin_apscheduler import scheduler

from ..plugin_utils.auth_utils import check_gold
from ..plugin_utils.http_utils import AsyncHttpx
from ..plugin_utils.image_utils import image

driver: Driver = nonebot.get_driver()

__zx_plugin_name__ = "星铁攻略"
__plugin_usage__ = """
usage：
    查询星铁攻略
    指令：
        光锥评级/推荐/建议
        遗器推荐/适配/评级
        角色配队/阵容
        XX攻略
        XX图鉴
        XX素材/材料
""".strip()
__plugin_des__ = "查询星铁攻略"
__plugin_cmd__ = ["角色配装", "角色评级", "武器推荐", "副本分析", "深渊配队", "每日素材"]
__plugin_type__ = ("星铁相关",)
__plugin_version__ = 0.6
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {"level": 5, "default_status": True, "limit_superuser": False, "cmd": __plugin_cmd__}
# common_role_equip = on_regex("^角色(配装|出装)$", priority=1, block=True)
# common_role_grade = on_regex("^角色(评级|推荐|建议)$", priority=1, block=True)
common_weapon_grade = on_regex("^光锥(推荐|适配|评级)$", priority=1, block=True)
common_artifact_guide = on_regex("^遗器(推荐|评级|分析)$", priority=1, block=True)
common_abyss = on_regex("^角色(配队|阵容)$", priority=1, block=True)

update_info = on_command("更新星铁推荐", permission=SUPERUSER, priority=3, block=True)
check_update = on_command("检查星铁插件更新", permission=SUPERUSER, priority=3, block=True)
role_guide = on_regex(r"(.*)攻略$", priority=15)
starrail_info = on_regex(r"(.*)图鉴$", priority=15)
break_material = on_regex(r"(.*)(素材|材料)$", priority=15)
src_url = "/CRAZYShimakaze/CRAZYShimakaze.github.io/main/starrail/"
nick_url = "/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_role_info/res/json_data/"
alias_url = nick_url + "nickname.json"

common_guide = src_url + "common_guide/{}.jpg"
starrail_role_guide = src_url + "role_guide/{}.png"
starrail_role_break = src_url + "role_break/{}.png"
starrail_role_info = src_url + "role_info/{}.png"
starrail_weapon_info = src_url + "weapon_info/{}.png"
RES_PATH = os.path.join(os.path.dirname(__file__), ".") + '/data'
ROLE_GUIDE_PATH = RES_PATH + '/role_guide'
ROLE_BREAK_PATH = RES_PATH + '/role_break'
ROLE_INFO_PATH = RES_PATH + '/role_info'
COMMON_GUIDE_PATH = RES_PATH + '/common_guide'
WEAPON_INFO_PATH = RES_PATH + '/weapon_info'
nickname_path = os.path.join(os.path.dirname(__file__), "./nickname.json")


def get_img_md5(image_file):
    with open(image_file, 'rb') as img:
        md5_value = hashlib.md5(img.read()).hexdigest()
    return md5_value


async def get_img(url, arg, save_path, ignore_exist):
    if not os.path.exists(save_path) or ignore_exist:
        await AsyncHttpx.download_file(get_raw() + url.format(arg), save_path, follow_redirects=True)


@role_guide.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for key, value in role_list.items():
        if role in value:
            role = key
            break
    else:
        return
    save_path = f'{ROLE_GUIDE_PATH}/{role}.png'
    await get_img(starrail_role_guide, role, save_path, ignore_exist=False)
    await check_gold(event, coin=10, percent=1)
    await role_guide.send(image(Path(save_path)))


@common_weapon_grade.handle()
async def _(event: MessageEvent):
    arg = '光锥推荐'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}1.jpg', f'{COMMON_GUIDE_PATH}/{arg}2.jpg', f'{COMMON_GUIDE_PATH}/{arg}3.jpg']
    await check_gold(event, coin=10, percent=1)
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, ignore_exist=False)
        await common_weapon_grade.send(image(Path(item)))


@common_artifact_guide.handle()
async def _(event: MessageEvent):
    arg = '遗器推荐'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}1.jpg', f'{COMMON_GUIDE_PATH}/{arg}2.jpg']
    await check_gold(event, coin=10, percent=1)
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, ignore_exist=False)
        await common_artifact_guide.send(image(Path(item)))


@common_abyss.handle()
async def _(event: MessageEvent):
    arg = '角色配队'
    save_path = [f'{COMMON_GUIDE_PATH}/{arg}1.jpg', f'{COMMON_GUIDE_PATH}/{arg}2.jpg']
    await check_gold(event, coin=10, percent=1)
    for item in save_path:
        await get_img(common_guide, item.split('/')[-1].strip('.jpg'), item, ignore_exist=False)
        await common_abyss.send(image(Path(item)))


@starrail_info.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for key, value in role_list.items():
        if role in value:
            role = key
            break
    else:
        for key, value in weapon_list.items():
            if role in value:
                role = key
                break
        else:
            return
        save_path = f'{WEAPON_INFO_PATH}/{role}.png'
        await get_img(starrail_weapon_info, role, save_path, ignore_exist=False)
        await starrail_info.send(image(Path(save_path)))
        return
    save_path = f'{ROLE_INFO_PATH}/{role}.png'
    await get_img(starrail_role_info, role, save_path, ignore_exist=False)
    await check_gold(event, coin=10, percent=1)
    await starrail_info.send(image(Path(save_path)))


@break_material.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for key, value in role_list.items():
        if role in value:
            role = key
            break
    else:
        return
    save_path = f'{ROLE_BREAK_PATH}/{role}.png'
    await get_img(starrail_role_break, role, save_path, ignore_exist=False)
    await break_material.send(image(Path(save_path)))


@update_info.handle()
async def _update_info(is_cron=False):
    global alias_file, role_list, weapon_list

    async def check_md5(path, name, url, md5_list):
        try:
            if not path.exists() or md5_list.get(name, '') != str(get_img_md5(path)):
                try:
                    await get_img(url, name, path, ignore_exist=True)
                except:
                    return False
                else:
                    return True
        except:
            return False

    await update_info.send('开始更新星铁推荐信息,请耐心等待...')
    # shutil.rmtree(RES_PATH, ignore_errors=True)
    # 追加昵称更新
    alias_remote_file = await AsyncHttpx.get(get_raw() + alias_url, follow_redirects=True)
    alias_remote = json.loads(alias_remote_file.text)
    # 保存昵称
    with open(nickname_path, "w", encoding="utf8") as f:
        json.dump(alias_remote, f, ensure_ascii=False, indent=2)
    # 更新缓存
    alias_file = await get_alias()
    role_list = alias_file['characters']
    weapon_list = alias_file['light_cones']
    common_guide_md5 = (await AsyncHttpx.get(f"{get_raw()}{src_url}common_guide/md5.json", follow_redirects=True)).json()
    role_info_md5 = (await AsyncHttpx.get(f"{get_raw()}{src_url}role_info/md5.json", follow_redirects=True)).json()
    role_break_md5 = (await AsyncHttpx.get(f"{get_raw()}{src_url}role_break/md5.json", follow_redirects=True)).json()
    role_guide_md5 = (await AsyncHttpx.get(f"{get_raw()}{src_url}role_guide/md5.json", follow_redirects=True)).json()
    weapon_info_md5 = (await AsyncHttpx.get(f"{get_raw()}{src_url}weapon_info/md5.json", follow_redirects=True)).json()
    update_list = set()

    for item in common_guide_md5.keys():
        save_path = Path(f'{COMMON_GUIDE_PATH}/{item}.jpg')
        if await check_md5(save_path, item, common_guide, common_guide_md5):
            update_list.add(item)
    for role in role_info_md5.keys():
        save_path = Path(f'{ROLE_INFO_PATH}/{role}.png')
        if await check_md5(save_path, role, starrail_role_info, role_info_md5):
            update_list.add(role)
    for role in role_break_md5.keys():
        save_path = Path(f'{ROLE_BREAK_PATH}/{role}.png')
        if await check_md5(save_path, role, starrail_role_break, role_break_md5):
            update_list.add(role)
    for role in role_guide_md5.keys():
        save_path = Path(f'{ROLE_GUIDE_PATH}/{role}.png')
        if await check_md5(save_path, role, starrail_role_guide, role_guide_md5):
            update_list.add(role)
    for item in weapon_info_md5.keys():
        save_path = Path(f'{WEAPON_INFO_PATH}/{item}.png')
        if await check_md5(save_path, item, starrail_weapon_info, weapon_info_md5):
            update_list.add(item)

    if not update_list and not is_cron:
        return await update_info.send(f'所有推荐信息均为最新！')
    if not update_list:
        return
    if not is_cron:
        await update_info.send(f'已更新{",".join(update_list)}的推荐信息！')
    else:
        bot = nonebot.get_bot()
        for admin in bot.config.superusers:
            await bot.send_private_msg(user_id=int(admin), message=f'已更新{",".join(update_list)}的推荐信息！')


async def get_alias():
    if not os.path.exists(nickname_path):
        await AsyncHttpx.download_file(get_raw() + alias_url, nickname_path, follow_redirects=True)
    return json.load(open(nickname_path, 'r', encoding='utf-8'))


def get_raw():
    raw = "https://raw.githubusercontent.com"
    return raw


async def get_update_info():
    url = f"{get_raw()}/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_recommend/README.md"
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r"\*\*\[v\d.\d]((?:.|\n)*?)\*\*", str(version.text))
    except Exception as e:
        print(f"{__zx_plugin_name__}插件获取更新内容失败，请检查github连接性是否良好!: {e}")
        return ''
    return version.group(1).strip()


@check_update.handle()
async def _check_update(is_cron=False):
    url = f"{get_raw()}/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_recommend/__init__.py"
    bot = nonebot.get_bot()
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})", str(version.text))
    except Exception as e:
        print(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        return
    if float(version.group(1)) > __plugin_version__:
        modify_info = await get_update_info()
        if not is_cron:
            await check_update.send(
                f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{modify_info}")
        else:
            for admin in bot.config.superusers:
                await bot.send_private_msg(user_id=int(admin),
                                           message=f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{modify_info}")
            print(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
    else:
        if not is_cron:
            modify_info = await get_update_info()
            await check_update.send(f"{__zx_plugin_name__}插件已经是最新V{__plugin_version__}！最近一次的更新内容如下:\n{modify_info}")


@driver.on_startup
async def _():
    global alias_file, role_list, weapon_list
    alias_file = await get_alias()
    role_list = alias_file['characters']
    weapon_list = alias_file['light_cones']
    scheduler.add_job(_check_update, "cron", args=[1], hour=random.randint(9, 22), minute=random.randint(0, 59), id='starrail_role_recommend_check_update')
    scheduler.add_job(_update_info, "cron", args=[1], hour=random.randint(9, 22), minute=random.randint(0, 59), id='starrail_role_recommend_update_info')
