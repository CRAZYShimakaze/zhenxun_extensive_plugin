from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .miao_runtime import compile_js_function, format_miao_number
from .models import DamageContext
from .rules import _apply_value


_PLUGIN_PATH = Path(__file__).resolve().parents[2]
with (_PLUGIN_PATH / "res/json_data/miao_damage_equipment.json").open(
    encoding="utf-8"
) as _equipment_file:
    _EQUIPMENT = json.load(_equipment_file)


def _artifact_sets(context: DamageContext) -> Counter[str]:
    return Counter(
        artifact.get("所属套装", "")
        for artifact in context.artifacts
        if artifact.get("所属套装")
    )


def _evaluate(value: Any, context: DamageContext) -> Any:
    if isinstance(value, dict) and "__function__" in value:
        return compile_js_function(value["__function__"])(context, None)
    if isinstance(value, list):
        return [_evaluate(item, context) for item in value]
    if isinstance(value, dict):
        return {key: _evaluate(item, context) for key, item in value.items()}
    return value


def _check(raw: dict[str, Any], context: DamageContext) -> bool:
    check = raw.get("check")
    if not check:
        return True
    return bool(_evaluate(check, context))


def _format_value(value: Any) -> str:
    return format_miao_number(float(value))


def _apply_buff(
    raw: dict[str, Any],
    context: DamageContext,
    title_prefix: str = "",
) -> tuple[bool, str]:
    if raw.get("isStatic") or not _check(raw, context):
        return False, ""

    data = dict(raw.get("data") or {})
    refine = max(0, int(context.weapon.get("精炼等级", 1)) - 1)
    multiplier = raw.get("buffCount", 1) or 1
    for key, values in (raw.get("refine") or {}).items():
        if isinstance(values, list):
            if not values:
                continue
            value = values[min(refine, len(values) - 1)]
        else:
            value = values
        data[key] = float(value) * multiplier

    changed = False
    title = title_prefix + str(raw.get("title", ""))
    for key, value in data.items():
        resolved = _evaluate(value, context)
        if resolved is None or isinstance(resolved, bool):
            continue
        if isinstance(resolved, (int, float)):
            _apply_value(context, key, float(resolved))
            title = title.replace(f"[{key}]", _format_value(float(resolved)))
            changed = True
    return changed, title


def _weapon_buffs(context: DamageContext) -> list[tuple[dict[str, Any], str]]:
    weapon_name = str(context.weapon.get("名称", ""))
    raw = _EQUIPMENT.get("weapons", {}).get(weapon_name)
    if not raw:
        return []
    items = raw if isinstance(raw, list) else [raw]
    buffs: list[tuple[dict[str, Any], str]] = []
    for item in items:
        if isinstance(item, dict):
            buffs.append((item, f"{weapon_name}："))
    return buffs


def _artifact_buffs(context: DamageContext) -> list[tuple[dict[str, Any], str]]:
    buffs: list[tuple[dict[str, Any], str]] = []
    sets = _artifact_sets(context)
    all_buffs = _EQUIPMENT.get("artifacts", {})
    for name, count in sets.items():
        if count < 2:
            continue
        raw_set = all_buffs.get(name)
        if not raw_set:
            continue
        for level in (2, 4) if count >= 4 else (2,):
            raw = raw_set.get(str(level)) if isinstance(raw_set, dict) else None
            items = raw if isinstance(raw, list) else [raw]
            for item in items:
                if isinstance(item, dict):
                    buffs.append((item, f"{name}{level}："))
    return buffs


def _equipment_buffs(context: DamageContext) -> list[tuple[dict[str, Any], str]]:
    return _weapon_buffs(context) + _artifact_buffs(context)


def apply_all_buffs(context: DamageContext, character_buffs) -> list[str]:
    """Apply Miao's character, weapon and artifact buffs in global sort order."""
    operations: list[tuple[int, int, str, Any]] = []
    order = 0
    for buff in character_buffs:
        if buff.mastery and not context.state.get("mastery"):
            context.state["mastery"] = buff.mastery
        operations.append((buff.sort, order, "character", buff))
        order += 1
    for raw, prefix in _equipment_buffs(context):
        operations.append((int(raw.get("sort", 1) or 1), order, prefix, raw))
        order += 1

    notes: list[str] = []
    for _, _, kind, buff in sorted(operations, key=lambda item: (item[0], item[1])):
        if kind == "character":
            if buff.enabled(context):
                title = buff.apply(context) or buff.title
                if title and title not in notes:
                    notes.append(title)
            continue
        changed, title = _apply_buff(buff, context, kind)
        if changed and title and title not in notes:
            notes.append(title)
    return notes


def apply_common_buffs(context: DamageContext) -> list[str]:
    """Apply the same dynamic equipment Buffs as Miao's DmgBuffs module."""
    notes: list[str] = []
    for raw, prefix in _equipment_buffs(context):
        changed, title = _apply_buff(raw, context, prefix)
        if changed and title:
            notes.append(title)
    return notes
