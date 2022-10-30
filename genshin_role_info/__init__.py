# -*- coding: utf-8 -*-
import os
import random
import re
import shutil
import time
from pathlib import Path
from typing import Tuple

import nonebot
from nonebot import Driver
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent
from nonebot.params import CommandArg, RegexGroup
from nonebot.permission import SUPERUSER

from plugins.genshin.query_user._models import Genshin
from services.log import logger
from utils.http_utils import AsyncHttpx
from utils.message_builder import at
from utils.utils import get_bot, scheduler, get_message_at
from .data_source.draw_role_card import draw_role_card
from .utils.card_utils import load_json, player_info_path, PlayerInfo, json_path, other_path, get_name_by_id, \
    group_info_path
from .utils.image_utils import load_image, image_build

__zx_plugin_name__ = "原神角色面板"
__plugin_usage__ = """
usage：
    查询橱窗内角色的面板
    指令：
        原神角色卡 uid 角色名
        更新角色卡 uid
        角色面板 (例:刻晴面板、刻晴面板@XXX)
        更新面板
        我的角色
        他的角色@XXX
        最强XX (例:最强甘雨)
""".strip()
__plugin_des__ = "查询橱窗内角色的面板"
__plugin_cmd__ = ["原神角色面板", "更新角色面板", "我的角色", "他的角色", "XX面板", "群最强XX"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 1.7
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

char_card = on_command("原神角色卡", priority=4, block=True)
update_card = on_command("更新角色卡", priority=4, block=True)
my_card = on_command("我的角色", priority=4, block=True)
his_card = on_command("他的角色", aliases={"她的角色"}, priority=4, block=True)

driver: Driver = nonebot.get_driver()

get_card = on_regex(r"(.*)面板(.*)", priority=4)
group_best = on_regex(r"最强(.*)", priority=4)
reset_best = on_command("重置最强", permission=SUPERUSER, priority=3, block=True)

alias_file = load_json(path=f'{json_path}/alias.json')
name_list = alias_file['roles']


@get_card.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    at_user = args[1].strip()
    if role != "更新":
        for item in name_list:
            if role in name_list.get(item):
                role = name_list.get(item)[0]
                break
        else:
            return
    if at_user:
        uid = await Genshin.get_user_uid(get_message_at(event.json())[0])
    else:
        uid = await Genshin.get_user_uid(event.user_id)
    if not uid:
        await get_card.finish("请输入原神绑定uidXXXX进行绑定后再查询！")
    if not check_uid(uid):
        await my_card.finish(f"绑定的uid{uid}不合法，请重新绑定!")
    if role == "更新":
        await update(uid)
    else:
        await gen(event, uid, role)


@group_best.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    for item in name_list:
        if role in name_list.get(item):
            role = name_list.get(item)[0]
            break
    else:
        return
    role_path = f'{group_info_path}/{event.group_id}/{role}'
    if not os.path.exists(role_path):
        await group_best.finish(f"本群还没有{role}的数据收录哦！赶快去查询吧！", at_sender=True)
    else:
        role_info = os.listdir(role_path)[0]
        role_pic = load_image(f'{role_path}/{role_info}')
        role_pic = image_build(img=role_pic, quality=100, mode='RGB')
        await group_best.finish(f"本群最强{role}!由{role_info.split('-')[-1].rstrip('.png')}查询\n" + role_pic)


@reset_best.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    role = arg.extract_plain_text().strip()
    for item in name_list:
        if role in name_list.get(item):
            role = name_list.get(item)[0]
            break
    else:
        return
    role_path = f'{group_info_path}/{event.group_id}/{role}'
    shutil.rmtree(role_path, ignore_errors=True)
    await reset_best.finish(f'重置群最强{role}成功!')


@my_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg:
        return
    uid = await Genshin.get_user_uid(event.user_id)
    if not uid:
        await my_card.finish("请输入原神绑定uidXXXX进行绑定后再查询！")
    if not check_uid(uid):
        await my_card.finish(f"绑定的uid{uid}不合法，请重新绑定!")
    await get_char(uid)


async def get_char(uid: int):
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        try:
            req = await AsyncHttpx.get(url=url, follow_redirects=True)
        except Exception as e:
            print(e)
            await char_card.finish("更新出错,请重试...")
        if req.status_code != 200:
            await char_card.finish("服务器维护中,请稍后再试...")
        data = req.json()
        player_info = PlayerInfo(uid)
        try:
            player_info.set_player(data['playerInfo'])
            if 'avatarInfoList' in data:
                for role in data['avatarInfoList']:
                    player_info.set_role(role)
                player_info.save()
            else:
                guide = load_image(f'{other_path}/collections.png')
                guide = image_build(img=guide, quality=100, mode='RGB')
                await char_card.finish(guide + "在游戏中打开显示详情选项!", at_sender=True)
        except Exception as e:
            print(e)
            return  # await char_card.finish("发生错误，请尝试更新命令！", at_sender=True)
    else:
        player_info = PlayerInfo(uid)
    roles_list = player_info.get_roles_list()
    if not roles_list:
        guide = load_image(f'{other_path}/collections.png')
        guide = image_build(img=guide, quality=100, mode='RGB')
        await char_card.finish(guide + "无角色信息,在游戏中将角色放入展柜并输入更新角色卡XXXX(uid)!",
                               at_sender=True)
    else:
        await my_card.finish(f"uid{uid}的角色:{','.join(roles_list)}",
                             at_sender=True)


@his_card.handle()
async def _(event: MessageEvent):
    uid = await Genshin.get_user_uid(get_message_at(event.json())[0])
    if not uid:
        await his_card.finish("请输入原神绑定uidXXXX进行绑定后再查询！")
    await get_char(uid)


@char_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    try:
        uid = int(msg[0])
    except Exception as e:
        print(e)
        await char_card.finish("请输入正确uid+角色名(uid与角色名需要用空格隔开)", at_sender=True)
    if not check_uid(uid):
        await my_card.finish(f"uid{uid}不合法!")
    if len(msg) != 2:
        await char_card.finish("请输入正确角色名...", at_sender=True)
    role = msg[1]
    for item in name_list:
        if role in name_list.get(item):
            role = name_list.get(item)[0]
            break
    else:
        return
    await gen(event, uid, role)


async def gen(event: MessageEvent, uid: int, role_name: str):
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        try:
            req = await AsyncHttpx.get(
                url=url,
                follow_redirects=True,
            )
        except Exception as e:
            print(e)
            await char_card.finish("获取数据出错,请重试...")
        if req.status_code != 200:
            await char_card.finish("服务器维护中,请稍后再试...")
        data = req.json()
        player_info = PlayerInfo(uid)
        player_info.set_player(data['playerInfo'])
        if 'avatarInfoList' in data:
            for role in data['avatarInfoList']:
                player_info.set_role(role)
            player_info.save()
        else:
            guide = load_image(f'{other_path}/collections.png')
            guide = image_build(img=guide, quality=100, mode='RGB')
            await char_card.finish(guide + "在游戏中打开显示详情选项!", at_sender=True)
    else:
        player_info = PlayerInfo(uid)
    roles_list = player_info.get_roles_list()
    if not roles_list:
        guide = load_image(f'{other_path}/collections.png')
        guide = image_build(img=guide, quality=100, mode='RGB')
        await his_card.finish(guide + "无角色信息,在游戏中将角色放入展柜并输入更新角色卡XXXX(uid)!",
                              at_sender=True)
    if role_name not in roles_list:
        await char_card.finish(
            f"角色展柜里没有{role_name}的信息哦!可查询:{','.join(roles_list)}",
            at_sender=True)
    else:
        role_data = player_info.get_roles_info(role_name)
        img, score = await draw_role_card(uid, role_data)
        msg = check_best_role(role_name, event, img, score)
        img = image_build(img=img, quality=100, mode='RGB')
        await char_card.finish(msg + img + f"\n可查询角色:{','.join(roles_list)}", at_sender=True)


@update_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        uid = int(msg)
    except Exception as e:
        print(e)
        await update_card.finish("请输入正确uid...", at_sender=True)
    if not check_uid(uid):
        await update_card.finish(f"uid{uid}不合法!")
    await update(uid)


async def update(uid: int):
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if os.path.exists(f'{player_info_path}/{uid}.json'):
        mod_time = os.path.getmtime(f'{player_info_path}/{uid}.json')
        cd_time = int(time.time() - mod_time)
        if cd_time < 130:
            await char_card.finish(f'{130 - cd_time}秒后可再次更新!', at_sender=True)
    try:
        req = await AsyncHttpx.get(
            url=url,
            follow_redirects=True,
        )
    except Exception as e:
        print(e)
        await char_card.finish("更新出错,请重试...")
    if req.status_code != 200:
        await char_card.finish("服务器维护中,请稍后再试...")
    data = req.json()
    player_info = PlayerInfo(uid)
    player_info.set_player(data['playerInfo'])
    if 'avatarInfoList' in data:
        update_role_list = []
        for role in data['avatarInfoList']:
            player_info.set_role(role)
            update_role_list.append(get_name_by_id(str(role['avatarId'])))
    else:
        guide = load_image(f'{other_path}/collections.png')
        guide = image_build(img=guide, quality=100, mode='RGB')
        await char_card.finish(guide + "在游戏中打开显示详情选项!", at_sender=True)
    player_info.save()
    roles_list = player_info.get_roles_list()
    # await char_card.finish(f"更新uid{uid}的{','.join(update_role_list)}数据完成!\n可查询:{','.join(roles_list)}(注:数据更新有3分钟延迟)",at_sender=True)
    await char_card.finish(f"更新uid{uid}的{','.join(update_role_list)}数据完成!(注:数据更新有3分钟延迟)",
                           at_sender=True)


def check_best_role(role_name, event, img, score):
    if isinstance(event, GroupMessageEvent) and str(score)[-1] != '*':
        role_path = f'{group_info_path}/{event.group_id}/{role_name}/{score}-{event.user_id}.png'
        role_path = Path(role_path)
        role_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.listdir(role_path.parent):
            img.save(role_path)
            return f"恭喜成为本群最强{role_name}!\n"
        else:
            role_info = os.listdir(role_path.parent)[0].split('-')
            if float(role_info[0]) <= score:
                os.unlink(f'{role_path.parent}/{os.listdir(role_path.parent)[0]}')
                img.save(role_path)
                old_best = int(role_info[1].rstrip('.png'))
                if old_best != event.user_id:
                    return Message(f"恭喜你击败{at(old_best)}成为本群最强{role_name}!\n")
                else:
                    return f"你仍然是本群最强{role_name}!\n"
            else:
                return f"距本群最强{role_name}还有{round(float(role_info[0]) - score, 2)}分差距!\n"
    return ""


def check_uid(uid: int):
    return re.search(r'^[12589]\d{8}$', str(uid)) is not None


@driver.on_bot_connect
@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def check_update():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_info/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        return
    if float(version.group(1)) > __plugin_version__:
        for admin in bot.config.superusers:
            await bot.send_private_msg(user_id=int(admin),
                                       message=f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
        logger.warning(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")

# @trans_data.handle()
# async def _():
#    json_data = os.listdir(GENSHIN_CARD_PATH + f"/player_info_old/")
#    for item in json_data:
#        try:
#            uid = os.path.basename(item).split('.')[0]
#            print(item)
#            data = load_json(GENSHIN_CARD_PATH + f"/player_info_old/" + item)
#            player_info = PlayerInfo(uid)
#            player_info.set_player(data['playerInfo'])
#            if 'avatarInfoList' in data:
#                for role in data['avatarInfoList']:
#                    player_info.set_role(role)
#            player_info.save()
#        except Exception as e:
#            print(e)
