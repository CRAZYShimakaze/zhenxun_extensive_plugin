# -*- coding: utf-8 -*-
import random
import re
from typing import Tuple

import nonebot
from nonebot import Driver
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from nonebot.params import CommandArg, RegexGroup

from plugins.genshin.query_user._models import Genshin
from services.log import logger
from utils.http_utils import AsyncHttpx
from utils.utils import get_bot, scheduler, get_message_at
from .data_source import get_alc_image, get_char_list

driver: Driver = nonebot.get_driver()

__zx_plugin_name__ = "原神角色卡"
__plugin_usage__ = """
usage：
    查询橱窗内角色的面板
    指令：
        原神角色卡 uid
        原神角色卡 uid 角色名
        角色面板 ?[@用户] (例:刻晴面板)
""".strip()
__plugin_des__ = "查询橱窗内角色的面板"
__plugin_cmd__ = ["原神角色卡 [uid] ?[角色名]"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 2.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["原神角色卡"],
}
get_card = on_regex(r".*?(.*)面板(.*).*?", priority=4)
char_card = on_command("原神角色卡", priority=4, block=True)
characters = {
    '钟离': 'zhongli',
    '神里绫华': 'ayaka',
    '胡桃': 'hutao',
    '甘雨': 'ganyu',
    '雷电将军': 'shougun',
    '温迪': 'venti',
    '达达利亚': 'tartaglia',
    '夜兰': 'yelan',
    '七七': 'qiqi',
    '优菈': 'eula',
    '八重神子': 'yae',
    '可莉': 'klee',
    '宵宫': 'yoimiya',
    '枫原万叶': 'kazuha',
    '珊瑚宫心海': 'kokomi',
    '申鹤': 'shenhe',
    '荒泷一斗': 'itto',
    '莫娜': 'mona',
    '迪卢克': 'diluc',
    '阿贝多': 'albedo',
    '魈': 'xiao',
    '神里绫人': 'ayato',
    '刻晴': 'keqing',
    '琴': 'qinc',
    '凝光': 'ningguang',
    '香菱': 'xiangling',
    '烟绯': 'feiyan',
    '重云': 'chongyun',
    '班尼特': 'bennett',
    '九条裟罗': 'sara',
    '砂糖': 'sucrose',
    '诺艾尔': 'noel',
    '迪奥娜': 'diona',
    '芭芭拉': 'barbara',
    '早柚': 'sayu',
    '安柏': 'ambor',
    '埃洛伊': 'aloy',
    '云堇': 'yunjin',
    '罗莎莉亚': 'rosaria',
    '凯亚': 'kaeya',
    '北斗': 'beidou',
    '雷泽': 'razor',
    '行秋': 'xingqiu',
    '丽莎': 'lisa',
    '托马': 'tohma',
    '辛焱': 'xinyan',
    '久岐忍': 'shinobu',
    '五郎': 'gorou',
    '菲谢尔': 'fischl',
    '鹿野院平藏': 'heizo',
    '柯莱': 'collei',
    '提纳里': 'tighnari'
}


# char_occupy = False


@get_card.handle()
# async def _(bot: Bot, event: MessageEvent):
#     city = get_msg(event.get_plaintext())
async def _(event: MessageEvent, args: Tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    at = args[1].strip()
    if at:
        uid = await Genshin.get_user_uid(get_message_at(event.json())[0])
    else:
        uid = await Genshin.get_user_uid(event.user_id)
    if not uid:
        await get_card.finish("请输入原神绑定uid+uid进行绑定后再查询！")
    await gen(event, [str(uid), role])


@char_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    await gen(event, msg)


async def gen(event: MessageEvent, msg: list):
    # global char_occupy
    try:
        # if char_occupy:
        # await char_card.finish("当前正有角色正在查询,请稍后再试...")
        # char_occupy = True
        # msg = arg.extract_plain_text().strip().split()
        # print(msg)
        try:
            uid = int(msg[0])
        except:
            await char_card.send("请输入正确uid...")
            # char_occupy = False
            return
        if len(str(uid)) != 9:
            await char_card.send("请输入正确uid...")
            # char_occupy = False
            return
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
        if len(msg) == 2:
            if msg[1] in characters:
                chara = characters[msg[1]]
                await char_card.send("开始获取角色信息...")
            else:
                await char_card.send("请输入正确角色名...")
                # char_occupy = False
                return
        else:
            chara = 'none'
            await char_card.send("未指定角色,默认橱窗第一位...")
        char_list, page = await get_char_list(str(uid))
        logger.info(f"角色获取完成！{char_list}")
        if char_list is not None:
            char_hanzi = []
            char_lower = [item.lower() for item in char_list]
            for item in characters.keys():
                for tar in char_lower:
                    if characters[item] in tar:
                        char_hanzi.append(item)
                        break
        else:
            # char_occupy = False
            await char_card.send(f"获取UID({str(uid)})角色信息超时,请检查是否已开放详细信息权限！",
                                 at_sender=True)
            return
        alc_img = await get_alc_image(str(uid), chara, page, char_list)
        logger.info(f"角色卡获取完成！")
        if alc_img:
            mes = alc_img + f"\n可查询角色:{','.join(char_hanzi)}"
            await char_card.send(mes, at_sender=True)
            # char_occupy = False
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 发送原神角色卡")
        else:
            await char_card.send(
                f"获取UID({str(uid)})角色信息失败,请检查是否已放入指定角色!\n可查询角色:{','.join(char_hanzi)}",
                at_sender=True)
            # char_occupy = False
        # try:
        #    version = await check_update()
        #    if float(version) > __plugin_version__ and version != '':
        #        logger.info(
        #            f"[genshin_role_card]发现插件版本更新{version}!请前往github项目获取更新！")
        # except Exception as e:
        #    logger.warning(f"{e}")
    except Exception as e:
        # char_occupy = False
        # await char_card.send(f"获取UID({str(uid)})角色信息失败!", at_sender=True)
        print(e)


@driver.on_bot_connect
@scheduler.scheduled_job(
    "cron",
    hour=random.randint(9, 22),
    minute=random.randint(0, 59),
)
async def check_update():
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_card/__init__.py"
    bot = get_bot()
    try:
        version = await AsyncHttpx.get(url)
        version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                            str(version.text))
    except Exception as e:
        logger.warning(f"原神角色卡插件检查更新失败，请检查github连接性是否良好!: {e}")
        url = "https://ghproxy.com/https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main" \
              "/genshin_role_card/__init__.py "
        try:
            version = await AsyncHttpx.get(url)
            version = re.search(r"__plugin_version__ = ([0-9.]{3})",
                                str(version.text))
        except Exception as e:
            for admin in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(admin),
                    message="原神角色卡插件检查更新失败，请检查github连接性是否良好!")
            logger.warning(f"原神角色卡插件检查更新失败，请检查github连接性是否良好!: {e}")
            return
    if float(version.group(1)) > __plugin_version__:
        for admin in bot.config.superusers:
            await bot.send_private_msg(user_id=int(admin),
                                       message="检测到原神角色卡插件有更新！请前往github下载！")
        logger.warning("检测到原神角色卡插件有更新！请前往github下载！")
