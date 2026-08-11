from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Callable

from .models import DamageContext, DamageResult


def format_miao_number(value: float) -> str:
    """Match Miao's Format.comma(value, 1) used in Buff descriptions."""
    return f"{float(value):,.1f}"


class _JSUndefined:
    """Small JS-undefined substitute used for optional Miao params."""

    def __bool__(self) -> bool:
        return False

    def __float__(self) -> float:
        return 0.0

    def __int__(self) -> int:
        return 0

    def __eq__(self, other: Any) -> bool:
        # Strict equality with false/zero must remain false.
        return isinstance(other, _JSUndefined)

    def __lt__(self, other: Any) -> bool:
        return 0 < other

    def __le__(self, other: Any) -> bool:
        return 0 <= other

    def __gt__(self, other: Any) -> bool:
        return 0 > other

    def __ge__(self, other: Any) -> bool:
        return 0 >= other

    def __add__(self, other: Any) -> Any:
        return other

    def __radd__(self, other: Any) -> Any:
        return other

    def __sub__(self, other: Any) -> Any:
        return -other

    def __rsub__(self, other: Any) -> Any:
        return other

    def __mul__(self, other: Any) -> Any:
        return 0

    def __rmul__(self, other: Any) -> Any:
        return 0

    def __truediv__(self, other: Any) -> float:
        return 0.0

    def __rtruediv__(self, other: Any) -> float:
        return math.inf if other else 0.0

    def __pow__(self, other: Any) -> float:
        return math.nan

    def __rpow__(self, other: Any) -> float:
        return math.nan


_JS_UNDEFINED = _JSUndefined()


class _NumericView(float):
    def __new__(
        cls,
        value: float,
        base: float = 0,
        plus: float = 0,
        pct: float = 0,
        inc: float = 0,
    ):
        instance = super().__new__(cls, value)
        instance.base = base
        instance.plus = plus
        instance.pct = pct
        instance.inc = inc
        return instance


class _AttrView:
    def __init__(self, context: DamageContext):
        self._context = context

    def __getattr__(self, name: str) -> Any:
        attr = self._context.attr
        if name == "hp":
            return _NumericView(
                attr.hp,
                attr.base_hp,
                attr.hp - attr.base_hp * (1 + attr.hp_pct / 100),
                attr.hp_pct,
            )
        if name == "atk":
            return _NumericView(
                attr.atk,
                attr.base_atk,
                attr.atk - attr.base_atk * (1 + attr.atk_pct / 100),
                attr.atk_pct,
            )
        if name in {"def", "defense"}:
            return _NumericView(
                attr.defense,
                attr.base_defense,
                attr.defense - attr.base_defense * (1 + attr.defense_pct / 100),
                attr.defense_pct,
            )
        if name == "shield":
            return _NumericView(
                attr.shield,
                base=100,
                plus=attr.shield - 100,
                inc=attr.shield_inc,
            )
        if name == "heal":
            return _NumericView(attr.heal, plus=attr.heal, inc=attr.heal_inc)
        if name == "recharge":
            return _NumericView(
                attr.recharge,
                base=100,
                plus=attr.recharge - 100,
            )
        if name in {
            "mastery",
            "cpct",
            "cdmg",
            "dmg",
            "phy",
            "enemydmg",
            "coloringDmg",
            "stance",
            "joy",
        }:
            attr_name = "coloring_dmg" if name == "coloringDmg" else name
            value = getattr(attr, attr_name, 0)
            inc = attr.mastery_inc if name == "mastery" else 0
            return _NumericView(value, base=value, inc=inc)
        if name == "element":
            return self._context.element
        if name == "characterName":
            return self._context.name
        raise AttributeError(name)


class _TalentView:
    def __init__(self, context: DamageContext):
        self._context = context

    def __getattr__(self, kind: str) -> _TalentKindView:
        return _TalentKindView(self._context, kind)


class _TalentKindView:
    def __init__(self, context: DamageContext, kind: str):
        self._context = context
        self._kind = kind

    def __getitem__(self, name: str) -> Any:
        try:
            return self._context.talent(self._kind, str(name))
        except (KeyError, IndexError):
            return _JS_UNDEFINED


