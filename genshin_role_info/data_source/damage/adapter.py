from __future__ import annotations

import json
from pathlib import Path

from .artifact_stats import static_percent_attributes
from .models import DamageAttributes, DamageContext


ELEMENT_INDEX = {
    "火": 1,
    "雷": 2,
    "水": 3,
    "草": 4,
    "风": 5,
    "岩": 6,
    "冰": 7,
}

ELEMENT_RULE_KEY = {
    "风": "anemo",
    "雷": "electro",
    "岩": "geo",
    "草": "dendro",
    "水": "hydro",
    "火": "pyro",
    "冰": "cryo",
}

_plugin_path = Path(__file__).resolve().parents[2]
with (_plugin_path / "res/json_data/miao_damage_talents.json").open(
    encoding="utf-8"
) as talent_file:
    _talent_source = json.load(talent_file)
TALENT_DATA = _talent_source.get("characters", {})

with (_plugin_path / "res/json_data/role_info.json").open(
    encoding="utf-8"
) as role_file:
    ROLE_INFO = json.load(role_file)

_WEAPON_TYPE_OVERRIDES = {
    "莱欧斯利": "法器",
    "那维莱特": "法器",
    "玛薇卡": "双手剑",
    "荧": "单手剑",
    "空": "单手剑",
    "旅行者": "单手剑",
}


def build_context(data: dict) -> DamageContext:
    prop = data["属性"]
    base_hp = float(prop["基础生命"])
    base_atk = float(prop["基础攻击"])
    base_defense = float(prop["基础防御"])
    damage_bonus = prop.get("伤害加成", [0] * 8)
    element_idx = ELEMENT_INDEX.get(data["元素"], 0)
    own_damage = float(damage_bonus[element_idx]) * 100
    physical_damage = float(damage_bonus[0]) * 100
    # Miao treats off-element Pyro/Hydro/Electro/Cryo bonuses as the pool used
    # by converted attacks.  Keep the panel value separate from later buffs.
    coloring_damage = sum(
        float(damage_bonus[index]) * 100
        for index in (1, 2, 3, 7)
        if index != element_idx
    )
    static_percent = static_percent_attributes(data)
    attr = DamageAttributes(
        base_hp=base_hp,
        base_atk=base_atk,
        base_defense=base_defense,
        hp=base_hp + float(prop["额外生命"]),
        atk=base_atk + float(prop["额外攻击"]),
        defense=base_defense + float(prop["额外防御"]),
        mastery=float(prop["元素精通"]),
        recharge=float(prop["元素充能效率"]) * 100,
        cpct=float(prop["暴击率"]) * 100,
        cdmg=float(prop["暴击伤害"]) * 100,
        dmg=own_damage,
        phy=physical_damage,
        heal=float(prop.get("治疗加成", 0)) * 100,
        hp_pct=static_percent["hp"],
        atk_pct=static_percent["atk"],
        defense_pct=static_percent["defense"],
        static_dmg=own_damage,
        static_phy=physical_damage,
        coloring_dmg=coloring_damage,
        static_coloring_dmg=coloring_damage,
    )
    talent_levels = {
        "a": int(data["天赋"][0]["等级"]),
        "e": int(data["天赋"][1]["等级"]),
        "q": int(data["天赋"][2]["等级"]),
    }
    talent_key = data["名称"]
    if data["名称"] in {"荧", "空", "旅行者"}:
        talent_key = f"旅行者/{ELEMENT_RULE_KEY.get(data['元素'], '')}"
    weapon = dict(data["武器"])
    weapon_type = weapon.get("类型") or weapon.get("武器类型")
    if not weapon_type:
        weapon_type = _WEAPON_TYPE_OVERRIDES.get(data["名称"])
    if not weapon_type:
        weapon_type = ROLE_INFO.get(data["名称"], {}).get("武器", "")
    if weapon_type == "大剑":
        weapon_type = "双手剑"
    if weapon_type:
        weapon["类型"] = weapon_type
    return DamageContext(
        name=data["名称"],
        element=data["元素"],
        level=int(data["等级"]),
        cons=len(data.get("命座", [])),
        talent_levels=talent_levels,
        weapon=weapon,
        artifacts=data.get("圣遗物", []),
        attr=attr,
        talent_data=TALENT_DATA.get(talent_key, TALENT_DATA.get(data["名称"], {})),
    )
