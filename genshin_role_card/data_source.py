# -*- coding: utf-8 -*-
from utils.message_builder import image
from datetime import datetime
from pathlib import Path
from utils.http_utils import AsyncPlaywright
from nonebot.adapters.onebot.v11 import MessageSegment
from typing import Optional
import os


async def get_alc_image(path: Path, uid: str) -> Optional[MessageSegment]:
    """
    截取卡片
    :param path: 存储路径
    """
    url = "https://enka.shinshin.moe/u/" + uid
    return await AsyncPlaywright.screenshot(url, path / f"{uid}.png",
                                            ".Card.svelte-m3ch8z")
