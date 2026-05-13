from __future__ import annotations

import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
from nonebot import require

from zhenxun.services.log import logger

from .constants import DEFAULT_TIMEOUT, DEFAULT_WIKI_BASE_URL, IMAGE_FETCH_CONCURRENCY

try:
    require("nonebot_plugin_htmlrender")
    from nonebot_plugin_htmlrender import template_to_pic
except Exception as e:
    template_to_pic = None
    logger.warning(f"加载 htmlrender 失败，远行商人图片渲染不可用: {e}")

_IMAGE_DATA_CACHE: dict[str, str | None] = {}

async def _render_merchant_image(data: dict[str, Any]) -> bytes | None:
    if template_to_pic is None:
        return None
    template_dir = Path(__file__).resolve().parent / "templates"
    return await template_to_pic(
        template_path=str(template_dir),
        template_name="merchant.html",
        templates=data,
    )

def _quote_url(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%")
    query = quote(parts.query, safe="=&%")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))

def _looks_like_image(content: bytes, content_type: str) -> bool:
    head = content[:64].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        return False
    if content_type.startswith("image/"):
        return True
    return (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        or content.startswith(b"\xff\xd8\xff")
        or content.startswith(b"GIF87a")
        or content.startswith(b"GIF89a")
        or (content.startswith(b"RIFF") and content[8:12] == b"WEBP")
        or head.startswith(b"<svg")
    )

async def _image_to_data_url(url: str) -> str | None:
    raw = str(url or "").strip()
    if not raw:
        return None
    if raw.startswith("data:"):
        return raw
    if raw in _IMAGE_DATA_CACHE:
        return _IMAGE_DATA_CACHE[raw]

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                _quote_url(raw),
                headers={"Referer": DEFAULT_WIKI_BASE_URL, "Accept": "image/*,*/*;q=0.8"},
            )
            content = response.content
    except Exception as e:
        logger.debug(f"[洛克图鉴] 图片下载失败: {raw} {e}")
        _IMAGE_DATA_CACHE[raw] = None
        return None

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    if not content or not _looks_like_image(content, content_type):
        _IMAGE_DATA_CACHE[raw] = None
        return None
    if not content_type.startswith("image/"):
        content_type = mimetypes.guess_type(raw)[0] or "image/png"
    data_url = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"
    _IMAGE_DATA_CACHE[raw] = data_url
    return data_url

async def _first_available_image(*urls: str) -> str:
    fallback = ""
    for url in urls:
        if url and not fallback:
            fallback = url
        data_url = await _image_to_data_url(url)
        if data_url:
            return data_url
    return fallback

async def _inline_pet_wiki_images(data: dict[str, Any]) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(IMAGE_FETCH_CONCURRENCY)

    async def load_image(*urls: str) -> str:
        async with semaphore:
            return await _first_available_image(*urls)

    main_image = str(data.get("main_image") or "")
    pet_icon = str(data.get("pet_icon") or "")
    data["main_image"] = await load_image(main_image, pet_icon)
    data["pet_icon"] = await load_image(pet_icon, main_image)

    evo_tasks = [
        load_image(str(item.get("image") or ""), str(item.get("icon") or ""))
        for item in data.get("pet_evolution", [])
    ]
    skill_tasks = [
        load_image(str(item.get("icon") or ""))
        for item in data.get("sprite_skills", [])
    ]
    evo_images, skill_icons = await asyncio.gather(
        asyncio.gather(*evo_tasks) if evo_tasks else asyncio.sleep(0, result=[]),
        asyncio.gather(*skill_tasks) if skill_tasks else asyncio.sleep(0, result=[]),
    )
    for item, image in zip(data.get("pet_evolution", []), evo_images):
        item["image"] = image
        item["icon"] = image
    for item, icon in zip(data.get("sprite_skills", []), skill_icons):
        item["icon"] = icon
    return data

async def _inline_egg_size_images(data: dict[str, Any]) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(IMAGE_FETCH_CONCURRENCY)
    items = [
        item
        for group_key in ("exact_matches", "candidate_matches")
        for item in data.get(group_key, [])
        if isinstance(item, dict)
    ]

    async def load_image(url: str) -> str:
        async with semaphore:
            return await _first_available_image(url)

    unique_urls = [
        str(item.get("icon") or item.get("image") or "").strip()
        for item in items
        if str(item.get("icon") or item.get("image") or "").strip()
    ]
    unique_urls = list(dict.fromkeys(unique_urls))
    resolved = dict(
        zip(
            unique_urls,
            await asyncio.gather(*(load_image(url) for url in unique_urls)),
        )
    )
    for item in items:
        icon = str(item.get("icon") or item.get("image") or "").strip()
        if icon:
            item["icon"] = resolved.get(icon, icon)
    return data

async def _render_egg_size_image(data: dict[str, Any]) -> bytes | None:
    if template_to_pic is None:
        return None
    template_dir = Path(__file__).resolve().parent / "templates"
    return await template_to_pic(
        template_path=str(template_dir),
        template_name="egg_size.html",
        templates=data,
    )

async def _render_pet_wiki_image(data: dict[str, Any]) -> bytes | None:
    if template_to_pic is None:
        return None
    template_dir = Path(__file__).resolve().parent / "templates"
    return await template_to_pic(
        template_path=str(template_dir),
        template_name="pet_wiki.html",
        templates=data,
    )

async def _render_player_image(data: dict[str, Any]) -> bytes | None:
    if template_to_pic is None:
        return None
    template_dir = Path(__file__).resolve().parent / "templates"
    return await template_to_pic(
        template_path=str(template_dir),
        template_name="player.html",
        templates=data,
    )
