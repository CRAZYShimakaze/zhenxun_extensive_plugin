from __future__ import annotations

import copy
from dataclasses import dataclass
from itertools import product
import math
from typing import Iterable

from .artifact_stats import (
    artifact_attributes as _artifact_attributes,
    static_set_attributes as _static_set_attributes,
)
from .engine import get_role_dmg

ELEMENT_INDEX = {
    "火": 1,
    "雷": 2,
    "水": 3,
    "草": 4,
    "风": 5,
    "岩": 6,
    "冰": 7,
}
MAX_EXHAUSTIVE_COMBINATIONS = 12_000
BEAM_WIDTH = 24
GLOBAL_CANDIDATES = 10
MAX_SHORTLIST = 18


class DamageTargetError(ValueError):
    pass


@dataclass(frozen=True)
class DamageRecommendation:
    data: dict
    title: str
    value: float


def apply_artifact_combination(data: dict, artifacts: Iterable[dict]) -> dict:
    """Return role data adjusted from its current artifacts to ``artifacts``."""
    result = copy.deepcopy(data)
    selected = [copy.deepcopy(artifact) for artifact in artifacts]
    current = result.get("圣遗物", [])
    if len(current) != 5 or len(selected) != 5:
        raise ValueError("角色和候选圣遗物都必须包含五个部位")

    delta: dict[str, float] = {}
    for sign, artifact_list in ((-1, current), (1, selected)):
        for artifact in artifact_list:
            for name, value in _artifact_attributes(artifact):
                delta[name] = delta.get(name, 0) + sign * value
        for name, value in _static_set_attributes(artifact_list):
            delta[name] = delta.get(name, 0) + sign * value

    prop = result["属性"]
    for stat, base_key, extra_key in (
        ("生命值", "基础生命", "额外生命"),
        ("攻击力", "基础攻击", "额外攻击"),
        ("防御力", "基础防御", "额外防御"),
    ):
        flat = delta.get(stat, 0)
        percent = delta.get(f"百分比{stat}", 0)
        prop[extra_key] = round(
            float(prop[extra_key]) + flat + float(prop[base_key]) * percent / 100
        )

    for stat, scale in (
        ("暴击率", 100),
        ("暴击伤害", 100),
        ("元素精通", 1),
        ("元素充能效率", 100),
        ("治疗加成", 100),
    ):
        prop[stat] = max(0, float(prop.get(stat, 0)) + delta.get(stat, 0) / scale)

    damage_bonus = list(prop.get("伤害加成", [0] * 8))
    damage_bonus.extend([0] * (8 - len(damage_bonus)))
    damage_bonus[0] += delta.get("物理伤害加成", 0) / 100
    for element, index in ELEMENT_INDEX.items():
        damage_bonus[index] += delta.get(f"{element}元素伤害加成", 0) / 100
    prop["伤害加成"] = damage_bonus
    result["圣遗物"] = selected
    return result


def get_damage_target(data: dict, damage_index: int) -> tuple[str, float]:
    rows = [
        (title, values)
        for title, values in (get_role_dmg(data) or {}).items()
        if title != "额外说明"
    ]
    if not rows:
        raise DamageTargetError("该角色暂无可用于推荐的伤害计算")
    if damage_index < 1 or damage_index > len(rows):
        raise DamageTargetError(
            f"伤害序号应在 1-{len(rows)} 之间，当前输入为 {damage_index}"
        )

    title, values = rows[damage_index - 1]
    # Miao returns expected damage first even though the rendered table shows
    # the critical column on the left.
    raw_value = values[0]
    try:
        value = float(str(raw_value).rstrip("%"))
    except ValueError as error:
        raise DamageTargetError(f"第 {damage_index} 项“{title}”不是数值伤害") from error
    return title, value


def _evaluate(data: dict, artifacts: Iterable[dict], damage_index: int) -> DamageRecommendation:
    candidate_data = apply_artifact_combination(data, artifacts)
    title, value = get_damage_target(candidate_data, damage_index)
    return DamageRecommendation(candidate_data, title, value)


def recommend_single_artifact(
    data: dict,
    artifacts: Iterable[dict],
    position: int,
    damage_index: int,
) -> DamageRecommendation | None:
    ranked = rank_single_artifacts(data, artifacts, position, damage_index)
    return ranked[0] if ranked else None


def rank_single_artifacts(
    data: dict,
    artifacts: Iterable[dict],
    position: int,
    damage_index: int,
) -> list[DamageRecommendation]:
    get_damage_target(data, damage_index)
    ranked: list[tuple[float, int, DamageRecommendation]] = []
    current = list(data["圣遗物"])
    for order, artifact in enumerate(artifacts):
        combination = list(current)
        combination[position] = artifact
        recommendation = _evaluate(data, combination, damage_index)
        ranked.append((recommendation.value, order, recommendation))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [recommendation for _, _, recommendation in ranked]


