from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from zhenxun.services.log import logger

from .common import _cn_now, _format_countdown
from .constants import (
    CN_TZ,
    DEFAULT_API_BASE_URL,
    DEFAULT_API_KEY,
    DEFAULT_TIMEOUT,
    MERCHANT_HIGHLIGHT_ITEM_NAMES,
    ROUND_START_HOURS,
)
from .errors import MerchantQueryError
from .rendering import _render_merchant_image


def _current_merchant_round(now: datetime | None = None) -> dict[str, Any]:
    now = now or _cn_now()
    start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    round_index = None
    round_start = None
    round_end = None
    if start <= now < start + timedelta(hours=16):
        delta_seconds = int((now - start).total_seconds())
        round_index = delta_seconds // int(timedelta(hours=4).total_seconds()) + 1
        round_start = start + timedelta(hours=4 * (round_index - 1))
        round_end = round_start + timedelta(hours=4)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "current": round_index,
        "total": 4,
        "round_id": (
            f"{now.strftime('%Y-%m-%d')}-{round_index}"
            if round_index
            else f"{now.strftime('%Y-%m-%d')}-closed"
        ),
        "is_open": round_index is not None,
        "countdown": _format_countdown(round_end - now) if round_end else "未开市",
        "start_time": round_start,
        "end_time": round_end,
    }

