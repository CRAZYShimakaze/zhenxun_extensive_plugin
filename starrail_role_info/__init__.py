# -*- coding: utf-8 -*-
import copy
import os
import random
import re
import shutil
import time
from pathlib import Path
from typing import Tuple

import nonebot
from configs.config import Config
from nonebot import Driver
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent
from nonebot.params import CommandArg, RegexGroup
from nonebot.permission import SUPERUSER
from services.log import logger

from utils.http_utils import AsyncHttpx
from utils.message_builder import at
from utils.utils import get_bot, scheduler, get_message_at
from .data_source.draw_artifact_card import draw_artifact_card
from .data_source.draw_recommend_card import gen_artifact_recommend
from .data_source.draw_role_card import draw_role_card
from .data_source.draw_update_card import draw_role_pic
from .utils.card_utils import load_json, save_json, player_info_path, PlayerInfo, json_path, other_path, get_name_by_id, \
    group_info_path
from .utils.image_utils import load_image, image_build
#from ..plugin_utils.auth_utils import check_gold

__zx_plugin_name__ = "星铁角色面板"
__plugin_usage__ = """
usage：
    查询角色的面板
    指令：
        星铁绑定uidXXXX
        星铁解绑
        角色面板 (例:希儿面板、希儿面板@XXX、希儿面板+uid)
        更新/刷新星铁面板 (uid)
        XX(头手身脚球绳)推荐
        我的星铁角色
        他的星铁角色@XXX
        最强XX (例:最强希儿)
        最菜XX
        遗器榜单
        群遗器榜单
""".strip()
__plugin_des__ = "查询橱窗内角色的面板"
__plugin_cmd__ = ["星铁角色面板", "更新角色面板", "我的角色", "他的角色", "XX面板", "最强XX", "最菜XX", "遗器榜单",
                  "群遗器榜单"]
__plugin_type__ = ("星铁相关",)
__plugin_version__ = 0.4
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

Config.add_plugin_config(
    "startail_role_info",
    "CHECK_UPDATE",
    True,
    help_="定期自动检查更新",
    default_value=True,
)
Config.add_plugin_config(
    "startail_role_info",
    "ALPHA",
    83,
    help_="群榜单背景透明度",
    default_value=83,
)
starrail_url = 'https://api.mihomo.me/sr_info/{}'

my_card = on_command("我的星铁角色", priority=4, block=True)
his_card = on_command("他的星铁角色", aliases={"她的星铁角色"}, priority=4, block=True)

bind = on_regex(r"(星铁绑定|绑定星铁)(UID|uid)(.*)", priority=5, block=True)
unbind = on_command("星铁解绑", priority=4, block=True)

driver: Driver = nonebot.get_driver()

get_card = on_regex(r"(.*)面板(.*)", priority=4)
group_best = on_regex(r"最强(.*)", priority=4)
group_worst = on_regex(r"最菜(.*)", priority=4)

artifact_recommend = on_regex("(.*?)([头手身脚球绳])推荐", priority=4)
artifact_list = on_command("遗器榜单", aliases={"遗器排行"}, priority=4, block=True)
group_artifact_list = on_command("群遗器榜单", aliases={"群遗器排行"}, priority=4, block=True)
reset_best = on_command("重置最强", permission=SUPERUSER, priority=3, block=False)
check_update = on_command("检查星铁面板更新", permission=SUPERUSER, priority=3, block=True)
alias_file = load_json(f'{json_path}/nickname.json')
name_list = alias_file['characters']


def get_role_name(role):
    role_name = ''
    for nicknames in name_list.values():
        if role in nicknames:
            role_name = nicknames[0]
            break
    return role_name


def get_uid(user_qq):
    qq2uid = load_json(f'{player_info_path}/qq2uid.json')
    return qq2uid.get(str(user_qq), '')


def bind_uid(user_qq, uid):
    qq2uid = load_json(f'{player_info_path}/qq2uid.json')
    qq2uid[str(user_qq)] = uid
    save_json(qq2uid, f"{player_info_path}/qq2uid.json")


