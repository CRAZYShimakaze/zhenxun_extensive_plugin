import asyncio
import json
import os
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
from .utils import get_file_md5, resolve_name, version_key


driver: Driver = nonebot.get_driver()

__plugin_meta__ = PluginMetadata(
    name="绝区零攻略",
    description="绝区零角色攻略、养成材料与音擎图鉴",
    usage="""
    查询绝区零攻略
    指令：
        XX攻略
        XX素材/材料
        XX图鉴/音擎
        更新绝区零推荐（仅超级用户可用）
        检查绝区零插件更新（仅超级用户可用）
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.2",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)
__zx_plugin_name__ = __plugin_meta__.name
__plugin_version__ = __plugin_meta__.extra.get("version")

role_guide = on_regex(r"^(.*)攻略$", priority=15)
weapon_info = on_regex(r"^(.*?)(?:图鉴|音擎)$", priority=15)
break_material = on_regex(r"^(.*)(?:素材|材料)$", priority=15)
update_info = on_command("更新绝区零推荐", permission=SUPERUSER, priority=3, block=True)
check_update = on_command("检查绝区零插件更新", permission=SUPERUSER, priority=3, block=True)

SRC_URL = "/CRAZYShimakaze/CRAZYShimakaze.github.io/main/zzz/"
NICKNAME_URL = (
    "/CRAZYShimakaze/zhenxun_extensive_plugin/main/"
    "zenlesszonezero_role_info/res/json_data/nickname.json"
)
PLUGIN_URL = (
    "/CRAZYShimakaze/zhenxun_extensive_plugin/main/"
    "zenlesszonezero_recommend/"
)

RES_PATH = Path(__file__).parent / "data"
ROLE_GUIDE_PATH = RES_PATH / "role_guide"
ROLE_BREAK_PATH = RES_PATH / "role_break"
WEAPON_INFO_PATH = RES_PATH / "weapon_info"
NICKNAME_PATH = RES_PATH / "nickname.json"

CATEGORIES = {
    "role_guide": {
        "label": "角色攻略",
        "path": ROLE_GUIDE_PATH,
        "extension": ".png",
    },
    "role_break": {
        "label": "角色素材",
        "path": ROLE_BREAK_PATH,
        "extension": ".jpg",
    },
    "weapon_info": {
        "label": "音擎图鉴",
        "path": WEAPON_INFO_PATH,
        "extension": ".png",
    },
}

for category in CATEGORIES.values():
    category["path"].mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


catalogs: dict[str, dict[str, str]] = {
    name: _read_json(category["path"] / "md5.json")
    for name, category in CATEGORIES.items()
}
nickname_data: dict = _read_json(NICKNAME_PATH)
catalog_lock = asyncio.Lock()


def get_raw() -> str:
    return "https://raw.githubusercontent.com"


def _clean_query(query: str) -> str:
    return re.sub(r"^(?:绝区零|zzz)\s*", "", query.strip(), flags=re.IGNORECASE)


def _role_aliases() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for role, value in nickname_data.items():
        if not isinstance(role, str) or not isinstance(value, dict):
            continue
        values = value.get("别名", [])
        aliases[role] = [item for item in values if isinstance(item, str)]
    aliases.setdefault("柳", []).append("月城柳")
    return aliases


def _resolve_role(query: str, category: str) -> str | None:
    return resolve_name(
        _clean_query(query),
        catalogs[category],
        _role_aliases(),
    )


def _resolve_weapon(query: str) -> str | None:
    return resolve_name(_clean_query(query), catalogs["weapon_info"])


def _validated_catalog(data: object, category: str) -> dict[str, str]:
    if not isinstance(data, dict) or not data:
        raise ValueError(f"{category}索引为空")
    result = {
        name: digest.lower()
        for name, digest in data.items()
        if isinstance(name, str)
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-fA-F]{32}", digest)
    }
    if len(result) != len(data):
        raise ValueError(f"{category}索引包含无效数据")
    return result


async def _fetch_json(url: str) -> dict:
    response = await AsyncHttpx.get(get_raw() + url, follow_redirects=True)
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"远程JSON格式无效: {url}")
    return data


async def _refresh_remote_state() -> bool:
    global nickname_data

    requests = [
        _fetch_json(f"{SRC_URL}{category}/md5.json")
        for category in CATEGORIES
    ]
    requests.append(_fetch_json(NICKNAME_URL))
    results = await asyncio.gather(*requests, return_exceptions=True)

    refreshed = True
    for category, result in zip(CATEGORIES, results[: len(CATEGORIES)]):
        if isinstance(result, BaseException):
            logger.warning(f"绝区零攻略获取{category}索引失败: {result}")
            refreshed = False
            continue
        try:
            catalog = _validated_catalog(result, category)
        except ValueError as exc:
            logger.warning(str(exc))
            refreshed = False
            continue
        catalogs[category] = catalog
        _write_json(CATEGORIES[category]["path"] / "md5.json", catalog)

    nickname_result = results[-1]
    if isinstance(nickname_result, BaseException):
        logger.warning(f"绝区零攻略获取角色别名失败: {nickname_result}")
    else:
        nickname_data = nickname_result
        _write_json(NICKNAME_PATH, nickname_data)
    return refreshed


async def _ensure_catalogs() -> bool:
    if all(catalogs.values()):
        return True
    async with catalog_lock:
        if all(catalogs.values()):
            return True
        await _refresh_remote_state()
    return all(catalogs.values())


async def _download_verified(
    category: str,
    name: str,
    destination: Path,
) -> None:
    expected_md5 = catalogs[category][name]
    if destination.is_file() and get_file_md5(destination) == expected_md5:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    task_id = id(asyncio.current_task())
    temporary = destination.with_name(f".{destination.name}.{task_id}.tmp")
    try:
        downloaded = await AsyncHttpx.download_file(
            f"{get_raw()}{SRC_URL}{category}/{name}{destination.suffix}",
            temporary,
            follow_redirects=True,
        )
        if not downloaded:
            raise RuntimeError(f"下载失败: {category}/{name}")
        actual_md5 = get_file_md5(temporary)
        if actual_md5 != expected_md5:
            raise ValueError(
                f"{category}/{name}校验失败: expected={expected_md5}, actual={actual_md5}"
            )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


async def _send_asset(matcher, category: str, name: str) -> None:
    category_data = CATEGORIES[category]
    destination = category_data["path"] / f"{name}{category_data['extension']}"
    await _download_verified(category, name, destination)
    await matcher.send(image(destination))


@gold_cost(coin=1, percent=1)
async def _send_charged_asset(
    event: MessageEvent,
    matcher,
    category: str,
    name: str,
) -> None:
    try:
        await _send_asset(matcher, category, name)
    except Exception:
        await matcher.send("资源下载失败，请稍后再试。")
        raise


@role_guide.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if not await _ensure_catalogs():
        return
    if role := _resolve_role(args[0], "role_guide"):
        await _send_charged_asset(event, role_guide, "role_guide", role)


@break_material.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if not await _ensure_catalogs():
        return
    if role := _resolve_role(args[0], "role_break"):
        await _send_charged_asset(event, break_material, "role_break", role)


@weapon_info.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    if not await _ensure_catalogs():
        return
    if weapon := _resolve_weapon(args[0]):
        await _send_charged_asset(event, weapon_info, "weapon_info", weapon)


async def _sync_category(category: str) -> tuple[int, int]:
    category_data = CATEGORIES[category]
    semaphore = asyncio.Semaphore(5)

    async def sync_one(name: str) -> tuple[bool, bool]:
        destination = category_data["path"] / f"{name}{category_data['extension']}"
        if destination.is_file() and get_file_md5(destination) == catalogs[category][name]:
            return False, False
        try:
            async with semaphore:
                await _download_verified(category, name, destination)
            return True, False
        except Exception as exc:
            logger.warning(f"绝区零攻略更新{category}/{name}失败: {exc}")
            return False, True

    results = await asyncio.gather(*(sync_one(name) for name in catalogs[category]))
    return sum(changed for changed, _ in results), sum(failed for _, failed in results)


def _format_update_summary(results: dict[str, tuple[int, int]]) -> str:
    changed_parts = [
        f"{CATEGORIES[name]['label']}{result[0]}项"
        for name, result in results.items()
        if result[0]
    ]
    failed = sum(result[1] for result in results.values())
    summary = "，".join(changed_parts) if changed_parts else "没有资源变化"
    if failed:
        summary += f"，另有{failed}项更新失败"
    return summary


@update_info.handle()
async def _update_info(is_cron=False):
    if not is_cron:
        await update_info.send("开始更新绝区零推荐信息，请耐心等待...")

    refreshed = await _refresh_remote_state()
    if not refreshed and not all(catalogs.values()):
        if not is_cron:
            await update_info.send("获取远程资源索引失败，请稍后重试。")
        return

    results = {
        category: await _sync_category(category)
        for category in CATEGORIES
    }
    summary = _format_update_summary(results)
    changed = any(result[0] for result in results.values())
    failed = any(result[1] for result in results.values())

    if not is_cron:
        if not changed and not failed:
            await update_info.send("所有推荐信息均为最新！")
        else:
            await update_info.send(f"绝区零推荐更新完成：{summary}。")
        return

    if changed or failed:
        bot = nonebot.get_bot()
        for admin in bot.config.superusers:
            await bot.send_private_msg(
                user_id=int(admin),
                message=f"绝区零推荐自动更新完成：{summary}。",
            )


async def get_update_info() -> str:
    try:
        response = await AsyncHttpx.get(
            f"{get_raw()}{PLUGIN_URL}README.md",
            follow_redirects=True,
        )
    except Exception as exc:
        logger.warning(f"{__zx_plugin_name__}插件获取更新内容失败: {exc}")
        return ""
    match = re.search(
        r"\*\*[^*]+\*\*\[v[0-9.]+\]\s*(.*?)(?=\n\*\*|\Z)",
        response.text,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""


@check_update.handle()
async def _check_update(is_cron=False):
    bot = nonebot.get_bot()
    try:
        response = await AsyncHttpx.get(
            f"{get_raw()}{PLUGIN_URL}__init__.py",
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
        id="zenlesszonezero_recommend_check_update",
        replace_existing=True,
    )
    scheduler.add_job(
        _update_info,
        "cron",
        args=[1],
        hour=random.randint(9, 22),
        minute=random.randint(0, 59),
        id="zenlesszonezero_recommend_update_info",
        replace_existing=True,
    )