def _format_merchant_time(timestamp_ms: Any) -> str:
    try:
        dt = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=CN_TZ)
        return dt.strftime("%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return "--"

def _format_merchant_window(item: dict[str, Any]) -> str:
    start_time = item.get("start_time")
    end_time = item.get("end_time")
    if start_time is None or end_time is None:
        return "当前轮次"
    start_label = _format_merchant_time(start_time)
    end_label = _format_merchant_time(end_time)
    if start_label == "--" or end_label == "--":
        return "当前轮次"
    if start_label[:5] == end_label[:5]:
        return f"{start_label} - {end_label[6:]}"
    return f"{start_label} - {end_label}"

def _datetime_from_timestamp_ms(timestamp_ms: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=CN_TZ)
    except (TypeError, ValueError, OSError):
        return None

def _merchant_activity_from_response(res: dict[str, Any] | None) -> dict[str, Any]:
    payload = res or {}
    activities = payload.get("merchantActivities")
    if activities is None:
        activities = payload.get("merchant_activities")
    activities = activities or []
    return next(
        (item for item in activities if item.get("name") == "远行商人"),
        activities[0] if activities else {},
    )

def _normalize_merchant_item(item: dict[str, Any], kind: str) -> dict[str, Any]:
    image = item.get("icon_url") or item.get("main_url") or item.get("cover_url") or ""
    name = item.get("name", f"未知{kind}")
    return {
        "kind": kind,
        "name": name,
        "image": image,
        "start_time": item.get("start_time"),
        "end_time": item.get("end_time"),
        "start_dt": _datetime_from_timestamp_ms(item.get("start_time")),
        "end_dt": _datetime_from_timestamp_ms(item.get("end_time")),
        "time_label": _format_merchant_window(item),
        "is_highlight": str(name).strip() in MERCHANT_HIGHLIGHT_ITEM_NAMES,
    }

def _merchant_products_from_activity(activity: dict[str, Any]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    products.extend(_normalize_merchant_item(item, "道具") for item in activity.get("get_props") or [])
    products.extend(_normalize_merchant_item(item, "精灵") for item in activity.get("get_pets") or [])
    products.extend(_normalize_merchant_item(item, "额外") for item in activity.get("get_extra_props") or [])
    return products

def _activity_date(activity: dict[str, Any]) -> datetime:
    raw_date = str(activity.get("start_date") or "").strip()
    if raw_date:
        try:
            return datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=CN_TZ)
        except ValueError:
            pass
    now = _cn_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def _round_label(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

def _item_overlaps_round(item: dict[str, Any], start: datetime, end: datetime) -> bool:
    item_start = item.get("start_dt")
    item_end = item.get("end_dt")
    if not item_start or not item_end:
        return False
    return item_start < end and item_end > start

def _build_schedule(
    activity: dict[str, Any],
    products: list[dict[str, Any]],
    round_info: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    date_base = _activity_date(activity)
    date_label = date_base.strftime("%Y-%m-%d")
    rounds: list[dict[str, Any]] = []
    for index, start_hour in enumerate(ROUND_START_HOURS, start=1):
        start = date_base.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=4)
        rounds.append(
            {
                "index": index,
                "label": _round_label(start, end),
                "is_current": round_info.get("date") == date_label and round_info.get("current") == index,
                "items": [item for item in products if _item_overlaps_round(item, start, end)],
            }
        )
    unscheduled = [item for item in products if not item.get("start_dt") or not item.get("end_dt")]
    return rounds, unscheduled

def _highlight_merchant_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        name = str(item.get("name") or "").strip()
        if item.get("is_highlight") and name not in seen:
            highlights.append(item)
            seen.add(name)
    return highlights

def _format_merchant_product_names(items: list[dict[str, Any]]) -> str:
    return "、".join(
        f"【稀有】{item['name']}" if item.get("is_highlight") else item["name"]
        for item in items
    )

def _build_summary_text(
    activity: dict[str, Any],
    rounds: list[dict[str, Any]],
    unscheduled: list[dict[str, Any]],
    round_info: dict[str, Any],
) -> str:
    title = activity.get("name", "远行商人") if activity else "远行商人"
    lines = [f"{title}今日排期："]
    highlights = _highlight_merchant_items(
        [item for round_data in rounds for item in round_data["items"]] + unscheduled
    )
    if highlights:
        lines.append("稀有货物：" + "、".join(item["name"] for item in highlights))
    for round_data in rounds:
        names = _format_merchant_product_names(round_data["items"]) or "暂无商品"
        lines.append(f"第{round_data['index']}轮 {round_data['label']}：{names}")
    if unscheduled:
        lines.append("未标注时间：" + _format_merchant_product_names(unscheduled))
    if round_info.get("is_open"):
        lines.append(f"当前轮次：第{round_info['current']}轮")
        lines.append(f"剩余：{round_info['countdown']}")
    else:
        lines.append("当前未开市")
    return "\n".join(lines)

def _build_template_data(
    activity: dict[str, Any],
    rounds: list[dict[str, Any]],
    unscheduled: list[dict[str, Any]],
    round_info: dict[str, Any],
) -> dict[str, Any]:
    current_round = next((item for item in rounds if item.get("is_current")), None)
    current_items = (current_round or {}).get("items") or []
    highlights = _highlight_merchant_items(
        [item for round_data in rounds for item in round_data["items"]] + unscheduled
    )
    return {
        "title": activity.get("name", "远行商人") if activity else "远行商人",
        "date_label": activity.get("start_date") or round_info.get("date") or "",
        "status_label": f"第{round_info['current']}轮" if round_info.get("is_open") else "未开市",
        "round_status_label": (
            f"第 {round_info['current']} / {round_info.get('total', 4)} 轮"
            if round_info.get("is_open")
            else "未开市"
        ),
        "countdown": round_info.get("countdown", "--"),
        "current_items": current_items,
        "current_item_count": len(current_items),
        "current_names": _format_merchant_product_names(current_items) or "暂无商品",
        "highlight_names": "、".join(item["name"] for item in highlights),
        "rounds": rounds,
        "unscheduled": unscheduled,
    }

async def _fetch_merchant_info(base_url: str, api_key: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/v1/games/rocom/merchant/info"
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                url,
                headers=headers,
                params={"refresh": "true"},
            )
    except Exception as e:
        logger.warning(f"[远行商人] 请求失败: {e}")
        raise MerchantQueryError(f"请求失败：{e}") from e

    try:
        data = response.json()
    except Exception as e:
        logger.warning(f"[远行商人] 响应解析失败: {e}")
        raise MerchantQueryError("接口返回内容无法解析") from e

    if data.get("code") != 0:
        raise MerchantQueryError(str(data.get("message") or "接口返回错误"))
    return data.get("data") or {}

async def _build_merchant_reply_once(
    base_url: str,
    api_key: str,
) -> tuple[bytes | None, str]:
    res = await _fetch_merchant_info(base_url, api_key)
    activity = _merchant_activity_from_response(res)
    products = _merchant_products_from_activity(activity)
    round_info = _current_merchant_round()
    rounds, unscheduled = _build_schedule(activity, products, round_info)
    data = _build_template_data(activity, rounds, unscheduled, round_info)
    text = _build_summary_text(activity, rounds, unscheduled, round_info)
    pic = await _render_merchant_image(data)
    return pic, text


async def build_merchant_reply(
    base_url: str = DEFAULT_API_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
) -> tuple[bytes | None, str]:
    try:
        return await _build_merchant_reply_once(base_url, api_key)
    except Exception as e:
        logger.warning(f"[远行商人] 首次获取失败，3 秒后自动重试: {e}")
        await asyncio.sleep(3)
        return await _build_merchant_reply_once(base_url, api_key)
