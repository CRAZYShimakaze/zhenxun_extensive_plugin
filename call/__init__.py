from ipaddress import ip_address
import traceback
from urllib.parse import urlparse
from uuid import uuid4

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from zhenxun.configs.path_config import TEMP_PATH
from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger
from zhenxun.utils.browser import AsyncPlaywright
from zhenxun.utils.enum import PluginType

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


call = on_command("call", aliases={"ck"}, priority=4, block=True)


def _normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("请输入要截图的网址")
    if not url.startswith(("https://", "http://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("请输入正确的网址（仅支持 http/https）")
    host = parsed.hostname or ""
    if host.lower() == "localhost":
        raise ValueError("不支持本地回环地址")
    try:
        host_ip = ip_address(host)
    except ValueError:
        return parsed.geturl()
    if any(
        (
            host_ip.is_loopback,
            host_ip.is_private,
            host_ip.is_link_local,
            host_ip.is_multicast,
            host_ip.is_unspecified,
            host_ip.is_reserved,
        )
    ):
        raise ValueError("不支持内网或特殊地址")
    return parsed.geturl()


@call.handle()
async def capture(arg: Message = CommandArg()):
    if isinstance(arg, str):
        raw_url = arg
    else:
        raw_url = arg.extract_plain_text()
    try:
        url = _normalize_url(raw_url)
    except ValueError as e:
        return await call.send(str(e))
    path = TEMP_PATH / f"call_{uuid4().hex}.png"
    timeout = 120000
    try:
        card = await AsyncPlaywright.screenshot(
            url,
            path,
            viewport_size={"width": 1920, "height": 2048},
            timeout=timeout,
            element=[],
            full_page=True,
        )
        if not card:
            raise RuntimeError("截图结果为空")
    except Exception as e:
        error_message = (
            "截图超时，请稍后重试"
            if "timeout" in e.__class__.__name__.lower()
            else "截图失败"
        )
        logger.error(f"{error_message}\n{traceback.format_exc()}", "call", e=e)
        return await call.send(error_message)
    await card.send()