def _rank_candidates(
    data: dict,
    candidates: list[dict],
    position: int,
    damage_index: int,
) -> list[dict]:
    current = list(data["圣遗物"])
    ranked: list[tuple[float, int, dict]] = []
    for order, artifact in enumerate(candidates):
        combination = list(current)
        combination[position] = artifact
        ranked.append((_evaluate(data, combination, damage_index).value, order, artifact))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [artifact for _, _, artifact in ranked]


def _shortlist(ranked: list[dict]) -> list[dict]:
    selected = list(ranked[:GLOBAL_CANDIDATES])
    main_props = {
        artifact.get("主属性", {}).get("属性名")
        for artifact in selected
    }
    for artifact in ranked[GLOBAL_CANDIDATES:]:
        main_prop = artifact.get("主属性", {}).get("属性名")
        if main_prop not in main_props:
            selected.append(artifact)
            main_props.add(main_prop)
        if len(selected) >= MAX_SHORTLIST:
            break
    return selected


def _best_from_product(
    data: dict,
    groups: list[list[dict]],
    damage_index: int,
) -> DamageRecommendation | None:
    best: DamageRecommendation | None = None
    for combination in product(*groups):
        recommendation = _evaluate(data, combination, damage_index)
        if best is None or recommendation.value > best.value:
            best = recommendation
    return best


def _best_from_beam(
    data: dict,
    groups: list[list[dict]],
    shortlists: list[list[dict]],
    damage_index: int,
) -> DamageRecommendation | None:
    seed = [candidates[0] for candidates in shortlists]
    beam: list[tuple[float, list[dict], DamageRecommendation]] = []
    seed_result = _evaluate(data, seed, damage_index)
    beam.append((seed_result.value, seed, seed_result))

    # Expanding the largest group first avoids paying its branching factor
    # once for every item already retained in the beam.
    for position in sorted(range(5), key=lambda index: len(shortlists[index]), reverse=True):
        expanded: list[tuple[float, list[dict], DamageRecommendation]] = []
        for _, combination, _ in beam:
            for artifact in shortlists[position]:
                next_combination = list(combination)
                next_combination[position] = artifact
                recommendation = _evaluate(data, next_combination, damage_index)
                expanded.append((recommendation.value, next_combination, recommendation))
        expanded.sort(key=lambda item: item[0], reverse=True)
        beam = expanded[:BEAM_WIDTH]

    best = beam[0][2] if beam else None
    if best is None:
        return None

    # Revisit every cached artifact while holding the other four fixed. This
    # recovers strong candidates omitted by the shortlist without an unbounded
    # five-dimensional Cartesian product.
    combination = list(best.data["圣遗物"])
    for _ in range(3):
        changed = False
        for position, candidates in enumerate(groups):
            position_best = best
            position_artifact = combination[position]
            for artifact in candidates:
                next_combination = list(combination)
                next_combination[position] = artifact
                recommendation = _evaluate(data, next_combination, damage_index)
                if recommendation.value > position_best.value:
                    position_best = recommendation
                    position_artifact = artifact
            if position_best.value > best.value:
                best = position_best
                combination[position] = position_artifact
                changed = True
        if not changed:
            break
    return best


def recommend_artifact_set(
    data: dict,
    artifact_lists: Iterable[Iterable[dict]],
    suit: str,
    damage_index: int,
    occupy: bool = False,
) -> DamageRecommendation | None:
    get_damage_target(data, damage_index)
    role_name = data["名称"]
    all_groups = [
        [
            artifact
            for artifact in artifacts
            if not occupy or artifact.get("角色", "") in {"", role_name}
        ]
        for artifacts in artifact_lists
    ]
    suit_groups = [
        [artifact for artifact in artifacts if suit in artifact.get("所属套装", "")]
        for artifacts in all_groups
    ]
    ranked_all = [
        _rank_candidates(data, candidates, position, damage_index)
        if candidates
        else []
        for position, candidates in enumerate(all_groups)
    ]
    ranked_suit = [
        _rank_candidates(data, candidates, position, damage_index)
        if candidates
        else []
        for position, candidates in enumerate(suit_groups)
    ]

    best: DamageRecommendation | None = None
    for off_piece in range(5):
        groups = [
            all_groups[position] if position == off_piece else suit_groups[position]
            for position in range(5)
        ]
        if any(not candidates for candidates in groups):
            continue
        combinations = math.prod(len(candidates) for candidates in groups)
        if combinations <= MAX_EXHAUSTIVE_COMBINATIONS:
            recommendation = _best_from_product(data, groups, damage_index)
        else:
            ranked = [
                ranked_all[position] if position == off_piece else ranked_suit[position]
                for position in range(5)
            ]
            recommendation = _best_from_beam(
                data,
                groups,
                [_shortlist(candidates) for candidates in ranked],
                damage_index,
            )
        if recommendation is not None and (
            best is None or recommendation.value > best.value
        ):
            best = recommendation
    return best
