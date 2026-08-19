from __future__ import annotations

from .models import DamageAttributes, DamageResult
from .reactions import (
    crystallize_base_damage,
    REACTION_NAMES,
    level_base_damage,
    mastery_multiplier,
    reaction_config,
)


class DamageCalculator:
    def __init__(
        self,
        attr: DamageAttributes,
        level: int,
        element: str,
        enemy_level: int = 103,
        enemy_resistance: float = 10,
    ):
        self.attr = attr
        self.level = level
        self.element = element
        self.enemy_level = enemy_level
        self.enemy_resistance = enemy_resistance

    @staticmethod
    def _resistance_coefficient(resistance: float) -> float:
        if resistance >= 75:
            return 1 / (1 + 3 * resistance / 100)
        if resistance >= 0:
            return (100 - resistance) / 100
        return 1 - resistance / 200

    def _defense_coefficient(self, enemy_def: float, enemy_ignore: float) -> float:
        return (self.level + 100) / (
            (self.level + 100)
            + (self.enemy_level + 100)
            * (1 - enemy_def / 100)
            * (1 - enemy_ignore / 100)
        )

    def calculate(
        self,
        multiplier: float = 0,
        talents: str = "",
        reaction: str | None = None,
        base: float | None = None,
        physical: bool = False,
        dynamic_dmg: float = 0,
        dynamic_phy: float = 0,
        dynamic_cpct: float = 0,
        dynamic_cdmg: float = 0,
        dynamic_enemy_damage: float = 0,
        coloring: bool = False,
        scene: bool = False,
    ) -> DamageResult:
        bonus_keys = tuple(key for key in talents.split(",") if key)
        pct = multiplier
        multi = self.attr.multi
        plus = 0.0
        if physical:
            # Physical attacks use the physical bonus and ignore dynamic
            # elemental damage buffs, matching DmgCalc's ``phy`` branch.
            dmg_bonus = self.attr.phy
            dynamic_bonus = dynamic_phy
        elif coloring:
            # Converted attacks remove only the panel's static elemental
            # bonus.  Dynamic ordinary damage buffs remain active, and the
            # converted-element bonus is then added on top.
            dmg_bonus = (
                self.attr.dmg
                - self.attr.static_dmg
                + self.attr.coloring_dmg
            )
            dynamic_bonus = dynamic_dmg
        elif scene:
            # Scene damage has the same static-bonus subtraction as coloring
            # damage, but does not add a converted-element bonus.
            dmg_bonus = self.attr.dmg - self.attr.static_dmg
            dynamic_bonus = dynamic_dmg
        else:
            dmg_bonus = self.attr.dmg
            dynamic_bonus = dynamic_dmg
        cpct = self.attr.cpct + dynamic_cpct
        cdmg = self.attr.cdmg + dynamic_cdmg
        enemy_def = self.attr.enemy_def
        enemy_ignore = self.attr.enemy_ignore
        elevated = self.attr.elevated

        for key in bonus_keys:
            bonus = self.attr.talent(key)
            pct += bonus.pct
            multi += bonus.multi
            plus += bonus.plus
            dmg_bonus += bonus.dmg
            cpct += bonus.cpct
            cdmg += bonus.cdmg
            # ``enemydmg`` is intentionally ignored for Genshin; see above.
            enemy_def += bonus.enemy_def
            enemy_ignore += bonus.enemy_ignore
            elevated += bonus.elevated

        damage_base = (
            base * (1 + multi / 100) + plus
            if base is not None
            else self.attr.atk * pct / 100 * (1 + multi / 100) + plus
        )
        cpct = max(0, min(100, cpct)) / 100
        cdmg /= 100
        if cpct == 0:
            cdmg = 0
        reaction_key = reaction
        if reaction:
            reaction_type, coefficient = reaction_config(reaction, self.element)
            reaction_key = REACTION_NAMES.get(reaction, reaction)
            reaction_bonus = self.attr.reaction_bonus.get(reaction_key, 0)
            mastery = mastery_multiplier(reaction_type, self.attr.mastery)
            resistance_reduction = self.attr.resistance_reduction
            if reaction_key == "swirl":
                resistance_reduction = self.attr.reaction_resistance_reduction
            if reaction_type == "pct":
                damage_base *= coefficient * (1 + mastery + reaction_bonus / 100)
            elif reaction_type == "bonus":
                damage_base += (
                    level_base_damage(self.level)
                    * coefficient
                    * (1 + mastery + reaction_bonus / 100)
                )
            elif reaction_type == "fusion":
                avg = (
                    (
                        level_base_damage(self.level)
                        * (1 + self.attr.reaction_base_pct / 100)
                        + self.attr.reaction_base_plus
                    )
                    * coefficient
                    * (1 + mastery + reaction_bonus / 100)
                    + level_base_damage(self.level) * self.attr.reaction_inc / 100
                    + self.attr.reaction_plus
                ) * self._resistance_coefficient(
                    self.enemy_resistance - resistance_reduction
                )
                return DamageResult(avg=avg, direct=avg)
            elif reaction_type in {"lunar", "stellar"}:
                lunar_base = damage_base or level_base_damage(self.level)
                if reaction_key == "lunarCharged":
                    # Miao applies the 3x hit multiplier only when the
                    # reaction has a damage base; otherwise the reaction
                    # base multiplier (7.2) from DmgCalcMeta applies.
                    coefficient = 3 if damage_base else coefficient
                elif reaction_key == "lunarCrystallize":
                    coefficient = 1.6 if damage_base else coefficient
                elif reaction_key == "stellarConduct":
                    # Miao defaults the no-base stellar reaction to its
                    # reaction base multiplier (0), while a talent-linked
                    # stellar hit uses the 2x hit multiplier.
                    coefficient = 2 if damage_base else 0
                else:
                    # lunarBloom: Miao unconditionally uses the 1x base.
                    coefficient = 1
                value = (
                    (
                        lunar_base * (1 + self.attr.reaction_base_pct / 100)
                        + self.attr.reaction_base_plus
                    )
                    * coefficient
                    * (1 + mastery + reaction_bonus / 100)
                    + lunar_base * self.attr.reaction_inc / 100
                    + self.attr.reaction_plus
                )
                value *= 1 + elevated / 100
                value *= self._resistance_coefficient(
                    self.enemy_resistance - resistance_reduction
                )
                return DamageResult(
                    avg=value * (1 + cpct * cdmg),
                    crit=value * (1 + cdmg),
                    direct=value,
                )
            elif reaction_type == "shield":
                value = (
                    crystallize_base_damage(self.level)
                    * (1 + mastery + reaction_bonus / 100)
                    * self.attr.shield
                    / 100
                    * self.attr.shield_inc
                    / 100
                )
                return DamageResult(avg=value, direct=value)

        dmg_coefficient = 1 + (dmg_bonus + dynamic_bonus) / 100
        def_coefficient = self._defense_coefficient(enemy_def, enemy_ignore)
        resistance_reduction = self.attr.resistance_reduction
        if coloring:
            # Miao applies both ordinary elemental resistance reduction and
            # reaction resistance reduction (for example Viridescent Venerer)
            # to converted-element damage.
            resistance_reduction += self.attr.reaction_resistance_reduction
        resistance = self._resistance_coefficient(
            self.enemy_resistance - resistance_reduction
        )
        non_crit = damage_base * dmg_coefficient * def_coefficient * resistance
        return DamageResult(
            avg=non_crit * (1 + cpct * cdmg),
            crit=non_crit * (1 + cdmg),
            direct=non_crit,
        )

    def heal(self, value: float) -> DamageResult:
        return DamageResult(
            avg=value * (1 + self.attr.heal / 100 + self.attr.heal_inc / 100),
            direct=value * (1 + self.attr.heal / 100 + self.attr.heal_inc / 100),
        )

    def shield(self, value: float) -> DamageResult:
        result = value * self.attr.shield / 100 * self.attr.shield_inc / 100
        return DamageResult(
            avg=result,
            direct=result,
        )
