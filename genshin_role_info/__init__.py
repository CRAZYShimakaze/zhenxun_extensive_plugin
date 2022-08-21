# -*- coding: utf-8 -*-
from .utils.card_utils import *
from .data_source.draw_role_card import draw_role_card
from curses.ascii import isdigit
from utils.utils import get_bot, scheduler, get_message_at
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from services.log import logger
from nonebot.params import CommandArg, RegexGroup
from utils.manager import group_manager
from configs.config import Config
from utils.http_utils import AsyncHttpx
import os
import time
import datetime
import nonebot
import requests
from nonebot import Driver
from plugins.genshin.query_user._models import Genshin

__zx_plugin_name__ = "原神角色面板"
__plugin_usage__ = """
usage：
    查询橱窗内角色的面板
    指令：
        原神角色卡 uid 角色名
        更新角色卡 uid
        角色面板 (例:刻晴面板)
        更新面板
        我的角色
        他的角色
""".strip()
__plugin_des__ = "查询橱窗内角色的面板"
__plugin_cmd__ = ["原神角色面板", "更新角色面板", "我的角色", "他的角色", "XX面板"]
__plugin_type__ = ("原神相关", )
__plugin_version__ = 0.5
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
his_card = on_command("他的角色", priority=4, block=True)

driver: Driver = nonebot.get_driver()

get_card = on_regex(r".*?(.*)面板(.*).*?", priority=1)
alias_file = load_json(path=GENSHIN_CARD_PATH + '/json_data' + '/alias.json')
name_list = alias_file['roles']


@get_card.handle()
# async def _(bot: Bot, event: MessageEvent):
#     city = get_msg(event.get_plaintext())
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    at = args[1].strip()
    if role != "更新":
        for item in name_list:
            if role in name_list.get(item):
                role = name_list.get(item)[0]
                break
        else:
            return
    if at:
        uid = await Genshin.get_user_uid(get_message_at(event.json())[0])
    else:
        uid = await Genshin.get_user_uid(event.user_id)
    if not uid:
        await get_card.finish("请输入原神绑定uid+uid进行绑定后再查询！")
    if role == "更新":
        await update(event, str(uid))
    else:
        await gen(event, str(uid), role)


@my_card.handle()
# async def _(bot: Bot, event: MessageEvent):
#     city = get_msg(event.get_plaintext())
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg:
        return
    uid = await Genshin.get_user_uid(event.user_id)
    if not uid:
        await my_card.finish("请输入原神绑定uid+uid进行绑定后再查询！")
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if not os.path.exists(GENSHIN_CARD_PATH + f"/player_info/{uid}.json"):
        try:
            req = await AsyncHttpx.get(
                url=url,
                follow_redirects=True,
            )
            data = req.json()
            player_info = PlayerInfo(uid)
            player_info.set_player(data['playerInfo'])
        except:
            await my_card.finish("服务器维护中,请稍后再试...")
        if 'avatarInfoList' in data:
            for role in data['avatarInfoList']:
                player_info.set_role(role)
        else:
            guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
            guide = Image_build(img=guide, quality=100, mode='RGB')
            await my_card.finish(guide + f"在游戏中打开显示详情选项!", at_sender=True)
        player_info.save()
    else:
        #data = load_json(GENSHIN_CARD_PATH + '/player_info' + f'/{uid}.json')
        player_info = PlayerInfo(uid)
        #player_info.set_player(data['playerInfo'])
        #if 'avatarInfoList' in data:
        #    for role in data['avatarInfoList']:
        #        player_info.set_role(role)
        #else:
        #    guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
        #    guide = Image_build(img=guide, quality=100, mode='RGB')
        #    await my_card.finish(guide + f"在游戏中打开显示详情选项并输入更新角色卡指令!",
        #                         at_sender=True)
    roles_list = player_info.get_roles_list()
    if roles_list == []:
        guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
        guide = Image_build(img=guide, quality=100, mode='RGB')
        await my_card.finish(guide + f"无角色信息,在游戏中打开显示详情选项并输入更新角色卡指令!",
                             at_sender=True)
    else:
        await my_card.finish(f"uid{uid}的角色:{','.join(roles_list)}",
                             at_sender=True)


