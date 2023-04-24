# -*- coding: utf-8 -*-

from copy import deepcopy
import re
from httpx import Response
import chardet

import nonebot
from nonebot import Driver
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, Event, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from bs4 import BeautifulSoup
from playwright._impl._api_types import Error

from nonebot_plugin_htmlrender import text_to_pic

from services.log import logger
from configs.path_config import TEMP_PATH
from configs.config import Config
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
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.3
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

call = on_command("call", aliases={"ck"}, permission=SUPERUSER, priority=4, block=True)


@call.handle()
async def _(event: Event, arg: Message = CommandArg()):
    url = arg.extract_plain_text().strip()
    url = url if url.startswith(('https://', 'http://')) else f'https://{url}'
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    try:
        response = deepcopy(await AsyncHttpx.get(url, follow_redirects=True))
        url = str(response.url)
    except Exception as e:
        logger.error("截图失败", "call", user_id=event.get_user_id(), group_id=group_id, e=e)
        return await call.send("截图失败")
    path = TEMP_PATH / "call.png"
    timeout = 30000
    if Config.get_config("call", "IGNORE_LAZYLOAD"):
        try:
            card = await AsyncPlaywright.screenshot(url,
                                                    path,
                                                    viewport_size={
                                                        "width": 1920,
                                                        "height": 2048
                                                    },
                                                    timeout=10000,
                                                    element=[])
            assert card
        except Error:
            if not chardet.detect(response.content).get("encoding"):
                return await call.send("检测到乱码，取消截图")
            return await call.send(image(await text_to_pic(text=response.text,
                                                           width=540)))
        except Exception as e:
            logger.error("截图失败",
                         "call",
                         user_id=event.get_user_id(),
                         group_id=group_id,
                         e=e)
            return await call.send("截图失败")
        await call.finish(card)
    try:
        async with AsyncPlaywright.new_page(viewport={
            "width": 1920,
            "height": 1080
        }) as page:
            await page.goto(url, timeout=timeout)

            # 设置竖直滚动起始点和步长
            start_position = 0
            scroll_height = await page.evaluate('window.document.body.scrollHeight')
            step = 500
            if await lazyload_test(url, response) or scroll_height > 2000:
                # 竖直滚动并等待页面加载
                while start_position < scroll_height:
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
                        await page.evaluate(f"window.document.querySelector('{element}') \
                            .style.display='none'")
                        await page.wait_for_load_state()
                if not bool(re.search(r"\d+", url)):
                    scroll_height = await page.evaluate(
                        'window.document.body.scrollHeight')
                    card = await page.screenshot(clip={
                        "x": 0,
                        "y": 0,
                        "width": 1920,
                        "height": scroll_height - 955
                    },
                        timeout=timeout,
                        full_page=True,
                        path=path)
                else:
                    card = await page.screenshot(timeout=timeout, full_page=True, path=path)
            assert card
    except Error:
        if not chardet.detect(response.content).get("encoding"):
            return await call.send("检测到乱码，取消截图")
        return await call.send(image(await text_to_pic(text=response.text, width=540)))
    except Exception as e:
        logger.error("截图失败", "call", user_id=event.get_user_id(), group_id=group_id, e=e)
        return await call.send("截图失败")
    await call.finish(image(path))


async def lazyload_test(url: str, response: Response):
    """判断懒加载"""
    if response.status_code != 200:
        response = await AsyncHttpx.get(url, follow_redirects=True)
    soup = BeautifulSoup(response.content, "html.parser")

    lazyload_exist = False
    for tag in soup.findAll():
        if tag.has_attr("class") and "lazyload" in tag["class"]:
            lazyload_exist = True
            break
        if tag.has_attr("data-src") or tag.has_attr("data-original"):
            lazyload_exist = True
            break

    return lazyload_exist