class _ParamsView:
    def __init__(self, context: DamageContext):
        self._context = context

    def __getattr__(self, name: str) -> Any:
        # JavaScript's `undefined` is falsey and coerces to zero in the
        # arithmetic/comparison expressions used by Miao's params checks.
        return self._context.params.get(name, _JS_UNDEFINED)

    def __getitem__(self, name: str) -> Any:
        return self._context.params.get(name, _JS_UNDEFINED)


class _WeaponView:
    def __init__(self, context: DamageContext):
        self._context = context

    @property
    def name(self) -> str:
        return str(self._context.weapon.get("名称", ""))

    @property
    def affix(self) -> int:
        return int(self._context.weapon.get("精炼等级", 1))


def _calc_value(value: Any) -> float:
    return float(value or 0)


def _step(start: float, increment: float | None = None) -> list[float]:
    increment = start / 4 if increment is None or increment == 0 else increment
    return [start + increment * index for index in range(6)]


def _js_floor(value: Any, *_ignored: Any) -> int:
    # JavaScript ignores extra arguments passed to Math.floor.
    return math.floor(value)


def _js_min(*values: Any) -> Any:
    return values[0] if len(values) == 1 else min(values)


def _js_max(*values: Any) -> Any:
    return values[0] if len(values) == 1 else max(values)


def _includes(values: Any, value: Any) -> bool:
    return value in values


def _format_percent(value: float) -> str:
    return f"{float(value) * 100:.1f}%"


def _js_to_string(value: Any) -> str:
    if isinstance(value, _JSUndefined):
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value.is_integer():
            return str(int(value))
    return str(value)


def _js_add(left: Any, right: Any) -> Any:
    """Implement JavaScript's string-coercing `+` for translated expressions."""
    if isinstance(left, str) or isinstance(right, str):
        return _js_to_string(left) + _js_to_string(right)
    return left + right


def _js_nullish(value: Any) -> bool:
    return value is None or isinstance(value, _JSUndefined)


def _convert_string_concat(source: str) -> str:
    """Wrap JavaScript `number + 'text'` expressions in `_js_add`."""
    while True:
        plus = None
        quote = None
        escaped = False
        index = 0
        while index < len(source) - 1:
            char = source[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                index += 1
                continue
            if char in "'\"`":
                quote = char
                index += 1
                continue
            if char == "+":
                cursor = index + 1
                while cursor < len(source) and source[cursor].isspace():
                    cursor += 1
                if cursor < len(source) and source[cursor] in "'\"":
                    plus = index
                    break
            index += 1
        if plus is None:
            return source

        cursor = plus - 1
        while cursor >= 0 and source[cursor].isspace():
            cursor -= 1
        depth = {"(": 0, "[": 0, "{": 0}
        start = cursor + 1
        while cursor >= 0:
            char = source[cursor]
            if char in ")]}":
                depth[{')': '(', ']': '[', '}': '{'}[char]] += 1
            elif char in "([{":
                if depth[char]:
                    depth[char] -= 1
                else:
                    start = cursor + 1
                    break
            elif not any(depth.values()) and char in ",:;=":
                start = cursor + 1
                break
            cursor -= 1
        else:
            start = 0
        while start < plus and source[start].isspace():
            start += 1

        quote_start = plus + 1
        while quote_start < len(source) and source[quote_start].isspace():
            quote_start += 1
        string_end = quote_start + 1
        escaped = False
        while string_end < len(source):
            if escaped:
                escaped = False
            elif source[string_end] == "\\":
                escaped = True
            elif source[string_end] == source[quote_start]:
                break
            string_end += 1
        left = source[start:plus].rstrip()
        literal = source[quote_start : min(string_end + 1, len(source))]
        source = source[:start] + f"_js_add({left}, {literal})" + source[string_end + 1 :]


def _member(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name)


def _collapse_whitespace(source: str) -> str:
    result: list[str] = []
    quote: str | None = None
    escaped = False
    pending_space = False
    for char in source:
        if quote:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"`":
            if pending_space and result and result[-1] != " ":
                result.append(" ")
            pending_space = False
            quote = char
            result.append(char)
        elif char.isspace():
            pending_space = True
        else:
            if pending_space and result and result[-1] != " ":
                result.append(" ")
            pending_space = False
            result.append(char)
    return "".join(result).strip()


def _strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"(?m)\s*//.*$", "", source).strip()


