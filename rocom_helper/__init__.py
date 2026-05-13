from __future__ import annotations

import re
import traceback

from nonebot import on_command, on_regex
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData, RegisterConfig, Task
from zhenxun.services.log import logger
from zhenxun.utils.common_utils import CommonUtils
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import broadcast_group

from .service import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_KEY,
    DEFAULT_WIKI_BASE_URL,
    EggSizeQueryError,
    MerchantQueryError,
    PetWikiNotFoundError,
    PetWikiQueryError,
    PlayerQueryError,
    build_egg_size_reply,
    build_merchant_reply,
    build_pet_wiki_reply,
    build_player_reply,
)

MODULE_NAME = "rocom_merchant"
MERCHANT_TASK_MODULE = "rocom_merchant_push"

Config.add_plugin_config(
    MODULE_NAME,
    "API_BASE_URL",
    DEFAULT_API_BASE_URL,
    help="洛克王国后端 API 地址",
    default_value=DEFAULT_API_BASE_URL,
    type=str,
)
Config.add_plugin_config(
    MODULE_NAME,
    "API_KEY",
    DEFAULT_API_KEY,
    help="WeGame API Key；默认使用参考仓库公开测试 key",
    default_value=DEFAULT_API_KEY,
    type=str,
)
Config.add_plugin_config(
    MODULE_NAME,
    "WIKI_BASE_URL",
    DEFAULT_WIKI_BASE_URL,
    help="洛克王国世界图鉴数据源地址；WeGame Wiki 接口不可用时使用",
    default_value=DEFAULT_WIKI_BASE_URL,
    type=str,
)
base_config = Config.get(MODULE_NAME)

