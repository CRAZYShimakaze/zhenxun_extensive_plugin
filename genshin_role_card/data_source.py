# -*- coding: utf-8 -*-
from utils.message_builder import image
from datetime import datetime
from utils.http_utils import AsyncPlaywright
from utils.http_utils import get_browser
from nonebot.adapters.onebot.v11 import MessageSegment
from typing import Optional
import os
import time
import pypinyin
from bs4 import BeautifulSoup
from services.log import logger

browser_genshin = None


#page_genshin = None
async def get_char_list(uid: str):
    global browser_genshin  #, page_genshin
    url = f"https://enka.shinshin.moe/u/{uid}"
    s = time.time()
    if browser_genshin == None:
        browser_genshin = await get_browser()
    #if page_genshin == None:
    page_genshin = await browser_genshin.new_page()
    try:
        logger.info(f"打开网页...")
        await page_genshin.goto(url, timeout=100000)
        logger.info(f"网页打开完成！{str(time.time()-s)}s")
        visible = await page_genshin.locator('.button.svelte-w04vzo').is_visible()
        if visible:
            logger.info(f"未开详细信息权限!")
            return None, None
        s = time.time()
        await page_genshin.set_viewport_size({"width": 2560, "height": 1080})
        html = await page_genshin.inner_html(".CharacterList", timeout=100000)
        logger.info(f"角色列表打开完成！{str(time.time()-s)}s")
        s = time.time()
        soup = BeautifulSoup(html, "html.parser")
        styles = [figure["style"] for figure in soup.find_all("figure")]
        return styles, page_genshin
    except:
        page_genshin.close()
        return None, None


async def get_alc_image(uid, chara, page_genshin, styles):
    """
    截取卡片
    :param path: 存储路径
    """
    try:
        s = time.time()
        await page_genshin.evaluate(
            "document.getElementsByClassName('Dropdown-list')[0].children[13].dispatchEvent(new Event('click'));"
        )
        logger.info("切换中文完成！")
        if chara == 'none':
            # Click [placeholder="Custom\ text\.\.\."]
            await page_genshin.click('[placeholder="自定文字..."]')
            # Fill [placeholder="Custom\ text\.\.\."]
            await page_genshin.fill('[placeholder="自定文字..."]', f"UID({uid})")
            await page_genshin.wait_for_load_state("networkidle",
                                                   timeout=100000)
            card = image(await page_genshin.locator('div.Card').screenshot())
            await page_genshin.close()
            #await browser_genshin.close()
            return card
        index = -1
        chara_src = ""
        for i, style in enumerate(styles):
            if chara in style.lower():
                index = i
                chara_src = style
                break
        if index == -1 or not chara_src:
            return None
        await page_genshin.locator(f'div.avatar.svelte-1kjx8ue >> nth={index}'
                                   ).click()
        logger.info(f"切换对应角色完成！{str(time.time()-s)}s")
        s = time.time()
        # Click [placeholder="Custom\ text\.\.\."]
        await page_genshin.click('[placeholder="自定文字..."]')
        # Fill [placeholder="Custom\ text\.\.\."]
        await page_genshin.fill('[placeholder="自定文字..."]', f"UID({uid})")
        await page_genshin.wait_for_load_state("networkidle", timeout=100000)
        logger.info(f"角色载入完成！{str(time.time()-s)}s")
        s = time.time()
        card = image(await page_genshin.locator('div.Card').screenshot())
        await page_genshin.close()
        #await browser_genshin.close()
        return card
    except Exception as e:
        print(e)
        await page_genshin.close()
        #await browser.close()
        return None
