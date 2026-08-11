from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable

from ..miao_runtime import compile_js_function, format_miao_number, resolve_value
from ..models import BuffRule, CharacterRule, DamageContext, DamageDetail, DamageResult
from ..reactions import level_base_damage, mastery_multiplier, reaction_config


_PLUGIN_PATH = Path(__file__).resolve().parents[3]
with (_PLUGIN_PATH / "res/json_data/miao_damage_rules.json").open(
    encoding="utf-8"
) as _rule_file:
    _RULE_SOURCE = json.load(_rule_file)


def _compiled(value: Any) -> Any:
    if isinstance(value, dict) and "__function__" in value:
        return compile_js_function(value["__function__"])
    return resolve_value(value)


def _evaluate(value: Any, context: DamageContext, methods=None) -> Any:
    if isinstance(value, dict) and "__function__" in value:
        return compile_js_function(value["__function__"])(context, methods)
    if isinstance(value, dict) and "__expression__" in value:
        return resolve_value(value)
    if isinstance(value, dict):
        return {key: _evaluate(item, context, methods) for key, item in value.items()}
    if isinstance(value, list):
        return [_evaluate(item, context, methods) for item in value]
    return resolve_value(value)


def _as_result(value: Any) -> DamageResult:
    if isinstance(value, DamageResult):
        return value
    if isinstance(value, dict):
        if value.get("type") == "text":
            return DamageResult(avg=0, text=str(value.get("avg", "")))
        average = float(value.get("avg", value.get("dmg", 0)) or 0)
        direct = value.get("dmg")
        critical = float(direct) if isinstance(direct, (int, float)) else None
        return DamageResult(
            avg=average,
            crit=critical,
            direct=critical if critical is not None else average,
        )
    return DamageResult(avg=float(value or 0), direct=float(value or 0))


def _make_detail(raw: dict[str, Any]) -> DamageDetail:
    title = str(_evaluate(raw.get("title", "伤害"), _DUMMY_CONTEXT))
    damage_function = _compiled(raw.get("dmg"))
    if not callable(damage_function):
        value = float(damage_function or 0)

        def calculate_constant(context, methods, value=value):
            return DamageResult(avg=value, direct=value)

        calculate = calculate_constant
    else:

        def calculate(context, methods, damage_function=damage_function):
            return _as_result(damage_function(context, methods))

    check = _compiled(raw.get("check")) if raw.get("check") is not None else None
    raw_params = raw.get("params", {})
    params_factory = None
    if isinstance(raw_params, dict) and "__function__" in raw_params:
        params_function = _compiled(raw_params)

        def params_factory(context):
            return params_function(context, None) or {}

        params = {}
    else:
        params = _evaluate(raw_params, _DUMMY_CONTEXT)
    return DamageDetail(
        title=title,
        calculate=calculate,
        params=params,
        check=(lambda context: bool(check(context, None))) if check else (lambda _: True),
        cons=int(raw.get("cons", 0) or 0),
        params_factory=params_factory,
        talent=str(raw.get("talent", raw.get("dmgKey", "")) or ""),
    )


def _dynamic_detail(raw_function: Callable[..., Any]) -> DamageDetail:
    def factory(context: DamageContext) -> DamageDetail:
        raw = raw_function(context, None)
        detail = _make_detail(raw)
        return detail

    return DamageDetail(
        title="动态伤害",
        calculate=lambda context, methods: DamageResult(avg=0, direct=0),
        factory=factory,
    )


