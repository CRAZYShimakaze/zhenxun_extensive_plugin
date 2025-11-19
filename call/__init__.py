import traceback

import nonebot
from nonebot import Driver, on_command
from nonebot.adapters.onebot.v11 import Event, Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from zhenxun.configs.path_config import TEMP_PATH
from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger
from zhenxun.utils.browser import AsyncPlaywright
from zhenxun.utils.enum import PluginType

driver: Driver = nonebot.get_driver()
__plugin_meta__ = PluginMetadata(
    name="网页截图",
    description="网页截图",
    usage="""
    usage：
    网页截图
    指令：
        call url
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.1",
        plugin_type=PluginType.NORMAL,
        limits=[],
    ).to_dict(),
)


call = on_command("call", aliases={"ck"}, permission=SUPERUSER, priority=4, block=True)


@call.handle()
async def capture(event: Event, arg: Message = CommandArg()):
    if isinstance(arg, str):
        url = arg
    else:
        url = arg.extract_plain_text().strip()
    url = url if url.startswith(("https://", "http://")) else f"https://{url}"
    path = TEMP_PATH / "call.png"
    timeout = 30000
    try:
        card = await AsyncPlaywright.screenshot(url, path, viewport_size={"width": 1920, "height": 2048}, timeout=timeout, element=[])
        assert card
    except Exception as e:
        logger.error(f"截图失败\n{traceback.format_exc()}", "call", e=e)
        return await call.send("截图失败")
    await card.send()
