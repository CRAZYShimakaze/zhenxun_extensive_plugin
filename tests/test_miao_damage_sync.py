from __future__ import annotations

import json
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "genshin_role_info"
sys.path.insert(0, str(PLUGIN_ROOT))

REVISION = "afff386eb6b31bc70a98144c3bbfa884eaf5e621"


def read_json(name: str) -> dict:
    return json.loads(
        (PLUGIN_ROOT / "res" / "json_data" / name).read_text(encoding="utf-8")
    )


def test_miao_source_revision_and_character_rules() -> None:
    rules = read_json("miao_damage_rules.json")
    talents = read_json("miao_damage_talents.json")

    assert rules["source"]["revision"] == REVISION
    assert talents["source"]["revision"] == REVISION
    assert rules["rules"]["赛诺"]["defDmgKey"] == "qStellarConduct"
    assert rules["rules"]["莱欧斯利"]["defDmgIdx"] == 7
    assert len(rules["rules"]["奥黛塔"]["details"]) == 8
    assert "奥黛塔" in talents["characters"]


def test_miao_latest_equipment_rules() -> None:
    equipment = read_json("miao_damage_equipment.json")
    expected_weapons = {
        "悬黎千钧",
        "霜雪誓约",
        "群王局戏",
        "寸心余响",
        "金律铸影",
        "救赎之斩",
        "寒息",
        "戍望谣歌",
        "熔猎异端之刃",
        "引火之源",
        "白湖冬羽",
    }

    assert expected_weapons <= equipment["weapons"].keys()
    assert equipment["artifacts"]["炉火融炼之心"]["4"]["data"] == {
        "atkPct": 12,
        "stellarConduct": 50,
    }


def test_miao_rules_compile_and_latest_score_data() -> None:
    from data_source.damage.rules import RULES

    assert {"赛诺", "莱欧斯利", "奥黛塔"} <= RULES.keys()
    assert len(RULES["赛诺"].details) == 10
    assert len(RULES["莱欧斯利"].details) == 8
    assert len(RULES["奥黛塔"].details) == 8

    score = read_json("score.json")
    assert score["桑多涅"]["mastery"] == 60
    assert score["桑多涅"]["recharge"] == 50

    role_info = read_json("role_info.json")
    assert {"小天鹅", "星星使者", "莱莱可", "跳舞小妹"} <= set(
        role_info["奥黛塔"]["别名"]
    )