def _apply_value(context: DamageContext, key: str, value: float) -> None:
    if key.startswith("_"):
        return
    attr = context.attr
    value = float(value)
    skill_match = re.fullmatch(
        r"(a|a2|a3|e|e2|q|q2|q3|t|t2|me|xe|xe2|mt|dot|break|nightsoul)"
        r"(Def|Ignore|Dmg|Enemydmg|Plus|Pct|Cpct|Cdmg|Multi|Elevated|Merrymakes)",
        key,
    )
    if skill_match:
        talent = attr.talent(skill_match.group(1))
        field_map = {
            "Def": "enemy_def",
            "Ignore": "enemy_ignore",
            "Dmg": "dmg",
            "Enemydmg": "enemy_damage",
            "Plus": "plus",
            "Pct": "pct",
            "Cpct": "cpct",
            "Cdmg": "cdmg",
            "Multi": "multi",
            "Elevated": "elevated",
            "Merrymakes": "dmg",
        }
        setattr(talent, field_map[skill_match.group(2)], getattr(talent, field_map[skill_match.group(2)]) + value)
        return

    stat_match = re.fullmatch(
        r"(mastery|cpct|cdmg|heal|recharge|dmg|enemydmg|phy|coloringDmg|shield)"
        r"(Plus|Pct|Inc)?",
        key,
    )
    if stat_match:
        stat, suffix = stat_match.groups()
        attr_name = {
            "enemydmg": "enemy_damage",
            "coloringDmg": "coloring_dmg",
        }.get(stat, stat)
        if stat == "shield" and suffix == "Inc":
            attr.shield_inc += value
        elif stat == "shield":
            attr.shield += value
        elif stat == "heal" and suffix == "Inc":
            attr.heal_inc += value
        elif stat == "mastery" and suffix == "Inc":
            attr.mastery_inc += value
        elif suffix == "Inc":
            # Miao stores generic ``Inc`` values separately from the
            # effective stat. Only healing and shield formulas consume it.
            return
        else:
            setattr(attr, attr_name, getattr(attr, attr_name) + value)
        return

    base_match = re.fullmatch(r"(hp|def|atk)(Base|Plus|Pct|Inc)?", key)
    if base_match:
        stat, suffix = base_match.groups()
        if stat == "def":
            stat = "defense"
        if suffix == "Base":
            pct = getattr(attr, f"{stat}_pct")
            setattr(attr, f"base_{stat}", getattr(attr, f"base_{stat}") + value)
            setattr(attr, stat, getattr(attr, stat) + value * (1 + pct / 100))
        elif suffix == "Pct":
            getattr(attr, f"add_{stat}_pct")(value)
        elif suffix == "Inc":
            return
        else:
            setattr(attr, stat, getattr(attr, stat) + value)
        return

    if key in {"enemyDef", "enemyIgnore", "ignore"}:
        if key == "enemyDef":
            attr.enemy_def += value
        else:
            attr.enemy_ignore += value
        return
    if key in {
        "vaporize",
        "melt",
        "crystallize",
        "burning",
        "superConduct",
        "swirl",
        "electroCharged",
        "shatter",
        "overloaded",
        "bloom",
        "burgeon",
        "hyperBloom",
        "aggravate",
        "spread",
        "lunarCharged",
        "lunarBloom",
        "lunarCrystallize",
        "stellarConduct",
    }:
        attr.reaction_bonus[key] = attr.reaction_bonus.get(key, 0) + value
        return
    if key == "elevated":
        attr.elevated += value
    elif key == "kx":
        attr.resistance_reduction += value
    elif key == "fykx":
        attr.reaction_resistance_reduction += value
    elif key == "multi":
        attr.multi += value
    elif key == "fyplus":
        attr.reaction_plus += value
    elif key == "fypct":
        attr.reaction_base_pct += value
    elif key == "fybase":
        attr.reaction_base_plus += value
    elif key == "fyinc":
        attr.reaction_inc += value
    elif key == "shieldInc":
        attr.shield_inc += value


