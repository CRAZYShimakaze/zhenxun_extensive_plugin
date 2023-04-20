# -*- coding: utf-8 -*-

import nonebot
from configs.path_config import TEMP_PATH
from nonebot import Driver
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from utils.http_utils import AsyncPlaywright

driver: Driver = nonebot.get_driver()

__zx_plugin_name__ = "网页截图"
__plugin_usage__ = """
usage：
    网页截图
    指令：
        call url
""".strip()
__plugin_des__ = "网页截图"
__plugin_cmd__ = ["call [url]"]
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}

call = on_command("call", aliases={"ck"}, permission=SUPERUSER, priority=4, block=True)


@call.handle()
async def _(arg: Message = CommandArg()):
    url = arg.extract_plain_text().strip()
    url = url if url.startswith(('https://', 'http://')) else f'https://{url}'
    await call.send(await AsyncPlaywright.screenshot(url, TEMP_PATH / "call.png", viewport_size=dict(width=1920, height=2048), element=[]))