@his_card.handle()
# async def _(bot: Bot, event: MessageEvent):
#     city = get_msg(event.get_plaintext())
async def _(event: MessageEvent, arg: Message = CommandArg()):
    uid = await Genshin.get_user_uid(get_message_at(event.json())[0])
    if not uid:
        await his_card.finish("请输入原神绑定uid+uid进行绑定后再查询！")
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if not os.path.exists(GENSHIN_CARD_PATH + f"/player_info/{uid}.json"):
        try:
            req = await AsyncHttpx.get(
                url=url,
                follow_redirects=True,
            )
            data = req.json()
            player_info = PlayerInfo(uid)
            player_info.set_player(data['playerInfo'])
        except:
            await his_card.finish("服务器维护中,请稍后再试...")
        if 'avatarInfoList' in data:
            for role in data['avatarInfoList']:
                player_info.set_role(role)
        else:
            await his_card.finish(f"未打开显示详情选项!", at_sender=True)
        player_info.save()
    else:
        #data = load_json(GENSHIN_CARD_PATH + '/player_info' + f'/{uid}.json')
        player_info = PlayerInfo(uid)
        #player_info.set_player(data['playerInfo'])
        #if 'avatarInfoList' in data:
        #    for role in data['avatarInfoList']:
        #        player_info.set_role(role)
        #else:
        #    await his_card.finish(f"未打开显示详情选项!", at_sender=True)
    roles_list = player_info.get_roles_list()
    if roles_list == []:
        guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
        guide = Image_build(img=guide, quality=100, mode='RGB')
        await his_card.finish(guide + f"无角色信息,在游戏中打开显示详情选项并输入更新角色卡指令!",
                              at_sender=True)
    else:
        await his_card.finish(f"uid{uid}的角色:{','.join(roles_list)}",
                              at_sender=True)


@char_card.handle()
#@driver.on_startup
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    try:
        uid = int(msg[0])
    except:
        await char_card.finish("请输入正确uid(uid与角色名需要用空格隔开)", at_sender=True)
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


async def gen(event: MessageEvent, uid: str, role_name: str):
    while 0:
        if str(uid)[0] in ["1", "2"]:
            service_dic = "官服"
            break
        elif str(uid)[0] in ["5"]:
            service_dic = "B服"
            break
        elif str(uid)[0] in ["6"]:
            service_dic = "美服"
        elif str(uid)[0] in ["7"]:
            service_dic = "欧服"
        elif str(uid)[0] in ["8"]:
            service_dic = "亚服"
        elif str(uid)[0] in ["9"]:
            service_dic = "港澳服"
        else:
            service_dic = ""
        await char_card.finish(f"暂不支持{service_dic}查询...", at_sender=True)
    #await char_card.send("正在获取角色数据...")
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if not os.path.exists(GENSHIN_CARD_PATH + f"/player_info/{uid}.json"):
        try:
            req = await AsyncHttpx.get(
                url=url,
                follow_redirects=True,
            )
        except:
            await char_card.finish("服务器维护中,请稍后再试...")
        data = req.json()
        player_info = PlayerInfo(uid)
        try:
            player_info.set_player(data['playerInfo'])
            if 'avatarInfoList' in data:
                for role in data['avatarInfoList']:
                    player_info.set_role(role)
            else:
                guide = load_image(GENSHIN_CARD_PATH +
                                   '/other/collections.png')
                guide = Image_build(img=guide, quality=100, mode='RGB')
                await char_card.finish(guide + f"在游戏中打开显示详情选项!",
                                       at_sender=True)
            player_info.save()
        except:
            return  #await char_card.finish("发生错误，请尝试更新命令！", at_sender=True)
    else:
        #data = load_json(GENSHIN_CARD_PATH + f"/player_info/{uid}.json")
        player_info = PlayerInfo(uid)
        #try:
        #    player_info.set_player(data['playerInfo'])
        #    if 'avatarInfoList' in data:
        #        for role in data['avatarInfoList']:
        #            player_info.set_role(role)
        #    else:
        #        guide = load_image(GENSHIN_CARD_PATH +
        #                           '/other/collections.png')
        #        guide = Image_build(img=guide, quality=100, mode='RGB')
        #        await char_card.finish(guide + f"在游戏中打开显示详情选项并输入更新角色卡指令!",
        #                               at_sender=True)
        #except:
        #    return  #await char_card.finish("发生错误，请尝试更新命令！", at_sender=True)
    roles_list = player_info.get_roles_list()
    if roles_list == []:
        guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
        guide = Image_build(img=guide, quality=100, mode='RGB')
        await his_card.finish(guide + f"无角色信息,在游戏中打开显示详情选项并输入更新角色卡指令!",
                              at_sender=True)
    if role_name not in roles_list:
        await char_card.finish(
            f"角色展柜里没有{role_name}的信息哦!可查询:{','.join(roles_list)}",
            at_sender=True)
    else:
        role_data = player_info.get_roles_info(role_name)
        img = await draw_role_card(uid, role_data)
        await char_card.finish(f"\n" + img + f"\n可查询角色:{','.join(roles_list)}",
                               at_sender=True)


