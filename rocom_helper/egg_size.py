from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from zhenxun.services.log import logger

from .common import (
    _as_list,
    _cn_now,
    _format_number,
    _format_size_range,
    _max_capped_percent,
    _max_number,
    _min_number,
    _num,
    _sum_numbers,
    _unique_texts,
)
from .constants import DEFAULT_API_BASE_URL, DEFAULT_API_KEY, DEFAULT_TIMEOUT
from .errors import EggSizeQueryError
from .rendering import _inline_egg_size_images, _render_egg_size_image


async def _fetch_egg_size_query(
    api_base_url: str,
    api_key: str,
    height_m: float,
    weight_kg: float,
) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/api/v1/games/rocom/pet/size-query"
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                url,
                headers=headers,
                params={"diameter": height_m, "weight": weight_kg},
            )
            data = response.json()
    except Exception as e:
        logger.warning(f"[洛克查蛋] 尺寸反查请求失败: {e}")
        raise EggSizeQueryError(f"请求失败：{e}") from e

    if isinstance(data, dict) and data.get("code") not in (None, 0):
        raise EggSizeQueryError(str(data.get("message") or "接口返回错误"))
    payload = data.get("data") if isinstance(data, dict) and "data" in data else data
    if not isinstance(payload, dict):
        raise EggSizeQueryError("接口返回内容无法解析")
    return payload


def _format_match_summary(probability: Any = None, match_count: Any = None) -> str:
    parts = []
    probability_text = _format_number(probability, 2)
    match_count_text = _format_number(match_count, 0)
    if probability_text:
        parts.append(f"匹配率 {probability_text}%")
    if match_count_text:
        parts.append(f"命中次数 {match_count_text}")
    return " / ".join(parts) if parts else "后端未提供"


def _format_egg_size_card(item: dict[str, Any]) -> dict[str, Any]:
    probability = _num(item.get("probability"))
    match_count = _num(item.get("matchCount"))
    height_min = _num(item.get("diameterMin"))
    height_max = _num(item.get("diameterMax"))
    weight_min = _num(item.get("weightMin"))
    weight_max = _num(item.get("weightMax"))
    return {
        "id": str(item.get("petId") or "-"),
        "name": item.get("pet") or "未知精灵",
        "icon": item.get("petIcon") or "",
        "image": item.get("petImage") or item.get("petIcon") or "",
        "probability": probability,
        "match_count": match_count,
        "match_info_label": _format_match_summary(probability, match_count),
        "height_min": height_min,
        "height_max": height_max,
        "height_label": _format_size_range(height_min, height_max, "m"),
        "weight_min": weight_min,
        "weight_max": weight_max,
        "weight_label": _format_size_range(weight_min, weight_max, "kg"),
    }


