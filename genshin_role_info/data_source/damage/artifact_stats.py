from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Iterable


_PLUGIN_PATH = Path(__file__).resolve().parents[2]
with (_PLUGIN_PATH / "res/json_data/miao_damage_equipment.json").open(
    encoding="utf-8"
) as _equipment_file:
    _ARTIFACT_RULES = json.load(_equipment_file).get("artifacts", {})

_STATIC_KEY_MAP = {
    "hpPct": "百分比生命值",
    "atkPct": "百分比攻击力",
    "defPct": "百分比防御力",
    "hpPlus": "生命值",
    "atkPlus": "攻击力",
    "defPlus": "防御力",
    "cpct": "暴击率",
    "cdmg": "暴击伤害",
    "mastery": "元素精通",
    "recharge": "元素充能效率",
    "heal": "治疗加成",
    "phy": "物理伤害加成",
}


def artifact_attributes(artifact: dict) -> Iterable[tuple[str, float]]:
    main = artifact.get("主属性") or {}
    if main.get("属性名"):
        yield str(main["属性名"]), float(main.get("属性值", 0))
    for affix in artifact.get("词条", []):
        if affix.get("属性名"):
            yield str(affix["属性名"]), float(affix.get("属性值", 0))


def static_set_attributes(
    artifacts: Iterable[dict],
) -> Iterable[tuple[str, float]]:
    sets = Counter(
        artifact.get("所属套装", "")
        for artifact in artifacts
        if artifact.get("所属套装")
    )
    for suit, count in sets.items():
        if count < 2:
            continue
        raw = (_ARTIFACT_RULES.get(suit) or {}).get("2") or {}
        if not raw.get("isStatic"):
            continue
        for key, value in (raw.get("data") or {}).items():
            if key == "dmg" and raw.get("elem"):
                yield f"{raw['elem']}元素伤害加成", float(value)
            elif key in _STATIC_KEY_MAP:
                yield _STATIC_KEY_MAP[key], float(value)


def static_percent_attributes(data: dict) -> dict[str, float]:
    names = {
        "百分比生命值": "hp",
        "百分比攻击力": "atk",
        "百分比防御力": "defense",
    }
    result = {value: 0.0 for value in names.values()}
    artifacts = data.get("圣遗物", [])
    attributes = [
        attribute
        for artifact in artifacts
        for attribute in artifact_attributes(artifact)
    ]
    attributes.extend(static_set_attributes(artifacts))

    weapon_affix = (data.get("武器", {}).get("副属性") or {})
    if weapon_affix.get("属性名"):
        attributes.append(
            (
                str(weapon_affix["属性名"]),
                float(weapon_affix.get("属性值", 0)),
            )
        )

    for name, value in attributes:
        if name in names:
            result[names[name]] += value
    return result
