from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable


@dataclass
class TalentBonus:
    pct: float = 0
    multi: float = 0
    plus: float = 0
    dmg: float = 0
    cpct: float = 0
    cdmg: float = 0
    enemy_damage: float = 0
    enemy_def: float = 0
    enemy_ignore: float = 0
    elevated: float = 0


@dataclass
class DamageAttributes:
    base_hp: float
    base_atk: float
    base_defense: float
    hp: float
    atk: float
    defense: float
    mastery: float
    recharge: float
    cpct: float
    cdmg: float
    dmg: float
    phy: float
    heal: float
    heal_inc: float = 0
    enemy_damage: float = 0
    coloring_dmg: float = 0
    shield: float = 100
    shield_inc: float = 100
    resistance_reduction: float = 0
    enemy_def: float = 0
    enemy_ignore: float = 0
    elevated: float = 0
    multi: float = 0
    hp_pct: float = 0
    atk_pct: float = 0
    defense_pct: float = 0
    reaction_bonus: dict[str, float] = field(default_factory=dict)
    reaction_base_pct: float = 0
    reaction_base_plus: float = 0
    reaction_plus: float = 0
    reaction_inc: float = 0
    talents: dict[str, TalentBonus] = field(default_factory=dict)
    # Values read from the profile panel.  Miao keeps these in
    # ``attr.staticAttr`` so scene/coloring damage can remove only the static
    # elemental bonus while retaining dynamic character/equipment buffs.
    static_dmg: float = 0
    static_phy: float = 0
    static_coloring_dmg: float = 0
    reaction_resistance_reduction: float = 0
    mastery_inc: float = 0

    def clone(self) -> DamageAttributes:
        return replace(
            self,
            reaction_bonus=dict(self.reaction_bonus),
            talents={key: replace(value) for key, value in self.talents.items()},
        )

    def talent(self, key: str) -> TalentBonus:
        if key not in self.talents:
            self.talents[key] = TalentBonus()
        return self.talents[key]

    def add_hp_pct(self, value: float) -> None:
        self.hp_pct += value
        self.hp += self.base_hp * value / 100

    def add_atk_pct(self, value: float) -> None:
        self.atk_pct += value
        self.atk += self.base_atk * value / 100

    def add_defense_pct(self, value: float) -> None:
        self.defense_pct += value
        self.defense += self.base_defense * value / 100


@dataclass(frozen=True)
class DamageResult:
    avg: float
    crit: float | None = None
    direct: float | None = None
    text: str | None = None

    def display(self) -> tuple[str, ...]:
        if self.text is not None:
            return (self.text,)
        if self.crit is None:
            return (str(int(self.avg)),)
        return str(int(self.avg)), str(int(self.crit))

    @property
    def dmg(self) -> float:
        return self.avg if self.crit is None else self.crit


@dataclass
class DamageContext:
    name: str
    element: str
    level: int
    cons: int
    talent_levels: dict[str, int]
    weapon: dict[str, Any]
    artifacts: list[dict[str, Any]]
    attr: DamageAttributes
    params: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    talent_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def clone(self, params: dict[str, Any] | None = None) -> DamageContext:
        return replace(
            self,
            attr=self.attr.clone(),
            params={**self.params, **(params or {})},
            notes=list(self.notes),
            state=dict(self.state),
        )

    def talent(self, kind: str, name: str) -> Any:
        values = self.talent_data[kind][name]
        level = max(1, min(self.talent_levels[kind], len(values)))
        return values[level - 1]


RuleCheck = Callable[[DamageContext], bool]
RuleApply = Callable[[DamageContext], str | None]


@dataclass(frozen=True)
class BuffRule:
    title: str
    apply: RuleApply
    check: RuleCheck = lambda _: True
    cons: int = 0
    max_cons: int | None = None
    sort: int = 1
    mastery: str = ""

    def enabled(self, context: DamageContext) -> bool:
        if context.cons < self.cons:
            return False
        if self.max_cons is not None and context.cons > self.max_cons:
            return False
        return self.check(context)


@dataclass(frozen=True)
class DamageDetail:
    title: str
    calculate: Callable[[DamageContext, Any], DamageResult]
    params: dict[str, Any] = field(default_factory=dict)
    check: RuleCheck = lambda _: True
    cons: int = 0
    factory: Callable[[DamageContext], "DamageDetail"] | None = None
    params_factory: Callable[[DamageContext], dict[str, Any]] | None = None
    talent: str = ""


@dataclass(frozen=True)
class CharacterRule:
    details: tuple[DamageDetail, ...]
    buffs: tuple[BuffRule, ...] = ()
    default_params: Any = field(default_factory=dict)
    default_detail: int = 0
    created_by: str = "Miao-Plugin"