def _merge_egg_size_card(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    ids = _unique_texts(left.get("id"), right.get("id"))
    if ids:
        merged["id"] = "/".join(ids)
    merged["icon"] = left.get("icon") or right.get("icon") or ""
    merged["image"] = left.get("image") or right.get("image") or merged["icon"]

    probability = _max_capped_percent(left.get("probability"), right.get("probability"))
    match_count = _sum_numbers(left.get("match_count"), right.get("match_count"))
    merged["probability"] = probability
    merged["match_count"] = match_count
    merged["match_info_label"] = _format_match_summary(probability, match_count)

    height_min = _min_number(left.get("height_min"), right.get("height_min"))
    height_max = _max_number(left.get("height_max"), right.get("height_max"))
    weight_min = _min_number(left.get("weight_min"), right.get("weight_min"))
    weight_max = _max_number(left.get("weight_max"), right.get("weight_max"))
    merged.update(
        {
            "height_min": height_min,
            "height_max": height_max,
            "height_label": _format_size_range(height_min, height_max, "m"),
            "weight_min": weight_min,
            "weight_max": weight_max,
            "weight_label": _format_size_range(weight_min, weight_max, "kg"),
        }
    )
    return merged


def _merge_egg_size_cards(
    exact: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exact_map: dict[str, dict[str, Any]] = {}
    candidate_map: dict[str, dict[str, Any]] = {}

    def card_key(item: dict[str, Any]) -> str:
        name = re.sub(r"\s+", "", str(item.get("name") or ""))
        return name or str(item.get("id") or "")

    for item in exact:
        key = card_key(item)
        exact_map[key] = _merge_egg_size_card(exact_map[key], item) if key in exact_map else item

    for item in candidates:
        key = card_key(item)
        if key in exact_map:
            exact_map[key] = _merge_egg_size_card(exact_map[key], item)
        else:
            candidate_map[key] = _merge_egg_size_card(candidate_map[key], item) if key in candidate_map else item

    return list(exact_map.values()), list(candidate_map.values())


def _sort_egg_size_cards(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            -(_num(item.get("probability")) or 0),
            str(item.get("name") or ""),
        ),
    )


def _build_egg_size_data(
    height_m: float,
    weight_kg: float,
    payload: dict[str, Any],
) -> dict[str, Any]:
    exact, candidates = _merge_egg_size_cards(
        [_format_egg_size_card(item) for item in _as_list(payload.get("exactResults")) if isinstance(item, dict)],
        [_format_egg_size_card(item) for item in _as_list(payload.get("candidates")) if isinstance(item, dict)],
    )
    exact = _sort_egg_size_cards(exact)
    candidates = _sort_egg_size_cards(candidates)
    query_label = f"身高 {_format_number(height_m)} m / 体重 {_format_number(weight_kg)} kg"
    return {
        "title": "洛克查蛋",
        "subtitle": "尺寸反查",
        "query_label": query_label,
        "exact_matches": exact,
        "candidate_matches": candidates,
        "exact_count": len(exact),
        "candidate_count": len(candidates),
        "total_count": len(exact) + len(candidates),
        "has_results": bool(exact or candidates),
        "updated_at": _cn_now().strftime("%Y-%m-%d %H:%M"),
        "data_source": DEFAULT_API_BASE_URL,
        "command_hint": "洛克查蛋 0.18 1.5",
    }


def _format_egg_size_line(item: dict[str, Any]) -> str:
    return (
        f"{item.get('name') or '未知精灵'} (#{item.get('id') or '-'}) - "
        f"{item.get('height_label') or '暂无数据'} / "
        f"{item.get('weight_label') or '暂无数据'} · "
        f"{item.get('match_info_label') or '后端未提供'}"
    )


def _build_egg_size_text(data: dict[str, Any]) -> str:
    query_label = data.get("query_label") or "当前尺寸"
    if not data.get("has_results"):
        return f"未找到符合 {query_label} 的精灵。"

    lines = [f"洛克查蛋尺寸反查：{query_label}"]
    exact = data.get("exact_matches") or []
    candidates = data.get("candidate_matches") or []
    if exact:
        lines.append(f"完美匹配（{len(exact)}）：")
        lines.extend(f"{index}. {_format_egg_size_line(item)}" for index, item in enumerate(exact[:10], 1))
        if len(exact) > 10:
            lines.append(f"... 还有 {len(exact) - 10} 个结果")
    if candidates:
        if exact:
            lines.append("")
        lines.append(f"范围匹配（{len(candidates)}）：")
        lines.extend(f"{index}. {_format_egg_size_line(item)}" for index, item in enumerate(candidates[:10], 1))
        if len(candidates) > 10:
            lines.append(f"... 还有 {len(candidates) - 10} 个结果")
    return "\n".join(lines)


async def _build_egg_size_reply_once(
    height_m: float,
    weight_kg: float,
    api_base_url: str = DEFAULT_API_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
) -> tuple[bytes | None, str]:
    payload = await _fetch_egg_size_query(api_base_url, api_key, height_m, weight_kg)
    data = _build_egg_size_data(height_m, weight_kg, payload)
    data["data_source"] = api_base_url.rstrip("/")
    text = _build_egg_size_text(data)
    data = await _inline_egg_size_images(data)
    pic = await _render_egg_size_image(data)
    return pic, text


async def build_egg_size_reply(
    height_m: float,
    weight_kg: float,
    api_base_url: str = DEFAULT_API_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
) -> tuple[bytes | None, str]:
    try:
        return await _build_egg_size_reply_once(height_m, weight_kg, api_base_url, api_key)
    except Exception as e:
        logger.warning(f"[洛克查蛋] 首次获取失败，3 秒后自动重试: {e}")
        await asyncio.sleep(3)
        return await _build_egg_size_reply_once(height_m, weight_kg, api_base_url, api_key)
