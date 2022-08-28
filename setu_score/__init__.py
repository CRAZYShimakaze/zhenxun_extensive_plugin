import json
import os
import re

import nonebot
import requests
from nonebot import on_command, require
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, PokeNotifyEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.params import Arg, Depends
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.params import State, CommandArg
from utils.utils import get_message_img
from configs.config import NICKNAME, Config
#master = nonebot.get_driver().config.master

__zx_plugin_name__ = "色图打分"
__plugin_usage__ = """
usage：
    色图打分
    指令：
        评分+图片
""".strip()
__plugin_des__ = "色图打分"
__plugin_cmd__ = ["打分"]
__plugin_type__ = ("一些工具", )
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
Config.add_plugin_config(
    "setu_score",
    "API_KEY",
    "",
    help_="API_KEY,通过登陆https://cloud.baidu.com/product/imagecensoring获取",
    default_value="",
)
Config.add_plugin_config(
    "setu_score",
    "SECRET_KEY",
    "",
    help_="SECRET_KEY,通过登陆https://cloud.baidu.com/product/imagecensoring获取",
    default_value="",
)
API_Key = Config.get_config("setu_score", "API_KEY")
Secret_Key = Config.get_config("setu_score", "SECRET_KEY")

setu_score = on_command('打分', priority=4, block=True)


def parse_image(key: str):

    async def _key_parser(state: T_State, img: Message = Arg(key)):
        if not get_message_img(img):
            await setu_score.finish("格式错误，打分已取消...")
        state[key] = img

    return _key_parser


@setu_score.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    if event.reply:
        state["img"] = event.reply.message
    if get_message_img(event.json()):
        state["img"] = event.message


@setu_score.got("img",
                prompt="图来!",
                parameterless=[Depends(parse_image("img"))])
async def setu_got(bot: Bot,
                   event: MessageEvent,
                   state: T_State = State(),
                   img: Message = Arg("img")):
    pic_url = get_message_img(img)[0]
    s = porn_pic(pic_url)
    if s == -1:
        await bot.send(event, '未配置KEY,请先在config.yaml中配置！')
    elif s == 0:
        await bot.send(event, '你太菜了，这张也能称为色图？')
        #await bot.send(event,
        #               message=MessageSegment.image(pic_url) +
        #               '你太菜了，这张也能称为色图？')
    elif s == 100:
        await bot.send(event, f'{NICKNAME}看了一眼你发的图，鉴定为:社保!')  #(评分{s})')
    elif s > 80:
        await bot.send(event, f'{NICKNAME}看了一眼你发的图，鉴定为:涩情!')  #(评分{s})')
    elif s > 50:
        await bot.send(event, f'{NICKNAME}看了一眼你发的图，鉴定为:一般!')  #(评分{s})')
    else:
        await bot.send(event, f'{NICKNAME}看了一眼你发的图，鉴定为:就这?')  #(评分{s})')
        #await bot.send(event,
        #               message=MessageSegment.image(pic_url) + f'色图评分为{s}')


def porn_pic(pic_url):
    # client_id 为官网获取的AK， client_secret 为官网获取的SK
    print(API_Key)
    print(Secret_Key)
    host = f'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_Key}&client_secret={Secret_Key}'
    response = requests.get(host)
    try:
        access_token = response.json()["access_token"]
    except Exception as e:
        print(e)
        return -1
    request_url = 'https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined'
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}

    params = {"imgUrl": pic_url}
    response = requests.post(request_url, data=params, headers=headers)
    try:
        data = response.json()['data'][0]
        if data['type'] == 1:
            score = round((data['probability']) * 100, 2)
            return int(score) + 1
        else:
            return 0
    except:
        return 0