def _find_matching(source: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    index = start
    while index < len(source):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise SyntaxError(f"unclosed {opening} in JavaScript rule")


def _split_top_level(source: str, separator: str = ",") -> list[str]:
    result: list[str] = []
    start = 0
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if stack:
                stack.pop()
        elif char == separator and not stack:
            result.append(source[start:index].strip())
            start = index + 1
        index += 1
    result.append(source[start:].strip())
    return [item for item in result if item]


def _convert_template(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(1)
        pieces: list[str] = []
        cursor = 0
        for expression in re.finditer(r"\$\{(.*?)\}", value):
            pieces.append(value[cursor : expression.start()])
            pieces.append("{" + _translate_expression(expression.group(1)) + "}")
            cursor = expression.end()
        pieces.append(value[cursor:])
        if len(pieces) == 1:
            return repr(value)
        return "f" + repr("".join(pieces))

    return re.sub(r"`([^`]*)`", replace, source)


def _ternary_bounds(source: str, question: int) -> tuple[int, int, int] | None:
    depth = {"(": 0, "[": 0, "{": 0}
    quote: str | None = None
    escaped = False
    index = 0
    question_depth: tuple[int, int, int] | None = None
    while index < len(source):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
        elif char in "([{":
            depth[char] += 1
        elif char == ")":
            depth["("] -= 1
        elif char == "]":
            depth["["] -= 1
        elif char == "}":
            depth["{"] -= 1
        if index == question:
            question_depth = (depth["("], depth["["], depth["{"])
            break
        index += 1
    if question_depth is None:
        return None

    nesting = 0
    scan_depth = list(question_depth)
    colon = None
    index = question + 1
    while index < len(source):
        char = source[index]
        if char in "'\"`":
            quote = char
            end = index + 1
            escaped = False
            while end < len(source):
                if escaped:
                    escaped = False
                elif source[end] == "\\":
                    escaped = True
                elif source[end] == quote:
                    break
                end += 1
            index = end + 1
            continue
        if char == "(":
            scan_depth[0] += 1
        elif char == ")":
            scan_depth[0] -= 1
        elif char == "[":
            scan_depth[1] += 1
        elif char == "]":
            scan_depth[1] -= 1
        elif char == "{":
            scan_depth[2] += 1
        elif char == "}":
            scan_depth[2] -= 1
        if char == "?":
            nesting += 1
        elif char == ":" and nesting == 0 and tuple(scan_depth) == question_depth:
            colon = index
            break
        elif char == ":" and nesting > 0:
            nesting -= 1
        index += 1
    if colon is None:
        return None

    # Find the expression start at the same bracket depth.
    start = question - 1
    local_depth = {"(": question_depth[0], "[": question_depth[1], "{": question_depth[2]}
    while start >= 0:
        char = source[start]
        if char == ")":
            local_depth["("] += 1
        elif char == "(":
            if local_depth["("] > question_depth[0]:
                local_depth["("] -= 1
            else:
                break
        elif char == "]":
            local_depth["["] += 1
        elif char == "[":
            if local_depth["["] > question_depth[1]:
                local_depth["["] -= 1
            else:
                break
        elif char == "}":
            local_depth["{"] += 1
        elif char == "{":
            if local_depth["{"] > question_depth[2]:
                local_depth["{"] -= 1
            else:
                break
        elif local_depth == {
            "(": question_depth[0],
            "[": question_depth[1],
            "{": question_depth[2],
        } and (
            char == ","
            or char == ":"
            or (
                char == "="
                and (start == 0 or source[start - 1] not in "=!<>")
                and (start + 1 >= len(source) or source[start + 1] not in "=")
            )
        ):
            break
        start -= 1
    condition_start = start + 1
    while condition_start < question and source[condition_start].isspace():
        condition_start += 1

    # The false branch ends at the enclosing expression delimiter.
    end = colon + 1
    scan_depth = list(question_depth)
    quote = None
    while end < len(source):
        char = source[end]
        if quote:
            if char == quote and source[end - 1] != "\\":
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "(":
            scan_depth[0] += 1
        elif char == ")":
            if tuple(scan_depth) == question_depth:
                break
            scan_depth[0] -= 1
        elif char == "[":
            scan_depth[1] += 1
        elif char == "]":
            if tuple(scan_depth) == question_depth:
                break
            scan_depth[1] -= 1
        elif char == "{":
            scan_depth[2] += 1
        elif char == "}":
            if tuple(scan_depth) == question_depth:
                break
            scan_depth[2] -= 1
        elif char == "," and tuple(scan_depth) == question_depth:
            break
        end += 1
    return condition_start, colon, end


def _convert_ternary(source: str) -> str:
    while True:
        question = None
        quote: str | None = None
        escaped = False
        for index, char in enumerate(source):
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in "'\"`":
                quote = char
            elif char == "?":
                question = index
                break
        if question is None:
            return source
        bounds = _ternary_bounds(source, question)
        if bounds is None:
            return source
        start, colon, end = bounds
        condition = _convert_ternary(source[start:question].strip())
        truthy = _convert_ternary(source[question + 1 : colon].strip())
        falsy = _convert_ternary(source[colon + 1 : end].strip())
        replacement = f"({truthy} if {condition} else {falsy})"
        source = source[:start] + replacement + source[end:]


def _translate_expression(source: str) -> str:
    source = _strip_comments(source.strip().rstrip(";"))
    source = _collapse_whitespace(source)
    source = _convert_string_concat(source)
    source = _convert_template(source)
    source = _convert_ternary(source)
    source = re.sub(r"\battr\.def\b", "attr.defense", source)
    source = re.sub(r"\bMath\.min\b", "_js_min", source)
    source = re.sub(r"\bMath\.max\b", "_js_max", source)
    source = re.sub(r"\bMath\.pow\b", "pow", source)
    source = re.sub(r"\bMath\.round\b", "round", source)
    source = re.sub(r"\bMath\.floor\b", "_js_floor", source)
    source = re.sub(
        r"((?:\[[^\]]*\]|'[^']*'|\"[^\"]*\"))\.includes\(([^()]*)\)",
        r"_includes(\1, \2)",
        source,
    )
    source = re.sub(r"\bFormat\.percent\b", "_format_percent", source)
    source = re.sub(
        r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*!=\s*null\b",
        r"not _js_nullish(\1)",
        source,
    )
    source = re.sub(
        r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*==\s*null\b",
        r"_js_nullish(\1)",
        source,
    )
    source = source.replace("!==", "!=").replace("===", "==")
    source = source.replace("&&", " and ").replace("||", " or ")
    source = re.sub(r"!(?!=)", " not ", source)
    source = re.sub(r"\btrue\b", "True", source)
    source = re.sub(r"\bfalse\b", "False", source)
    source = re.sub(r"\bundefined\b", "_JS_UNDEFINED", source)
    source = re.sub(r"\bnull\b", "None", source)
    # A few Miao modules keep an intermediate result in a file-scoped
    # variable.  The Python compiler executes each arrow function separately,
    # so persist that state on the damage context instead.
    source = re.sub(r"(?<![\w.])tmpDmg(?!\w)", 'state["tmpDmg"]', source)
    # JavaScript object literals and DamageResult values both expose these
    # fields through dot access.  Python dictionaries need an explicit lookup.
    source = re.sub(
        r"\b([A-Za-z_$][\w$]*)\.(dmg|avg)\b",
        lambda match: f'_member({match.group(1)}, "{match.group(2)}")',
        source,
    )
    source = re.sub(
        r"(?<=[{,])\s*([A-Za-z_$][\w$]*)\s*:",
        lambda match: f'"{match.group(1)}":',
        source,
    )
    source = re.sub(
        r"\{\s*([A-Za-z_$][\w$]*)\s*\}",
        lambda match: f'{{"{match.group(1)}": {match.group(1)}}}',
        source,
    )
    return source


def _read_statement(source: str, start: int) -> tuple[str, int]:
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    index = start
    while index < len(source):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if stack:
                stack.pop()
            elif char == "}":
                return source[start:index].strip(), index
        elif not stack and char == ";":
            return source[start:index].strip(), index + 1
        elif not stack and char == "\n":
            statement = source[start:index].strip()
            if statement:
                return statement, index + 1
        index += 1
    return source[start:].strip(), len(source)


def _parse_statements(source: str) -> list[tuple[str, Any]]:
    statements: list[tuple[str, Any]] = []
    index = 0
    while index < len(source):
        while index < len(source) and source[index].isspace():
            index += 1
        if index >= len(source):
            break
        if source.startswith("if", index) and re.match(r"if\s*\(", source[index:]):
            opening = source.find("(", index)
            closing = _find_matching(source, opening, "(", ")")
            brace = closing + 1
            while brace < len(source) and source[brace].isspace():
                brace += 1
            if brace >= len(source) or source[brace] != "{":
                raise SyntaxError("only braced if statements are supported")
            end = _find_matching(source, brace, "{", "}")
            statements.append(
                (
                    "if",
                    (_translate_expression(source[opening + 1 : closing]),
                     _parse_statements(source[brace + 1 : end])),
                )
            )
            index = end + 1
            continue
        statement, index = _read_statement(source, index)
        if statement:
            statements.append(("statement", statement))
    return statements


def _emit_statements(statements: list[tuple[str, Any]], indent: int = 1) -> list[str]:
    lines: list[str] = []
    prefix = "    " * indent
    for kind, value in statements:
        if kind == "if":
            condition, nested = value
            lines.append(f"{prefix}if {condition}:")
            lines.extend(_emit_statements(nested, indent + 1))
            continue
        statement = value.strip()
        destructured = re.match(
            r"^(?:const|let|var)\s*\{\s*([A-Za-z_$][\w$]*)\s*\}\s*=\s*(.*)$",
            statement,
            flags=re.S,
        )
        if destructured:
            name, expression = destructured.groups()
            temporary = f"_destructured_{name}"
            lines.append(f"{prefix}{temporary} = {_translate_expression(expression)}")
            lines.append(f'{prefix}{name} = _member({temporary}, "{name}")')
            continue
        if statement.startswith("return"):
            expression = statement[len("return") :].strip()
            lines.append(f"{prefix}return {_translate_expression(expression)}")
        else:
            statement = re.sub(r"^(const|let|var)\s+", "", statement)
            lines.append(f"{prefix}{_translate_expression(statement)}")
    return lines


def _compile_special_function(source: str) -> Callable[..., Any] | None:
    if "lodash.forEach('一二三'.split('')," in source:

        def calculate(context: DamageContext, methods: DamageMethods):
            result = {"dmg": 0, "avg": 0}
            for number in "一二三":
                damage = methods(
                    context.talent("a", f"{number}段伤害"),
                    "a",
                )
                result["dmg"] += damage.dmg
                result["avg"] += damage.avg
            if context.cons > 0:
                damage = methods.basic(methods.context.attr.hp * 0.3)
                result["dmg"] += damage.dmg
                result["avg"] += damage.avg
            return result

        return calculate

    if "let buffCount = 12" in source and "光降之剑" in source:

        def create_eula_detail(context: DamageContext, methods=None):
            buff_count = 12
            if context.weapon.get("名称") == "松籁响起之时":
                buff_count = 13
                if int(context.weapon.get("精炼等级", 1)) >= 4:
                    buff_count = 14
            if context.cons == 6:
                buff_count += 11

            def calculate(detail_context: DamageContext, detail_methods: DamageMethods):
                return detail_methods(
                    detail_context.talent("q", "光降之剑基础伤害")
                    + detail_context.talent("q", "每层能量伤害") * buff_count,
                    "q",
                    "phy",
                )

            return {
                "title": f"光降之剑{buff_count}层伤害",
                "params": {"gj": True},
                "dmg": calculate,
            }

        return create_eula_detail

    if "title: `${cons === 6 ? '半血' : ''}Q每跳治疗`" in source:

        def create_diona_detail(context: DamageContext, methods=None):
            def calculate(detail_context: DamageContext, detail_methods: DamageMethods):
                return detail_methods.heal(
                    detail_context.talent("q", "持续治疗量2")[0]
                    * detail_context.attr.hp
                    / 100
                    + detail_context.talent("q", "持续治疗量2")[1]
                )

            return {
                "title": f"{'半血' if context.cons == 6 else ''}Q每跳治疗",
                "dmg": calculate,
            }

        return create_diona_detail

    if "let count = cons === 6 ? 4 : 3" in source:

        def create_chongyun_detail(context: DamageContext, methods=None):
            count = 4 if context.cons == 6 else 3

            def calculate(detail_context: DamageContext, detail_methods: DamageMethods):
                return detail_methods(
                    detail_context.talent("q", "技能伤害") * count,
                    "q",
                )

            return {
                "title": f"Q {count}柄灵刃总伤害",
                "dmg": calculate,
            }

        return create_chongyun_detail
    return None


def compile_js_function(source: str) -> Callable[..., Any]:
    source = _strip_comments(source.strip())
    special = _compile_special_function(source)
    if special:
        return special
    arrow = source.find("=>")
    if arrow < 0:
        raise SyntaxError(f"invalid Miao function: {source}")
    body = source[arrow + 2 :].strip()
    if body.startswith("{"):
        body_end = _find_matching(body, 0, "{", "}")
        body = body[1:body_end]
        lines = _emit_statements(_parse_statements(body))
    else:
        lines = [f"    return {_translate_expression(body)}"]
    if not any(line.strip().startswith("return ") for line in lines):
        lines.append("    return None")

    function_source = "def _generated(context, methods=None):\n"
    function_source += "    attr = _AttrView(context)\n"
    function_source += "    talent = _TalentView(context)\n"
    function_source += "    params = _ParamsView(context)\n"
    function_source += "    weapon = _WeaponView(context)\n"
    function_source += "    cons = context.cons\n"
    function_source += "    level = context.level\n"
    function_source += "    refine = max(0, int(context.weapon.get('精炼等级', 1)) - 1)\n"
    function_source += "    element = context.element\n"
    function_source += "    characterName = context.name\n"
    function_source += "    weaponTypeName = context.weapon.get('类型', context.weapon.get('武器类型', ''))\n"
    function_source += "    currentTalent = context.state.get('currentTalent', '')\n"
    function_source += "    mastery = context.state.get('mastery', '')\n"
    function_source += "    calc = _calc_value\n"
    function_source += "    step = _step\n"
    function_source += "    dmg = methods\n"
    function_source += "    basic = methods.basic if methods else None\n"
    function_source += "    dynamic = methods.dynamic if methods else None\n"
    function_source += "    reaction = methods.reaction if methods else None\n"
    function_source += "    heal = methods.heal if methods else None\n"
    function_source += "    shield = methods.shield if methods else None\n"
    function_source += "    swirl = methods.swirl if methods else None\n"
    function_source += "    trees = context.params\n"
    function_source += "    state = context.state\n"
    function_source += "    game = 'gs'\n"
    function_source += "    _ = None\n"
    function_source += "\n".join(lines) + "\n"
    namespace = {
        "_AttrView": _AttrView,
        "_TalentView": _TalentView,
        "_ParamsView": _ParamsView,
        "_WeaponView": _WeaponView,
        "_calc_value": _calc_value,
        "_step": _step,
        "_js_floor": _js_floor,
        "_js_min": _js_min,
        "_js_max": _js_max,
        "_includes": _includes,
        "_member": _member,
        "_format_percent": _format_percent,
        "_js_add": _js_add,
        "_js_nullish": _js_nullish,
        "_JS_UNDEFINED": _JS_UNDEFINED,
        "math": math,
        "min": min,
        "max": max,
        "pow": pow,
        "round": round,
    }
    try:
        exec(function_source, namespace)
    except SyntaxError as error:
        raise SyntaxError(f"failed to translate Miao function {source}: {error}") from error
    return namespace["_generated"]


@dataclass
class DamageMethods:
    context: DamageContext
    calculator: Any

    def __call__(
        self,
        multiplier: float = 0,
        talent: str | bool = False,
        element: str | bool = False,
        basic_num: float = 0,
        mode: str = "talent",
        dynamic_data: dict[str, Any] | bool = False,
    ) -> DamageResult:
        data = dynamic_data if isinstance(dynamic_data, dict) else {}
        tokens = element.split(",") if isinstance(element, str) else []
        physical = "phy" in tokens
        coloring = "coloringDmg" in tokens
        scene = "scene" in tokens
        reaction = next(
            (
                token
                for token in tokens
                if token not in {"", "phy", "scene", "coloringDmg"}
            ),
            None,
        )
        if mode == "basic":
            return self.calculator.calculate(
                talents=str(talent or ""),
                reaction=reaction,
                base=float(basic_num),
                physical=physical,
                dynamic_dmg=float(data.get("dynamicDmg", 0)),
                dynamic_phy=float(data.get("dynamicPhy", 0)),
                dynamic_cpct=float(data.get("dynamicCpct", 0)),
                dynamic_cdmg=float(data.get("dynamicCdmg", 0)),
                dynamic_enemy_damage=float(data.get("dynamicEnemydmg", 0)),
                coloring=coloring,
                scene=scene,
            )
        return self.calculator.calculate(
            multiplier=float(multiplier),
            talents=str(talent or ""),
            reaction=reaction,
            physical=physical,
            dynamic_dmg=float(data.get("dynamicDmg", 0)),
            dynamic_phy=float(data.get("dynamicPhy", 0)),
            dynamic_cpct=float(data.get("dynamicCpct", 0)),
            dynamic_cdmg=float(data.get("dynamicCdmg", 0)),
            dynamic_enemy_damage=float(data.get("dynamicEnemydmg", 0)),
            coloring=coloring,
            scene=scene,
        )

    def basic(
        self,
        value: float = 0,
        talent: str | bool = False,
        element: str | bool = False,
        dynamic_data: dict[str, Any] | bool = False,
    ) -> DamageResult:
        return self(value, talent, element, value, "basic", dynamic_data)

    def dynamic(
        self,
        multiplier: float = 0,
        talent: str | bool = False,
        dynamic_data: dict[str, Any] | bool = False,
        element: str | bool = False,
    ) -> DamageResult:
        return self(multiplier, talent, element, 0, "talent", dynamic_data)

    def reaction(self, element: str = "", talent: str = "fy") -> DamageResult:
        return self(0, talent, element, 0, "basic", False)

    def heal(self, value: float) -> DamageResult:
        return self.calculator.heal(float(value))

    def shield(self, value: float) -> DamageResult:
        return self.calculator.shield(float(value))

    def swirl(self) -> DamageResult:
        return self.reaction("swirl")


def invoke_rule(function: Callable[..., Any], context: DamageContext, methods=None):
    return function(context, methods)


def resolve_value(value: Any) -> Any:
    if isinstance(value, list):
        return [resolve_value(item) for item in value]
    if isinstance(value, dict):
        if "__expression__" in value:
            expression = _translate_expression(value["__expression__"])
            return eval(
                expression,
                {
                    "math": math,
                    "min": min,
                    "max": max,
                    "pow": pow,
                    "round": round,
                },
            )
        if "__function__" in value:
            return compile_js_function(value["__function__"])
        return {key: resolve_value(item) for key, item in value.items()}
    return value


def invoke_compiled(function: Callable[..., Any], context: DamageContext, methods=None):
    return function(context, methods)
