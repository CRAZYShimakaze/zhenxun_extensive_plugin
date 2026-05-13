from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from .constants import CN_TZ, DEFAULT_WIKI_BASE_URL


def _cn_now() -> datetime:
    now = datetime.now(CN_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CN_TZ)
    return now

def _format_countdown(delta: timedelta | None) -> str:
    if not delta:
        return "--"
    total = max(0, int(delta.total_seconds()))
    hours, remainder = divmod(total, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0 and minutes > 0:
        return f"{hours}小时{minutes}分钟"
    if hours > 0:
        return f"{hours}小时"
    return f"{minutes}分钟"

def _normalize_query_text(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip().lower()

def _number_digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))

def _display_number(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "???"
    return re.sub(r"^no\.?", "", raw, flags=re.IGNORECASE).strip() or raw

def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

def _absolute_asset_url(url: Any, base_url: str = DEFAULT_WIKI_BASE_URL) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "data:", "{{")):
        return raw
    if raw.startswith("//"):
        return f"https:{raw}"
    return f"{base_url.rstrip('/')}/{raw.lstrip('/')}"

def _stat_value(stats: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = stats.get(key)
        if value not in (None, ""):
            return _to_int(value)
    return 0

def _build_stat_rows(stats: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    stat_defs = [
        ("HP", ("hp",), "#35b779"),
        ("攻击", ("atk", "attack"), "#e95f5f"),
        ("魔攻", ("matk", "sp_atk", "spAttack"), "#5d7cf2"),
        ("防御", ("def", "defense"), "#d9952f"),
        ("魔抗", ("mdef", "sp_def", "spDefense"), "#22a3a3"),
        ("速度", ("spd", "speed"), "#9162e4"),
    ]
    rows = []
    for label, keys, color in stat_defs:
        value = _stat_value(stats, *keys)
        rows.append(
            {
                "label": label,
                "value": value,
                "color": color,
                "percent": min(100, round(value / 160 * 100, 1)) if value else 0,
            }
        )
    total = _to_int(stats.get("total"), sum(item["value"] for item in rows))
    return rows, total

def _normalize_type_values(values: Any) -> list[str]:
    normalized = []
    for value in values or []:
        if isinstance(value, dict):
            text = value.get("name") or value.get("label") or value.get("value")
        else:
            text = value
        if text:
            normalized.append(str(text))
    return normalized

def _skill_category_class(category: str) -> str:
    if "物" in category:
        return "physical"
    if "魔" in category:
        return "special"
    if "防" in category:
        return "defense"
    return "status"

def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _format_number(value: Any, digits: int = 3) -> str:
    number = _num(value)
    if number is None:
        return ""
    return f"{round(number, digits):g}"

def _format_size_range(low: Any, high: Any, unit: str) -> str:
    low_text = _format_number(low)
    high_text = _format_number(high)
    if not low_text and not high_text:
        return "暂无数据"
    if low_text and high_text:
        return f"{low_text}{unit}" if low_text == high_text else f"{low_text}-{high_text}{unit}"
    return f"{low_text or high_text}{unit}"

def _sum_numbers(*values: Any) -> float | None:
    numbers = [number for number in (_num(value) for value in values) if number is not None]
    return sum(numbers) if numbers else None

def _max_capped_percent(*values: Any) -> float | None:
    numbers = [number for number in (_num(value) for value in values) if number is not None]
    return min(100.0, max(numbers)) if numbers else None

def _min_number(*values: Any) -> float | None:
    numbers = [number for number in (_num(value) for value in values) if number is not None]
    return min(numbers) if numbers else None

def _max_number(*values: Any) -> float | None:
    numbers = [number for number in (_num(value) for value in values) if number is not None]
    return max(numbers) if numbers else None

def _unique_texts(*values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in str(value or "").split("/"):
            text = part.strip().lstrip("#")
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
    return result
