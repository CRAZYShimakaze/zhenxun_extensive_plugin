# -*- coding: utf-8 -*-

import re
import nonebot
from configs.path_config import TEMP_PATH
from configs.config import Config
from nonebot import Driver
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from bs4 import BeautifulSoup
from utils.message_builder import image

from utils.http_utils import AsyncPlaywright, AsyncHttpx

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
__plugin_type__ = ("一些工具", )
__plugin_version__ = 0.2
__plugin_author__ = "CRAZYSHIMAKAZE, unknownsno"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
Config.add_plugin_config(
    "call",
    "IGNORE_LAZYLOAD",
    True,
    name="call",
    help_="是否忽略懒加载，默认True（改为False后即可截长图，单个图片8M左右，酌情选择）",
    default_value=True,
)

call = on_command("call",
                  aliases={"ck"},
                  permission=SUPERUSER,
                  priority=4,
                  block=True)


@call.handle()
async def _(arg: Message = CommandArg()):
    url = arg.extract_plain_text().strip()
    url = url if url.startswith(('https://', 'http://')) else f'https://{url}'
    path = TEMP_PATH / "call.png"
    timeout = 30000
    if Config.get_config("call", "IGNORE_LAZYLOAD"):
        try:
            card = await AsyncPlaywright.screenshot(url, TEMP_PATH / "call.png", viewport_size=dict(width=1920, height=2048), element=[])
            assert card
        except Exception as e:
            raise e
        await call.finish(card)
    try:
        async with AsyncPlaywright.new_page(
                viewport=dict(width=1920, height=1080)) as page:
            await page.goto(url, timeout=timeout)

            # 设置竖直滚动起始点和步长
            start_position = 0
            scrollHeight = await page.evaluate(
                'window.document.body.scrollHeight')
            step = 500
            if await lazyload_test(url) or scrollHeight > 2000:
                # 竖直滚动并等待页面加载
                while (start_position < (scrollHeight)):
                    start_position += step
                    position = str(start_position)
                    run_scroll = 'window.scrollTo(0,' + position + ')'
                    await page.evaluate(run_scroll)
                    await page.wait_for_timeout(1000)
                await page.wait_for_load_state()

            # 对bilibili特殊处理
            if "bilibili" in url:
                for element in [
                        ".bili-feed4 .bili-header .slide-down", ".login-tip",
                        ".header-channel-fixed"
                ]:
                    if await page.locator(f'{element}').is_visible():
                        await page.evaluate(
                            f"window.document.querySelector('{element}') \
                            .style.display='none'")
                        await page.wait_for_load_state()
                if not bool(re.search(r"\d+", url)):
                    scrollHeight = await page.evaluate(
                        'window.document.body.scrollHeight')
                    card = await page.screenshot(clip={
                        "x": 0,
                        "y": 0,
                        "width": 1920,
                        "height": scrollHeight - 955
                    },
                                                 timeout=timeout,
                                                 full_page=True,
                                                 path=path)
            else:
                card = await page.screenshot(timeout=timeout,
                                             full_page=True,
                                             path=path)
            assert card
    except Exception as e:
        raise e
    await call.finish(image(path))


async def lazyload_test(url: str):
    '''判断懒加载'''
    response = await AsyncHttpx.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    lazyload_exist = False
    for tag in soup.findAll():
        if tag.has_attr("class") and "lazyload" in tag["class"]:
            lazyload_exist = True
            break
        elif tag.has_attr("data-src") or tag.has_attr("data-original"):
            lazyload_exist = True
            break

    return lazyload_exist
