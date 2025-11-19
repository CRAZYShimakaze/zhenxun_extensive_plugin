import random
import re

from nonebot import on_command
from nonebot.adapters.onebot.v11.bot import Bot, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import Arg, Depends
from nonebot.typing import T_State
from zhenxun.configs.config import BotConfig
from zhenxun.utils.http_utils import AsyncHttpx

from ..genshin_role_info.utils.json_utils import get_message_img

__zx_plugin_name__ = "色图打分"
__plugin_usage__ = """
usage：
    色图打分
    指令：
        打分+图片
""".strip()
__plugin_des__ = "色图打分"
__plugin_cmd__ = ["打分"]
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.4
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

API_Key = ""
Secret_Key = ""

setu_score = on_command("打分", priority=4, block=True)


def parse_image(key: str):
    async def _key_parser(state: T_State, img: Message = Arg(key)):
        if not get_message_img(img):
            await setu_score.finish("格式错误，打分已取消...")
        state[key] = img

    return _key_parser


@setu_score.handle()
async def _(event: MessageEvent, state: T_State):
    if event.reply:
        state["img"] = event.reply.message
    if get_message_img(event.json()):
        state["img"] = event.message


@setu_score.got("img", prompt="图来!", parameterless=[Depends(parse_image("img"))])
async def setu_got(bot: Bot, event: MessageEvent, img: Message = Arg("img")):
    pic_url = get_message_img(img)[0]
    s = await porn_pic(pic_url)
    if s == -1:
        await bot.send(event, "未配置KEY,请先在config.yaml中配置！")
    elif s == 0:
        await bot.send(event, "你太菜了，这张也能称为色图？")
    elif s == 100:
        await bot.send(
            event,
            f"{BotConfig.self_nickname}看了一眼你发的图，鉴定为:"
            + random.choice(
                [
                    "社保!",
                    "刑!",
                    "一阵哆嗦后索然无味!",
                    "100分，我要报警拉!",
                    "多发点,我去拿纸!",
                    "我超太涩了(//// ^ ////)快撤回别让管理看见!",
                ]
            ),
        )  # (评分{s})')
        if 1:  # Config.get_config("setu_score", "SEND_TO_ADMIN"):
            for admin in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(admin),
                    message="检测到社保色图一份！" + MessageSegment.image(pic_url),
                )
    elif s > 80:
        await bot.send(
            event,
            f"{BotConfig.self_nickname}看了一眼你发的图，鉴定为:"
            + random.choice(["涩情!", "嗯了!", "是涩涩!好耶!"]),
        )  # (评分{s})')
    elif s > 50:
        await bot.send(
            event,
            f"{BotConfig.self_nickname}看了一眼你发的图，鉴定为:"
            + random.choice(
                ["一般!", "啧,一般~", "也就是处男才会嗯的水平吧~", "也就那样~"]
            ),
        )  # (评分{s})')
    else:
        await bot.send(
            event,
            f"{BotConfig.self_nickname}看了一眼你发的图，鉴定为:"
            + random.choice(
                [
                    "就这?",
                    "就这就这?不要小瞧色图啊混蛋!",
                    "不是吧不是吧，你平时就对着这种图冲?",
                    "你发的是少儿频道的图吧?",
                    "你太菜了，这张也能称为色图?",
                ]
            ),
        )  # (评分{s})')
        # await bot.send(event,
        #               message=MessageSegment.image(pic_url) + f'色图评分为{s}')


async def porn_pic(pic_url) -> int:
    host = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_Key}&client_secret={Secret_Key}"
    response = await AsyncHttpx.get(host)
    try:
        access_token = response.json()["access_token"]
    except Exception as e:
        print(e)
        return -1
    request_url = (
        "https://aip.baidubce.com/rest/2.0/solution/v1/img_censor/v2/user_defined"
    )
    request_url = request_url + "?access_token=" + access_token
    headers = {"content-type": "application/x-www-form-urlencoded"}

    params = {"imgUrl": pic_url}
    response = await AsyncHttpx.post(request_url, data=params, headers=headers)
    try:
        data = response.json()["data"]
        if data[0]["type"] == 1:
            data = re.findall(r"\'probability\': ([\d.]+),", str(data))
            data.sort()
            data = float(data[-1])
            score = round(data * 100, 2)
            return int(score) + 1
    except Exception as e:
        print(e)
        return 0
