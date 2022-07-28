# -*- coding: utf-8 -*-
from curses.ascii import isdigit
from utils.utils import get_bot, scheduler
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message
from services.log import logger
from configs.path_config import TEMP_PATH
from .data_source import get_alc_image, get_char_list
from nonebot.params import CommandArg
from utils.manager import group_manager
from configs.config import Config
from utils.http_utils import AsyncHttpx
import os

__zx_plugin_name__ = "原神角色卡"
__plugin_usage__ = """
usage：
    查询橱窗内角色的面板
    指令：
        原神角色卡 uid
        原神角色卡 uid 角色名
""".strip()
__plugin_des__ = "查询橱窗内角色的面板"
__plugin_cmd__ = ["原神角色卡 [uid] ?[角色名]"]
__plugin_type__ = ("原神相关", )
__plugin_version__ = 0.0
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["原神角色卡"],
}

char_card = on_command("原神角色卡", priority=15, block=True)
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
    '安柏': 'amber',
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
}
char_occupy = False


@char_card.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global char_occupy
    try:
        if char_occupy:
            await char_card.finish("当前正有角色正在查询,请稍后再试...")
        #char_occupy = True
        msg = arg.extract_plain_text().strip().split()
        #print(msg)
        try:
            uid = int(msg[0])
        except:
            await char_card.send("请输入正确uid...")
            #char_occupy = False
            return
        if len(msg) == 2:
            if msg[1] in characters:
                chara = characters[msg[1]]
                await char_card.send("开始获取角色信息...")
            else:
                await char_card.send("请输入正确角色名...")
                #char_occupy = False
                return
        else:
            chara = 'none'
            await char_card.send("未指定角色,默认橱窗第一位...")
        char_list, page = await get_char_list(str(uid))
        logger.info(f"角色获取完成！{char_list}")
        if char_list != None:
            char_hanzi = []
            char_lower = [item.lower() for item in char_list]
            for item in characters.keys():
                for tar in char_lower:
                    if characters[item] in tar:
                        char_hanzi.append(item)
                        break
        else:
            #char_occupy = False
            await char_card.send(f"获取UID({str(uid)})角色信息超时,请检查是否已开放详细信息权限！",
                                 at_sender=True)
            return
        alc_img = await get_alc_image(str(uid), chara, page, char_list)
        logger.info(f"角色卡获取完成！")
        if alc_img:
            mes = alc_img + f"\n可查询角色:{','.join(char_hanzi)}"
            await char_card.send(mes, at_sender=True)
            #char_occupy = False
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 发送原神角色卡")
        else:
            await char_card.send(
                f"获取UID({str(uid)})角色信息失败,请检查是否已放入指定角色!\n可查询角色:{','.join(char_hanzi)}",
                at_sender=True)
            #char_occupy = False
        #try:
        #    version = await check_update()
        #    if float(version) > __plugin_version__ and version != '':
        #        logger.info(
        #            f"[genshin_role_card]发现插件版本更新{version}!请前往github项目获取更新！")
        #except Exception as e:
        #    logger.warning(f"{e}")
    except Exception as e:
        #char_occupy = False
        #await char_card.send(f"获取UID({str(uid)})角色信息失败!", at_sender=True)
        print(e)


async def check_update() -> str:
    version_path = TEMP_PATH / '__version__'
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_card/__init__.py"
    try:
        await AsyncHttpx.download_file(url, version_path)
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
    with version_path.open("r", encoding="utf-8") as f:
        for item in f.readlines():
            if str(__plugin_version__) in item:
                new_version = item.split('=')[-1].strip()
                break
        else:
            new_version = '0.0'
    os.unlink(version_path)
    print(new_version)
    return new_version