def unbind_uid(user_qq):
    qq2uid = load_json(f'{player_info_path}/qq2uid.json')
    qq2uid.pop(str(user_qq))
    save_json(qq2uid, f"{player_info_path}/qq2uid.json")


async def get_msg_uid(event):
    at_user = get_message_at(event.json())
    user_qq = at_user[0] if at_user else event.user_id
    uid = get_uid(user_qq)
    if not uid:
        await artifact_list.finish("请绑定星铁uid后再查询！")
    if not check_uid(uid):
        await artifact_list.finish(f"绑定的uid{uid}不合法，请重新绑定!")
    return uid


async def get_starrail_info(url, uid, update_info):
    update_role_list = []
    if not os.path.exists(f"{player_info_path}/{uid}.json") or update_info:
        try:
            req = await AsyncHttpx.get(
                url=url,
                follow_redirects=True,
            )
        except Exception:
            return await get_card.finish("获取数据出错,请重试...")
        if req.status_code != 200:
            return await get_card.finish("服务器维护中,请稍后再试...")
        data = req.json()
        player_info = PlayerInfo(uid)
        if 'avatarDetailList' in data['detailInfo'] or 'assistAvatarDetail' in data['detailInfo']:
            player_info.set_player(data['detailInfo'])
            detail = []
            if 'avatarDetailList' in data['detailInfo']:
                detail += data['detailInfo'].get('avatarDetailList')
            if 'assistAvatarDetail' in data['detailInfo']:
                if data['detailInfo']['assistAvatarDetail']['avatarId'] not in [item['avatarId'] for item in detail]:
                    detail.append(data['detailInfo'].get('assistAvatarDetail'))
            for role in detail:
                try:
                    player_info.set_role(role)
                    update_role_list.append(get_name_by_id(str(role['avatarId'])))
                except Exception as e:
                    await get_card.send(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")
            player_info.save()
        else:
            guide = load_image(f'{other_path}/collections.png')
            guide = image_build(img=guide, quality=100, mode='RGB')
            return await get_card.finish(guide + "在游戏中打开显示详情选项!")
    else:
        player_info = PlayerInfo(uid)
    return player_info, update_role_list


async def check_artifact(event, player_info, uid, group_save):
    roles_list = player_info.get_roles_list()
    player_info.data['遗器榜单'] = []
    player_info.data['大毕业遗器'] = 0
    player_info.data['小毕业遗器'] = 0
    for role_name in roles_list:
        role_data = player_info.get_roles_info(role_name)
        _, _ = await draw_role_card(uid, role_data, player_info, __plugin_version__, only_cal=True)
    player_info.save()
    if group_save and isinstance(event, GroupMessageEvent):
        check_group_artifact(event, player_info)


async def check_role_avaliable(role_name, roles_list):
    if not roles_list:
        guide = load_image(f'{other_path}/collections.png')
        guide = image_build(img=guide, quality=100, mode='RGB')
        await his_card.finish(guide + "无角色信息,在游戏中将角色放入漫游签证并输入更新星铁面板XXXX(uid)!",
                              at_sender=True)
    if role_name not in roles_list:
        await get_card.finish(
            f"漫游签证里没有{role_name}的信息哦!可查询:{','.join(roles_list)}",
            at_sender=True)


@bind.handle()
async def _(event: MessageEvent, arg: Tuple[str, ...] = RegexGroup()):
    cmd = arg[1].strip()
    msg = arg[2].strip()
    uid = get_uid(event.user_id)
    if not msg.isdigit():
        await bind.finish("uid/id必须为纯数字！", at_senders=True)
    msg = int(msg)
    if uid:
        await bind.finish(f"您已绑定过uid：{uid}，如果希望更换uid，请先发送星铁解绑")
    else:
        bind_uid(event.user_id, msg)
        await bind.finish(f"已成功添加星铁uid：{msg}")


@unbind.handle()
async def _(event: MessageEvent):
    if get_uid(event.user_id):
        unbind_uid(event.user_id)
        await unbind.send("用户数据删除成功...")


@artifact_recommend.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    msg = args[0].strip(), args[1].strip()
    uid = await get_msg_uid(event)
    if len(msg) != 2:
        return await artifact_recommend.send("请输入正确角色名和遗器位置序号(头手身脚球绳)...", at_sender=True)
    role = msg[0]
    pos = ["头", "手", "身", "脚", "球", "绳"].index(msg[1])
    role_name = get_role_name(role)
    if not role_name:
        return
    url = starrail_url.format(uid)
    player_info, _ = await get_starrail_info(url, uid, update_info=False)
    #await check_gold(event, coin=10, percent=1)
    artifact_list = player_info.get_artifact_list(pos)

    if not artifact_list:
        return await artifact_recommend.send(f"{pos}号位没有遗器缓存！", at_sender=True)
    roles_list = player_info.get_roles_list()
    await check_role_avaliable(role_name, roles_list)
    role_data = player_info.get_roles_info(role_name)
    img, _ = await gen_artifact_recommend(f'{role}{msg[1]}遗器推荐', role_data, artifact_list, uid, role, pos, __plugin_version__)
    await artifact_recommend.finish(img)


@group_artifact_list.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    if not os.path.exists(f"{group_info_path}/{group_id}.json"):
        return await group_artifact_list.finish('未收录任何遗器信息,请先进行查询!')
    else:
        #await check_gold(event, coin=1, percent=1)
        group_artifact_info = load_json(f"{group_info_path}/{group_id}.json")
        img, _ = await draw_artifact_card(f'群遗器榜单', group_id, group_artifact_info, None, None,
                                          __plugin_version__, 1)
        await group_artifact_list.finish(img)


@artifact_list.handle()
async def _(event: MessageEvent):
    uid = await get_msg_uid(event)
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        return await artifact_list.finish('未收录任何角色信息,请先进行角色查询!', at_sender=True)
    else:
        player_info = PlayerInfo(uid)
        if not player_info.data['遗器榜单']:
            return await artifact_list.send("未收录任何遗器信息,请先输入'更新面板'命令!", at_sender=True)
        roles_list = player_info.get_roles_list()
        #await check_gold(event, coin=1, percent=1)
        img, text = await draw_artifact_card(f'遗器榜单', None, uid, player_info.data['遗器榜单'],
        img, text = await draw_artifact_card(f'遗器榜单', uid, player_info.data['遗器榜单'],
                                             player_info.data['大毕业遗器'],
                                             player_info.data['小毕业遗器'], __plugin_version__)
        await artifact_list.finish(img + text, at_sender=True)  # + f"\n数据来源:{','.join(roles_list)}", at_sender=True)


@get_card.handle()
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    at_user = args[1].strip()
    if role not in ["更新星铁", "刷新星铁"]:
        role = get_role_name(role)
    if not role:
        return
    if at_user.isdigit():
        uid = int(at_user)
    else:
        uid = await get_msg_uid(event)
    if role in ["更新星铁", "刷新星铁"]:
        if at_user:
            await update(event, uid, group_save=False)
        else:
            await update(event, uid, group_save=True)
    else:
        await gen(event, uid, role, at_user=at_user)


@group_best.handle()
async def _(event: GroupMessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f'{group_info_path}/{event.group_id}/{role}'
    if not os.path.exists(role_path):
        await group_best.finish(f"本群还没有{role}的数据收录哦！赶快去查询吧！", at_sender=True)
    else:
        role_list = os.listdir(role_path)
        if '@eaDir' in role_list:
            role_list.remove('@eaDir')
        data = sorted(role_list, key=lambda x: float(x.split('-')[0]))
        role_info = data[-1]
        role_pic = load_image(f'{role_path}/{role_info}')
        role_pic = image_build(img=role_pic, quality=100, mode='RGB')
        bot = get_bot()
        qq_name = await bot.get_stranger_info(user_id=int(role_info.split('-')[-1].rstrip('.png')))
        qq_name = qq_name["nickname"]
        await group_best.finish(f"本群最强{role}!仅根据遗器评分评判.\n由'{qq_name}'查询\n" + role_pic)


@group_worst.handle()
async def _(event: GroupMessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f'{group_info_path}/{event.group_id}/{role}'
    if not os.path.exists(role_path) or len(os.listdir(role_path)) < 2:
        await group_worst.finish(f"本群还没有最菜{role}的数据收录哦！赶快去查询吧！", at_sender=True)
    else:
        data = sorted(os.listdir(role_path), key=lambda x: float(x.split('-')[0]))
        role_info = data[0]
        role_pic = load_image(f'{role_path}/{role_info}')
        role_pic = image_build(img=role_pic, quality=100, mode='RGB')
        bot = get_bot()
        qq_name = await bot.get_stranger_info(user_id=int(role_info.split('-')[-1].rstrip('.png')))
        qq_name = qq_name["nickname"]
        await group_worst.finish(f"本群最菜{role}!仅根据遗器评分评判.\n由'{qq_name}'查询\n" + role_pic)


@reset_best.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    role = arg.extract_plain_text().strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f'{group_info_path}/{event.group_id}/{role}'
    shutil.rmtree(role_path, ignore_errors=True)
    await reset_best.finish(f'重置群{role}成功!')


@my_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg:
        return
    uid = await get_msg_uid(event)
    await get_char(uid)


async def get_char(uid):
    url = starrail_url.format(uid)
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        try:
            req = await AsyncHttpx.get(url=url, follow_redirects=True)
        except Exception as e:
            print(e)
            return await get_card.finish("更新出错,请重试...")
        if req.status_code != 200:
            return await get_card.finish("服务器维护中,请稍后再试...")
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
                await get_card.finish(guide + "在游戏中打开显示详情选项!", at_sender=True)
        except Exception as e:
            print(e)
            return  # await char_card.finish("发生错误，请尝试更新命令！", at_sender=True)
    else:
        player_info = PlayerInfo(uid)
    roles_list = player_info.get_roles_list()
    if not roles_list:
        guide = load_image(f'{other_path}/collections.png')
        guide = image_build(img=guide, quality=100, mode='RGB')
        await get_card.finish(guide + "无角色信息,在游戏中将角色放入漫游签证并输入更新星铁面板XXXX(uid)",
                              at_sender=True)
    else:
        await my_card.finish(await draw_role_pic(uid, roles_list, player_info),
                             at_sender=True)


@his_card.handle()
async def _(event: MessageEvent):
    uid = await get_msg_uid(event)
    await get_char(uid)


async def gen(event: MessageEvent, uid, role_name, at_user):
    url = starrail_url.format(uid)
    player_info, _ = await get_starrail_info(url, uid, update_info=False)
    roles_list = player_info.get_roles_list()
    await check_role_avaliable(role_name, roles_list)
    #await check_gold(event, coin=1, percent=1)
    role_data = player_info.get_roles_info(role_name)
    img, score = await draw_role_card(uid, role_data, player_info, __plugin_version__, only_cal=False)
    msg = '' if at_user else check_role(role_name, event, img, score)
    img = image_build(img=img, quality=100, mode='RGB')
    await get_card.finish(msg + img, at_sender=True)


async def update(event, uid, group_save):
    url = starrail_url.format(uid)
    if os.path.exists(f'{player_info_path}/{uid}.json'):
        mod_time = os.path.getmtime(f'{player_info_path}/{uid}.json')
        cd_time = int(time.time() - mod_time)
        if cd_time < 130:
            await get_card.finish(f'{130 - cd_time}秒后可再次更新!', at_sender=True)
    player_info, update_role_list = await get_starrail_info(url, uid, update_info=True)
    #await check_gold(event, coin=1, percent=1)
    await check_artifact(event, player_info, uid, group_save)
    await get_card.finish(await draw_role_pic(uid, update_role_list, player_info))


def check_role(role_name, event, img, score):
    print(score)
    if isinstance(event, GroupMessageEvent) and str(score)[-1] != '*':
        role_path = f'{group_info_path}/{event.group_id}/{role_name}/{score}-{event.user_id}.png'
        role_path = Path(role_path)
        role_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.listdir(role_path.parent):
            img.save(role_path)
            return f"恭喜成为本群最强{role_name}!\n"
        else:
            data = sorted(os.listdir(role_path.parent), key=lambda x: float(x.split('-')[0]))
            role_info_best = data[-1].split('-')
            if len(os.listdir(role_path.parent)) == 1:
                img.save(role_path)
                if float(role_info_best[0]) <= score:
                    old_best = int(role_info_best[1].rstrip('.png'))
                    if old_best != event.user_id:
                        return Message(f"恭喜你击败{at(old_best)}成为本群最强{role_name}!\n")
                    else:
                        return f"你仍然是本群最强{role_name}!\n"
                else:
                    return f"恭喜你成为本群最菜{role_name}!\n距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
            else:
                if float(role_info_best[0]) <= score:
                    os.unlink(f'{role_path.parent}/{data[-1]}')
                    img.save(role_path)
                    old_best = int(role_info_best[1].rstrip('.png'))
                    if old_best != event.user_id:
                        return Message(f"恭喜你击败{at(old_best)}成为本群最强{role_name}!\n")
                    else:
                        return f"你仍然是本群最强{role_name}!\n"
                else:
                    role_info_worst = data[0].split('-')
                    if float(role_info_worst[0]) >= score:
                        os.unlink(f'{role_path.parent}/{data[0]}')
                        img.save(role_path)
                        old_worst = int(role_info_worst[1].rstrip('.png'))
                        if old_worst != event.user_id:
                            return Message(f"恭喜你帮助{at(old_worst)}摆脱最菜{role_name}的头衔!\n")
                        else:
                            return f"你仍然是本群最菜{role_name}!\n距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
                    else:
                        return f"距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
    return ""


def check_group_artifact(event, player_info):
    if not os.path.exists(f"{group_info_path}/{event.group_id}.json"):
        group_artifact_info = []
    else:
        group_artifact_info = load_json(f"{group_info_path}/{event.group_id}.json")
    group_player_info = copy.deepcopy(player_info.data['遗器榜单'])
    for item in group_player_info:
        item['QQ'] = event.user_id
        if item not in group_artifact_info:
            group_artifact_info.append(item)
    group_artifact_info_20 = sorted(group_artifact_info, key=lambda x: float(x['评分']), reverse=True)[:20]
    save_json(group_artifact_info_20, f"{group_info_path}/{event.group_id}.json")


def check_uid(uid: int):
    return re.search(r'^[12589]\d{8}$', str(uid)) is not None


async def get_update_info():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_role_info/README.md"
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r"\*\*\[v\d.\d]((?:.|\n)*?)\*\*", str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件获取更新内容失败，请检查github连接性是否良好!: {e}")
        return ''
    return version.group(1).strip()


@check_update.handle()
async def _check_update():
    url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_role_info/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        return
    if float(version.group(1)) > __plugin_version__:
        update_info = await get_update_info()
        try:
            await check_update.send(
                f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{update_info}")
        except Exception:
            for admin in bot.config.superusers:
                await bot.send_private_msg(user_id=int(admin),
                                           message=f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{update_info}")
            logger.warning(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
    else:
        update_info = await get_update_info()
        try:
            await check_update.send(
                f"{__zx_plugin_name__}插件已经是最新V{__plugin_version__}！最近一次的更新内容如下:\n{update_info}")
        except Exception:
            pass


@driver.on_startup
async def _():
    if Config.get_config("starrail_role_info", "CHECK_UPDATE"):
        scheduler.add_job(_check_update, "cron", hour=random.randint(9, 22), minute=random.randint(0, 59),
                          id='starrail_role_info')
