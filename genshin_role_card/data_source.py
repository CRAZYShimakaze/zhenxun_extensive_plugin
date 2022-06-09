# -*- coding: utf-8 -*-
from utils.message_builder import image
from datetime import datetime
from pathlib import Path
from utils.http_utils import AsyncPlaywright
from utils.http_utils import get_browser
from nonebot.adapters.onebot.v11 import MessageSegment
from typing import Optional
import os


async def get_alc_image(path: Path, uid: str) -> Optional[MessageSegment]:
    """
    截取卡片
    :param path: 存储路径
    """
    url = "https://enka.shinshin.moe/u/" + uid
    browser = await get_browser()
    page = await browser.new_page()
    await page.goto(url, wait_until="networkidle", timeout=100000)
    await page.set_viewport_size({"width": 2560, "height": 1080})
    await page.evaluate(
        "document.getElementsByClassName('Dropdown-list')[0].children[13].dispatchEvent(new Event('click'));"
    )
    await page.locator('div.Card').screenshot(path=path / f"{uid}.png")
    await page.close()
    #await browser.close()
    return image(path / f"{uid}.png")
    #return await AsyncPlaywright.screenshot(url, path / f"{uid}.png", ".Card.svelte-m3ch8z")