__plugin_meta__ = PluginMetadata(
    name="洛克助手",
    description="查询洛克王国远行商人今日排期、精灵图鉴、查蛋尺寸反查与玩家资料",
    usage="""
    指令：
        远行商人
        XX图鉴
        洛克查蛋 0.18 1.5
        洛克玩家 <UID>
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.7",
        plugin_type=PluginType.NORMAL,
        configs=[
            RegisterConfig(
                module=MODULE_NAME,
                key="API_BASE_URL",
                value=DEFAULT_API_BASE_URL,
                help="洛克王国后端 API 地址",
                default_value=DEFAULT_API_BASE_URL,
                type=str,
            ),
            RegisterConfig(
                module=MODULE_NAME,
                key="API_KEY",
                value=DEFAULT_API_KEY,
                help="WeGame API Key；默认使用参考仓库公开测试 key",
                default_value=DEFAULT_API_KEY,
                type=str,
            ),
            RegisterConfig(
                module=MODULE_NAME,
                key="WIKI_BASE_URL",
                value=DEFAULT_WIKI_BASE_URL,
                help="洛克王国世界图鉴数据源地址；WeGame Wiki 接口不可用时使用",
                default_value=DEFAULT_WIKI_BASE_URL,
                type=str,
            ),
        ],
        tasks=[
            Task(
                module=MERCHANT_TASK_MODULE,
                name="远行商人",
                create_status=False,
                default_status=False,
            )
        ],
    ).to_dict(),
)

__zx_plugin_name__ = "洛克助手"
__plugin_usage__ = """
usage：
    远行商人
    XX图鉴
    洛克查蛋 0.18 1.5
    洛克玩家 <UID>
    指令：
        远行商人
        XX图鉴
        洛克查蛋 0.18 1.5
        洛克玩家 <UID>
""".strip()
__plugin_des__ = "查询洛克王国远行商人今日排期、精灵图鉴、查蛋尺寸反查与玩家资料"
__plugin_cmd__ = ["远行商人", "XX图鉴", "洛克查蛋", "洛克玩家"]
__plugin_version__ = 0.7
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_type__ = ("一些工具",)
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["远行商人", "XX图鉴", "洛克查蛋", "洛克玩家"],
}

merchant = on_command("远行商人", priority=5, block=True)
egg_size = on_command("洛克查蛋", aliases={"查蛋"}, priority=5, block=True)
player = on_command("洛克玩家", priority=5, block=True)
pet_wiki = on_regex(r"^(.+?)图鉴$", priority=14, block=False)

EGG_SIZE_USAGE = "查蛋用法：\n洛克查蛋 0.18 1.5\n前一个参数为身高(m)，后一个参数为体重(kg)。也支持：洛克查蛋 身高0.18m 体重1.5kg"
PLAYER_USAGE = "玩家查询用法：\n洛克玩家 <UID>"


def _parse_decimal(text: str, unit_pattern: str, prefix_pattern: str = "") -> float | None:
    raw = str(text or "").strip().lower()
    if prefix_pattern:
        raw = re.sub(prefix_pattern, "", raw, count=1, flags=re.IGNORECASE).strip()
    match = re.fullmatch(rf"([0-9]+(?:\.[0-9]+)?)({unit_pattern})?", raw)
    if not match:
        return None
    value = float(match.group(1))
    return value if value > 0 else None


def _parse_height_value(text: str) -> float | None:
    return _parse_decimal(text, r"m|米", r"^(身高|高度|h)")


def _parse_weight_value(text: str) -> float | None:
    return _parse_decimal(text, r"kg|千克|公斤", r"^(体重|重量|w)")


def _parse_egg_size_args(text: str) -> tuple[float, float] | None:
    parts = [part for part in re.split(r"\s+", str(text or "").strip()) if part]
    if not parts:
        return None

    height: float | None = None
    weight: float | None = None
    positional: list[str] = []
    for part in parts:
        if re.match(r"^(身高|高度|h)", part, flags=re.IGNORECASE):
            parsed = _parse_height_value(part)
            if parsed is not None:
                height = parsed
                continue
        if re.match(r"^(体重|重量|w)", part, flags=re.IGNORECASE):
            parsed = _parse_weight_value(part)
            if parsed is not None:
                weight = parsed
                continue
        positional.append(part)

    if positional:
        if height is None:
            height = _parse_height_value(positional[0])
        if weight is None and len(positional) >= 2:
            weight = _parse_weight_value(positional[1])

    if height is None or weight is None:
        return None
    return height, weight


async def _merchant_push_check(bot: Bot, group_id: str) -> bool:
    """检查该群是否开启了远行商人推送被动。"""
    return not await CommonUtils.task_is_block(bot, MERCHANT_TASK_MODULE, group_id)


# 远行商人每次刷新后 1 分钟推送到已开启该被动的群
@scheduler.scheduled_job("cron", hour="8,12,16,20", minute=5, second=0)
# @scheduler.scheduled_job("interval", seconds=30)
async def push_merchant_to_group_job():
    base_url = base_config.get("API_BASE_URL", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
    api_key = base_config.get("API_KEY", DEFAULT_API_KEY) or DEFAULT_API_KEY
    try:
        pic, text = await build_merchant_reply(base_url, api_key)
        message = MessageUtils.build_message(pic) if pic else MessageUtils.build_message(text)
        count = await broadcast_group(message, log_cmd="被动远行商人推送", check_func=_merchant_push_check)
        logger.info(f"[远行商人] 定时推送完成，成功发送到 {count} 个群")
    except MerchantQueryError as e:
        logger.error(f"[远行商人] 定时推送失败：{e}")
    except Exception as e:
        logger.error(f"[远行商人] 定时推送未知错误: {e}\n{traceback.format_exc()}")


@merchant.handle()
async def rocom_merchant(event: MessageEvent):
    """查询远行商人今日排期。"""
    base_url = base_config.get("API_BASE_URL", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
    api_key = base_config.get("API_KEY", DEFAULT_API_KEY) or DEFAULT_API_KEY
    try:
        pic, text = await build_merchant_reply(base_url, api_key)
    except MerchantQueryError as e:
        await merchant.finish(MessageSegment.reply(event.message_id) + f"查询远行商人失败：{e}")
        return
    except Exception as e:
        logger.error(f"[远行商人] 未知错误: {e}\n{traceback.format_exc()}")
        await merchant.finish(MessageSegment.reply(event.message_id) + f"查询远行商人失败：{e}")
        return

    if pic:
        await merchant.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))
        return
    await merchant.finish(MessageSegment.reply(event.message_id) + text)


@egg_size.handle()
async def rocom_egg_size(event: MessageEvent, args: Message = CommandArg()):
    """按身高与体重反查洛克王国精灵。"""
    query = args.extract_plain_text().strip()
    parsed = _parse_egg_size_args(query)
    if parsed is None:
        await egg_size.finish(MessageSegment.reply(event.message_id) + EGG_SIZE_USAGE)
        return

    height_m, weight_kg = parsed
    base_url = base_config.get("API_BASE_URL", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
    api_key = base_config.get("API_KEY", DEFAULT_API_KEY) or DEFAULT_API_KEY
    try:
        pic, text = await build_egg_size_reply(height_m, weight_kg, base_url, api_key)
    except EggSizeQueryError as e:
        await egg_size.finish(MessageSegment.reply(event.message_id) + f"查蛋尺寸反查失败：{e}")
        return
    except Exception as e:
        logger.error(f"[洛克查蛋] 尺寸反查未知错误: {e}\n{traceback.format_exc()}")
        await egg_size.finish(MessageSegment.reply(event.message_id) + f"查蛋尺寸反查失败：{e}")
        return

    if pic:
        await egg_size.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))
        return
    await egg_size.finish(MessageSegment.reply(event.message_id) + text)


@player.handle()
async def rocom_player(event: MessageEvent, args: Message = CommandArg()):
    """通过 ingame 接口查询洛克王国玩家基础资料。"""
    uid = args.extract_plain_text().strip()
    if not uid:
        await player.finish(MessageSegment.reply(event.message_id) + PLAYER_USAGE)
        return

    base_url = base_config.get("API_BASE_URL", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
    api_key = base_config.get("API_KEY", DEFAULT_API_KEY) or DEFAULT_API_KEY
    try:
        pic, text = await build_player_reply(uid, base_url, api_key)
    except PlayerQueryError as e:
        await player.finish(MessageSegment.reply(event.message_id) + f"查询玩家资料失败：{e}")
        return
    except Exception as e:
        logger.error(f"[洛克玩家] 未知错误: {e}\n{traceback.format_exc()}")
        await player.finish(MessageSegment.reply(event.message_id) + f"查询玩家资料失败：{e}")
        return

    if pic:
        await player.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))
        return
    await player.finish(MessageSegment.reply(event.message_id) + text)


@pet_wiki.handle()
async def rocom_pet_wiki(
    matcher: Matcher,
    event: MessageEvent,
    args: tuple[str, ...] = RegexGroup(),
):
    """查询洛克王国世界精灵图鉴。"""
    query = (args[0] if args else "").strip()
    if not query or len(query) > 40:
        return

    base_url = base_config.get("API_BASE_URL", DEFAULT_API_BASE_URL) or DEFAULT_API_BASE_URL
    api_key = base_config.get("API_KEY", DEFAULT_API_KEY) or DEFAULT_API_KEY
    wiki_base_url = base_config.get("WIKI_BASE_URL", DEFAULT_WIKI_BASE_URL) or DEFAULT_WIKI_BASE_URL
    try:
        pic, text = await build_pet_wiki_reply(query, base_url, api_key, wiki_base_url)
    except PetWikiNotFoundError:
        return
    except PetWikiQueryError as e:
        matcher.stop_propagation()
        await pet_wiki.finish(MessageSegment.reply(event.message_id) + f"查询精灵图鉴失败：{e}")
        return
    except Exception as e:
        logger.error(f"[洛克图鉴] 未知错误: {e}\n{traceback.format_exc()}")
        matcher.stop_propagation()
        await pet_wiki.finish(MessageSegment.reply(event.message_id) + f"查询精灵图鉴失败：{e}")
        return

    matcher.stop_propagation()
    if pic:
        await pet_wiki.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(pic))
        return
    await pet_wiki.finish(MessageSegment.reply(event.message_id) + text)