@update_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    try:
        uid = int(msg)
    except:
        await char_card.finish("请输入正确uid...", at_sender=True)
    await update(event, uid)


async def update(event: MessageEvent, uid: str):
    while 0:
        if str(uid)[0] in ["1", "2"]:
            service_dic = "官服"
            break
        elif str(uid)[0] in ["5"]:
            service_dic = "B服"
            break
        elif str(uid)[0] in ["6"]:
            service_dic = "美服"
        elif str(uid)[0] in ["7"]:
            service_dic = "欧服"
        elif str(uid)[0] in ["8"]:
            service_dic = "亚服"
        elif str(uid)[0] in ["9"]:
            service_dic = "港澳服"
        else:
            service_dic = ""
        await char_card.finish(f"暂不支持{service_dic}查询...", at_sender=True)
    #await char_card.send(f"正在更新uid{uid}的角色数据...")
    url = f'https://enka.shinshin.moe/u/{uid}/__data.json'
    if os.path.exists(GENSHIN_CARD_PATH + '/player_info' + f'/{uid}.json'):
        mod_time = os.path.getmtime(GENSHIN_CARD_PATH +
                                    f"/player_info/{uid}.json")
        cd_time = int(time.time() - mod_time)
        if cd_time < 180:
            await char_card.finish(f'{180 - cd_time}秒后可再次更新!', at_sender=True)
    try:
        req = await AsyncHttpx.get(
            url=url,
            follow_redirects=True,
        )
    except:
        await char_card.finish("服务器维护中，,请稍后再试...")
    data = req.json()
    player_info = PlayerInfo(uid)
    try:
        player_info.set_player(data['playerInfo'])
        if 'avatarInfoList' in data:
            for role in data['avatarInfoList']:
                player_info.set_role(role)
        else:
            guide = load_image(GENSHIN_CARD_PATH + '/other/collections.png')
            guide = Image_build(img=guide, quality=100, mode='RGB')
            await char_card.finish(guide + f"在游戏中打开显示详情选项!", at_sender=True)
    except Exception as e:
        print(e)
        pass  #await char_card.finish("发生错误，请重试！", at_sender=True)
    player_info.save()
    roles_list = player_info.get_roles_list()
    await char_card.finish(
        f"更新uid{uid}的角色数据完成!可查询:{','.join(roles_list)}(注:数据更新有3分钟延迟)",
        at_sender=True)


#@driver.on_startup
@scheduler.scheduled_job(
    "cron",
    hour="*/1",
)
async def check_update():
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_info/__init__.py"
    try:
        version = requests.get(url)
        version = re.search(r"__plugin_version__ = ([0-9\.]{3})",
                            str(version._content))
    except Exception as e:
        logger.warning(f"检测到原神角色面板插件更新时出现问题: {e}")
    if version.group(1) != str(__plugin_version__):
        bot = get_bot()
        for admin in bot.config.superusers:
            await bot.send_private_msg(user_id=int(admin),
                                       message="检测到原神角色面板插件有更新！请前往github下载！")
        logger.warning(f"检测到原神角色面板插件有更新！请前往github下载！")


#@trans_data.handle()
#async def _():
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