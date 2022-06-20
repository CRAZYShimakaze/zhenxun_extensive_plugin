# -*- coding: utf-8 -*-
from utils.message_builder import image
from datetime import datetime
from pathlib import Path
from utils.http_utils import AsyncPlaywright
from utils.http_utils import get_browser
from nonebot.adapters.onebot.v11 import MessageSegment
from typing import Optional
import os
import time
import pypinyin
from bs4 import BeautifulSoup


async def get_alc_image(path: Path, uid: str,
                        chara: str) -> Optional[MessageSegment]:
    """
    截取卡片
    :param path: 存储路径
    """
    #print(chara)
    url = f"https://enka.shinshin.moe/u/{uid}"
    browser = await get_browser()
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=300000)
        await page.set_viewport_size({"width": 2560, "height": 1080})
        await page.evaluate(
            "document.getElementsByClassName('Dropdown-list')[0].children[13].dispatchEvent(new Event('click'));"
        )
        if chara == 'none':
            await page.wait_for_load_state("networkidle", timeout=300000)
            await page.locator('div.Card').screenshot(path=path / f"{uid}.png")
            await page.close()
            #await browser.close()
            return image(path / f"{uid}.png")
        html = await page.inner_html(".CharacterList", timeout=300000)
        soup = BeautifulSoup(html, "html.parser")
        styles = [figure["style"] for figure in soup.find_all("figure")]
        #print(styles)
        index = -1
        chara_src = ""
        for i, style in enumerate(styles):
            if chara in style.lower():
                index = i
                chara_src = style
                break
        if index == -1 or not chara_src:
            return
        await page.locator(f'div.avatar.svelte-188i0pk >> nth={index}').click()
        # Click [placeholder="Custom\ text\.\.\."]
        await page.click("[placeholder=\"Custom\\ text\\.\\.\\.\"]")
        # Fill [placeholder="Custom\ text\.\.\."]
        await page.fill("[placeholder=\"Custom\\ text\\.\\.\\.\"]",
                        f"UID({uid})")
        await page.wait_for_load_state("networkidle", timeout=300000)
        await page.locator('div.Card').screenshot(path=path / f"{uid}.png")
        await page.close()
        #await browser.close()
        for file in os.listdir(path):
            if f"{uid}.png" != file:
                file = path / file
                try:
                    file.unlink()
                except:
                    pass
        return image(path / f"{uid}.png")
    except Exception as e:
        print(e)
        await page.close()
        #await browser.close()