def _make_buff(raw: Any) -> BuffRule:
    if isinstance(raw, str):
        reaction_names = {
            "vaporize": "蒸发",
            "melt": "融化",
            "swirl": "扩散",
            "aggravate": "超激化",
            "spread": "蔓激化",
        }

        def apply_mastery_buff(context: DamageContext) -> str:
            reaction_type, reaction_base = reaction_config(raw, context.element)
            mastery_bonus = mastery_multiplier(reaction_type, context.attr.mastery)
            title = (
                f"元素精通：{reaction_names.get(raw, raw)}伤害提高"
                f"{format_miao_number(mastery_bonus * 100)}%"
            )
            if reaction_type == "bonus":
                reaction_value = (
                    reaction_base
                    * (
                        1
                        + context.attr.reaction_bonus.get(raw, 0) / 100
                        + mastery_bonus
                    )
                    * level_base_damage(context.level)
                )
                title += (
                    "，造成的伤害值提升"
                    f"{format_miao_number(reaction_value)}"
                )
            return title

        return BuffRule(
            f"元素精通：{reaction_names.get(raw, raw)}伤害提高",
            apply_mastery_buff,
            sort=9,
            mastery=raw,
        )

    title = str(raw.get("title", "Miao-Plugin Buff"))
    check_function = _compiled(raw.get("check")) if raw.get("check") else None
    data = raw.get("data", {})

    def apply(context: DamageContext) -> str:
        resolved_title = title
        if raw.get("isStatic"):
            return resolved_title
        unused_values: list[float] = []
        for key, value in data.items():
            resolved = _evaluate(value, context)
            if resolved is not None and isinstance(resolved, (int, float)):
                _apply_value(context, key, resolved)
                placeholder = f"[{key}]"
                if placeholder in resolved_title:
                    resolved_title = resolved_title.replace(
                        placeholder,
                        format_miao_number(float(resolved)),
                    )
                else:
                    unused_values.append(float(resolved))
        unresolved = set(re.findall(r"\[[A-Za-z_][A-Za-z0-9_]*\]", resolved_title))
        if len(unresolved) == 1 and len(unused_values) == 1:
            resolved_title = resolved_title.replace(
                unresolved.pop(),
                format_miao_number(unused_values[0]),
            )
        return resolved_title

    return BuffRule(
        title=title,
        apply=apply,
        check=(lambda context: bool(check_function(context, None)))
        if check_function
        else (lambda _: True),
        cons=int(raw.get("cons", 0) or 0),
        max_cons=(
            int(raw["maxCons"])
            if raw.get("maxCons") is not None
            else None
        ),
        sort=int(raw.get("sort", 1) or 1),
    )


class _DummyContext:
    pass


_DUMMY_CONTEXT = _DummyContext()


def _build_rule(name: str, raw: dict[str, Any]) -> CharacterRule:
    details: list[DamageDetail] = []
    for item in raw.get("details", []):
        compiled = _compiled(item)
        if callable(compiled):
            details.append(_dynamic_detail(compiled))
        else:
            details.append(_make_detail(item))

    # Miao uses `undefined` for characters without global defaults.  Treat it
    # as an empty object before the engine merges per-detail parameters.
    default_params = raw.get("defParams", {}) or {}
    if isinstance(default_params, dict) and "__function__" in default_params:
        default_params = _compiled(default_params)
    else:
        default_params = resolve_value(default_params)
    return CharacterRule(
        details=tuple(details),
        buffs=tuple(_make_buff(item) for item in raw.get("buffs", [])),
        default_params=default_params,
        default_detail=int(raw.get("defDmgIdx", 0) or 0),
        created_by=str(raw.get("createdBy", "Miao-Plugin")),
    )


RULES = {
    name: _build_rule(name, raw)
    for name, raw in _RULE_SOURCE.get("rules", {}).items()
}


def get_rule(name: str, element: str | None = None) -> CharacterRule | None:
    if name in RULES:
        return RULES[name]
    if name in {"荧", "空", "旅行者"} and element:
        element_map = {
            "风": "anemo",
            "雷": "electro",
            "岩": "geo",
            "草": "dendro",
            "水": "hydro",
            "火": "pyro",
            "冰": "cryo",
        }
        return RULES.get(f"旅行者/{element_map.get(element, '')}")
    return None


__all__ = ["RULES", "get_rule"]
