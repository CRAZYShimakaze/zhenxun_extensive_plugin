from __future__ import annotations

from .adapter import build_context
from .buffs import apply_all_buffs
from .calculator import DamageCalculator
from .miao_runtime import DamageMethods
from .rules import get_rule


def _calculate_new(data: dict) -> dict[str, tuple[str, ...]] | None:
    rule = get_rule(data["名称"], data.get("元素"))
    if rule is None:
        return None
    context = build_context(data)
    if not context.talent_data:
        return None

    default_params = rule.default_params
    if callable(default_params):
        default_params = default_params(context, None) or {}
    output: dict[str, tuple[str, ...]] = {}
    default_notes: list[str] | None = None
    fallback_notes: list[str] | None = None
    for detail_index, base_detail in enumerate(rule.details):
        detail = (
            base_detail.factory(context)
            if base_detail.factory is not None
            else base_detail
        )
        detail_params = dict(detail.params)
        if detail.params_factory is not None:
            detail_params.update(detail.params_factory(context))
        detail_context = context.clone({**default_params, **detail_params})
        detail_context.state["currentTalent"] = detail.talent
        if detail_context.cons < detail.cons or not detail.check(detail_context):
            continue
        detail_notes = apply_all_buffs(detail_context, rule.buffs)
        calc = DamageCalculator(
            detail_context.attr,
            detail_context.level,
            detail_context.element,
        )
        try:
            # Miao detail functions receive the damage method facade (`dmg`,
            # `basic`, `heal`, ...), not the low-level calculator itself.
            output[detail.title] = detail.calculate(
                detail_context,
                DamageMethods(detail_context, calc),
            ).display()
            if fallback_notes is None:
                fallback_notes = detail_notes
            if detail_index == rule.default_detail:
                default_notes = detail_notes
            # Preserve file-scoped Miao intermediates (for example Eula's
            # first charged-E result) for subsequent detail functions.
            context.state.update(detail_context.state)
        except Exception as error:
            print(f"Miao damage detail failed for {data.get('名称')}:{detail.title}: {error}")

    notes = default_notes if default_notes is not None else fallback_notes
    if notes:
        output["额外说明"] = tuple(notes)
    return output or None


def get_role_dmg(data: dict):
    try:
        return _calculate_new(data)
    except Exception as error:
        print(f"Miao Python damage calculation failed for {data.get('名称')}: {error}")
        return None
