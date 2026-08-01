import asyncio
from collections.abc import Mapping
from pathlib import Path
import random
import re

import nonebot
from nonebot import Driver, logger, on_command, on_regex
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.params import RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import PluginType
from zhenxun.utils.http_utils import AsyncHttpx

from ..plugin_utils.auth_utils import gold_cost
from ..plugin_utils.image_utils import image
from ..plugin_utils.recommendation_sync import (
    ResourceCategory,
    atomic_write_json,
    download_verified,
    extract_update_info,
    fetch_json,
    read_json,
    resolve_alias,
    validated_md5_catalog,
    version_key,
)


driver: Driver = nonebot.get_driver()

__plugin_meta__ = PluginMetadata(
    name="星铁攻略",
    description="星铁攻略",
    usage="""
    查询星铁攻略
    指令：
        光锥评级/推荐/建议
        遗器推荐/适配/评级
        角色配队/阵容
        XX攻略
        XX图鉴
        XX素材/材料
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.8",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)
__zx_plugin_name__ = __plugin_meta__.name
__plugin_version__ = __plugin_meta__.extra.get("version")

common_weapon_grade = on_regex(r"^光锥(?:推荐|适配|评级)$", priority=1, block=True)
common_artifact_guide = on_regex(r"^遗器(?:推荐|评级|分析)$", priority=1, block=True)
common_abyss = on_regex(r"^角色(?:配队|阵容)$", priority=1, block=True)

update_info = on_command("更新星铁推荐", permission=SUPERUSER, priority=3, block=True)
check_update = on_command("检查星铁插件更新", permission=SUPERUSER, priority=3, block=True)
role_guide = on_regex(r"^(.*)攻略$", priority=15)
starrail_info = on_regex(r"^(.*)图鉴$", priority=15)
break_material = on_regex(r"^(.*)(?:素材|材料)$", priority=15)

RAW_BASE = "https://raw.githubusercontent.com"
SRC_URL = "/CRAZYShimakaze/CRAZYShimakaze.github.io/main/starrail/"
NICKNAME_URL = (
    "/CRAZYShimakaze/zhenxun_extensive_plugin/main/"
    "starrail_role_info/res/json_data/nickname.json"
)
PLUGIN_URL = "/CRAZYShimakaze/zhenxun_extensive_plugin/main/starrail_recommend/"

RES_PATH = Path(__file__).parent / "data"
NICKNAME_PATH = RES_PATH / "nickname.json"
LEGACY_NICKNAME_PATH = Path(__file__).parent / "nickname.json"

CATEGORIES = {
    "common_guide": ResourceCategory("通用攻略", RES_PATH / "common_guide", ".jpg"),
    "role_guide": ResourceCategory("角色攻略", RES_PATH / "role_guide", ".png"),
    "role_break": ResourceCategory("角色素材", RES_PATH / "role_break", ".png"),
    "role_info": ResourceCategory("角色图鉴", RES_PATH / "role_info", ".png"),
    "weapon_info": ResourceCategory("光锥图鉴", RES_PATH / "weapon_info", ".png"),
}

for category_data in CATEGORIES.values():
    category_data.path.mkdir(parents=True, exist_ok=True)


def _load_catalog(category: str) -> dict[str, str]:
    try:
        return validated_md5_catalog(
            read_json(CATEGORIES[category].path / "md5.json"),
            category,
        )
    except ValueError:
        return {}


def _validated_aliases(data: object) -> dict[str, dict[str, list[str]]]:
    if not isinstance(data, dict):
        raise ValueError("星铁别名格式无效")
    result: dict[str, dict[str, list[str]]] = {}
    for key in ("characters", "light_cones"):
        values = data.get(key)
        if not isinstance(values, dict) or not values:
            raise ValueError(f"星铁别名缺少{key}数据")
        aliases: dict[str, list[str]] = {}
        for canonical, names in values.items():
            if not isinstance(canonical, str) or not isinstance(names, list):
                raise ValueError(f"星铁{key}别名包含无效数据")
            aliases[canonical] = [name for name in names if isinstance(name, str)]
        result[key] = aliases
    return result


def _load_aliases() -> dict[str, dict[str, list[str]]]:
    for path in (NICKNAME_PATH, LEGACY_NICKNAME_PATH):
        try:
            return _validated_aliases(read_json(path))
        except ValueError:
            continue
    return {}


catalogs = {category: _load_catalog(category) for category in CATEGORIES}
alias_data = _load_aliases()
state_lock = asyncio.Lock()


def _clean_query(query: str) -> str:
    return re.sub(r"^(?:星铁|崩铁)\s*", "", query.strip(), flags=re.IGNORECASE)


def _resolve_role(query: str, category: str) -> str | None:
    return resolve_alias(
        _clean_query(query),
        alias_data.get("characters", {}),
        catalogs[category],
    )


def _resolve_weapon(query: str) -> str | None:
    return resolve_alias(
        _clean_query(query),
        alias_data.get("light_cones", {}),
        catalogs["weapon_info"],
    )


async def _refresh_remote_state() -> bool:
    global alias_data

    requests = [
        fetch_json(f"{RAW_BASE}{SRC_URL}{category}/md5.json")
        for category in CATEGORIES
    ]
    requests.append(fetch_json(f"{RAW_BASE}{NICKNAME_URL}"))
    results = await asyncio.gather(*requests, return_exceptions=True)

    refreshed = True
    for category, result in zip(CATEGORIES, results[: len(CATEGORIES)]):
        if isinstance(result, BaseException):
            logger.warning(f"星铁攻略获取{category}索引失败: {result}")
            refreshed = False
            continue
        try:
            catalog = validated_md5_catalog(result, category)
        except ValueError as exc:
            logger.warning(str(exc))
            refreshed = False
            continue
        catalogs[category] = catalog
        atomic_write_json(CATEGORIES[category].path / "md5.json", catalog)

    alias_result = results[-1]
    if isinstance(alias_result, BaseException):
        logger.warning(f"星铁攻略获取别名失败: {alias_result}")
        refreshed = False
    else:
        try:
            aliases = _validated_aliases(alias_result)
        except ValueError as exc:
            logger.warning(str(exc))
            refreshed = False
        else:
            alias_data = aliases
            atomic_write_json(NICKNAME_PATH, aliases)
    return refreshed


async def _ensure_state(require_aliases: bool = True) -> bool:
    ready = all(catalogs.values()) and (alias_data or not require_aliases)
    if ready:
        return True
    async with state_lock:
        ready = all(catalogs.values()) and (alias_data or not require_aliases)
        if not ready:
            await _refresh_remote_state()
    return all(catalogs.values()) and (bool(alias_data) or not require_aliases)


async def _send_asset(matcher, category: str, name: str) -> None:
    await download_verified(
        RAW_BASE,
        SRC_URL,
        category,
        CATEGORIES[category],
        catalogs[category],
        name,
    )
    await matcher.send(image(CATEGORIES[category].destination(name)))


@gold_cost(coin=1, percent=1)
async def _send_charged_assets(
    event: MessageEvent,
    matcher,
    category: str,
    names: tuple[str, ...],
) -> None:
    try:
        for name in names:
            await _send_asset(matcher, category, name)
    except Exception:
        await matcher.send("资源下载失败，请稍后再试。")
        raise


async def _send_common(
    event: MessageEvent,
    matcher,
    names: tuple[str, ...],
) -> None:
    if not await _ensure_state(require_aliases=False):
        await matcher.send("资源索引获取失败，请稍后再试。")
        return
    if not all(name in catalogs["common_guide"] for name in names):
        await matcher.send("该攻略资源暂未收录。")
        return
    await _send_charged_assets(event, matcher, "common_guide", names)


@common_weapon_grade.handle()
async def _(event: MessageEvent):
    await _send_common(
        event,
        common_weapon_grade,
        ("光锥推荐1", "光锥推荐2", "光锥推荐3"),
    )


@common_artifact_guide.handle()
async def _(event: MessageEvent):
    await _send_common(event, common_artifact_guide, ("遗器推荐1", "遗器推荐2"))


@common_abyss.handle()
async def _(event: MessageEvent):
    await _send_common(event, common_abyss, ("角色配队1", "角色配队2"))


@role_guide.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if await _ensure_state() and (role := _resolve_role(args[0], "role_guide")):
        await _send_charged_assets(event, role_guide, "role_guide", (role,))


@starrail_info.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if not await _ensure_state():
        return
    if role := _resolve_role(args[0], "role_info"):
        await _send_charged_assets(event, starrail_info, "role_info", (role,))
    elif weapon := _resolve_weapon(args[0]):
        await _send_charged_assets(event, starrail_info, "weapon_info", (weapon,))


@break_material.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if await _ensure_state() and (role := _resolve_role(args[0], "role_break")):
        await _send_charged_assets(event, break_material, "role_break", (role,))


async def _sync_resources() -> dict[str, tuple[int, int]]:
    semaphore = asyncio.Semaphore(5)

    async def sync_one(category: str, name: str) -> tuple[str, bool, bool]:
        try:
            async with semaphore:
                changed = await download_verified(
                    RAW_BASE,
                    SRC_URL,
                    category,
                    CATEGORIES[category],
                    catalogs[category],
                    name,
                )
            return category, changed, False
        except Exception as exc:
            logger.warning(f"星铁攻略更新{category}/{name}失败: {exc}")
            return category, False, True

    tasks = [
        sync_one(category, name)
        for category, catalog in catalogs.items()
        for name in catalog
    ]
    results = await asyncio.gather(*tasks)
    summary = {category: [0, 0] for category in CATEGORIES}
    for category, changed, failed in results:
        summary[category][0] += int(changed)
        summary[category][1] += int(failed)
    return {category: (counts[0], counts[1]) for category, counts in summary.items()}


def _format_update_summary(
    results: Mapping[str, tuple[int, int]],
    refresh_failed: bool,
) -> str:
    parts = [
        f"{CATEGORIES[category].label}{changed}项"
        for category, (changed, _) in results.items()
        if changed
    ]
    failed = sum(item[1] for item in results.values())
    if not parts:
        parts.append("没有资源变化")
    if failed:
        parts.append(f"{failed}项资源更新失败")
    if refresh_failed:
        parts.append("部分索引或别名刷新失败")
    return "，".join(parts)


@update_info.handle()
async def _update_info(is_cron=False):
    if not is_cron:
        await update_info.send("开始更新星铁推荐信息，请耐心等待...")

    refreshed = await _refresh_remote_state()
    if not all(catalogs.values()):
        if not is_cron:
            await update_info.send("获取远程资源索引失败，请稍后重试。")
        return

    results = await _sync_resources()
    summary = _format_update_summary(results, not refreshed)
    changed = any(item[0] for item in results.values())
    failed = any(item[1] for item in results.values()) or not refreshed

    if not is_cron:
        if not changed and not failed:
            await update_info.send("所有推荐信息均为最新！")
        else:
            await update_info.send(f"星铁推荐更新完成：{summary}。")
        return

    if changed or failed:
        bot = nonebot.get_bot()
        for admin in bot.config.superusers:
            await bot.send_private_msg(
                user_id=int(admin),
                message=f"星铁推荐自动更新完成：{summary}。",
            )


async def get_update_info() -> str:
    try:
        response = await AsyncHttpx.get(
            f"{RAW_BASE}{PLUGIN_URL}README.md",
            follow_redirects=True,
        )
    except Exception as exc:
        logger.warning(f"{__zx_plugin_name__}插件获取更新内容失败: {exc}")
        return ""
    return extract_update_info(response.text)


@check_update.handle()
async def _check_update(is_cron=False):
    try:
        response = await AsyncHttpx.get(
            f"{RAW_BASE}{PLUGIN_URL}__init__.py",
            follow_redirects=True,
        )
        match = re.search(
            r'version\s*=\s*"([0-9]+(?:\.[0-9]+)*)"',
            response.text,
        )
    except Exception as exc:
        logger.warning(f"{__zx_plugin_name__}插件检查更新失败: {exc}")
        return
    if not match:
        logger.warning(f"{__zx_plugin_name__}插件远端版本号格式无效")
        return

    latest_version = match.group(1)
    update_content = await get_update_info()
    if version_key(latest_version) > version_key(__plugin_version__):
        message = (
            f"检测到{__zx_plugin_name__}插件有更新"
            f"（当前V{__plugin_version__}，最新V{latest_version}）！\n"
            f"本次更新内容如下：\n{update_content}"
        )
        if not is_cron:
            await check_update.send(message)
        else:
            bot = nonebot.get_bot()
            for admin in bot.config.superusers:
                await bot.send_private_msg(user_id=int(admin), message=message)
        return

    if not is_cron:
        await check_update.send(
            f"{__zx_plugin_name__}插件已经是最新V{__plugin_version__}！\n"
            f"最近一次更新内容如下：\n{update_content}"
        )


@driver.on_startup
async def _():
    await _refresh_remote_state()
    scheduler.add_job(
        _check_update,
        "cron",
        args=[1],
        hour=random.randint(9, 22),
        minute=random.randint(0, 59),
        id="starrail_role_recommend_check_update",
        replace_existing=True,
    )
    scheduler.add_job(
        _update_info,
        "cron",
        args=[1],
        hour=random.randint(9, 22),
        minute=random.randint(0, 59),
        id="starrail_role_recommend_update_info",
        replace_existing=True,
    )
