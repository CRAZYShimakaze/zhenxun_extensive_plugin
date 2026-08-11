from __future__ import annotations


# Genshin reaction level multipliers, synchronized from Miao-Plugin DmgCalcMeta.
ELEMENT_BASE_DAMAGE = {
    1: 4.291,
    2: 4.634,
    3: 4.976,
    4: 5.319,
    5: 5.661,
    6: 6.162,
    7: 6.660,
    8: 7.217,
    9: 7.842,
    10: 8.536,
    11: 9.300,
    12: 10.165,
    13: 11.112,
    14: 12.141,
    15: 13.437,
    16: 14.770,
    17: 16.105,
    18: 17.431,
    19: 18.781,
    20: 20.146,
    21: 21.528,
    22: 22.926,
    23: 24.311,
    24: 25.703,
    25: 27.102,
    26: 28.300,
    27: 29.526,
    28: 30.745,
    29: 32.432,
    30: 34.073,
    31: 35.668,
    32: 37.257,
    33: 38.854,
    34: 40.456,
    35: 42.277,
    36: 44.130,
    37: 46.018,
    38: 47.927,
    39: 49.889,
    40: 51.846,
    41: 53.850,
    42: 56.041,
    43: 58.376,
    44: 60.838,
    45: 64.016,
    46: 67.136,
    47: 70.382,
    48: 73.753,
    49: 77.267,
    50: 80.9,
    51: 84.189,
    52: 87.633,
    53: 91.121,
    54: 94.655,
    55: 99.650,
    56: 104.100,
    57: 108.597,
    58: 113.238,
    59: 118.152,
    60: 123.221,
    61: 128.392,
    62: 134.776,
    63: 141.378,
    64: 148.135,
    65: 156.111,
    66: 162.868,
    67: 169.874,
    68: 176.949,
    69: 184.168,
    70: 191.41,
    71: 198.693,
    72: 206.169,
    73: 212.789,
    74: 219.436,
    75: 228.557,
    76: 236.687,
    77: 244.853,
    78: 252.806,
    79: 261.198,
    80: 269.361,
    81: 277.499,
    82: 285.744,
    83: 294.092,
    84: 302.546,
    85: 313.459,
    86: 322.238,
    87: 331.371,
    88: 340.864,
    89: 351.274,
    90: 361.713,
    95: 390.367,
    100: 418.522,
}

# Miao's crystallize shield base values.  Unlike transformative reactions,
# crystallize uses its own level table rather than the elemental reaction table.
CRYSTALLIZE_BASE_DAMAGE = {
    1: 91.18,
    2: 98.71,
    3: 106.24,
    4: 113.76,
    5: 121.29,
    6: 128.82,
    7: 136.35,
    8: 143.88,
    9: 151.41,
    10: 158.94,
    11: 169.99,
    12: 181.08,
    13: 192.19,
    14: 204.05,
    15: 215.94,
    16: 227.86,
    17: 247.69,
    18: 267.54,
    19: 287.43,
    20: 303.83,
    21: 320.23,
    22: 336.63,
    23: 352.32,
    24: 368.01,
    25: 383.70,
    26: 394.43,
    27: 405.18,
    28: 415.95,
    29: 426.74,
    30: 437.54,
    31: 450.60,
    32: 463.70,
    33: 476.85,
    34: 491.13,
    35: 502.55,
    36: 514.01,
    37: 531.41,
    38: 549.98,
    39: 568.58,
    40: 585.00,
    41: 605.67,
    42: 626.39,
    43: 646.05,
    44: 665.76,
    45: 685.50,
    46: 700.84,
    47: 723.33,
    48: 745.87,
    49: 768.44,
    50: 786.79,
    51: 809.54,
    52: 832.33,
    53: 855.16,
    54: 878.04,
    55: 899.48,
    56: 919.36,
    57: 946.04,
    58: 974.76,
    59: 1003.58,
    60: 1030.08,
    61: 1056.64,
    62: 1085.25,
    63: 1113.92,
    64: 1149.26,
    65: 1178.06,
    66: 1200.22,
    67: 1227.66,
    68: 1257.24,
    69: 1284.92,
    70: 1314.75,
    71: 1342.67,
    72: 1372.75,
    73: 1396.32,
    74: 1427.31,
    75: 1458.37,
    76: 1482.34,
    77: 1511.91,
    78: 1541.55,
    79: 1569.15,
    80: 1596.15,
    81: 1622.42,
    82: 1648.07,
    83: 1666.38,
    84: 1684.68,
    85: 1702.98,
    86: 1726.10,
    87: 1754.67,
    88: 1785.87,
    89: 1817.14,
    90: 1851.06,
}

REACTION_TYPE = {
    "vaporize": ("pct", {"水": 2.0, "default": 1.5}),
    "melt": ("pct", {"火": 2.0, "default": 1.5}),
    "crystallize": ("shield", 1.0),
    "burning": ("fusion", 1.0),
    "superConduct": ("fusion", 6.0),
    "swirl": ("fusion", 2.4),
    "electroCharged": ("fusion", 8.0),
    "shatter": ("fusion", 12.0),
    "overloaded": ("fusion", 11.0),
    "bloom": ("fusion", 8.0),
    "burgeon": ("fusion", 12.0),
    "hyperBloom": ("fusion", 12.0),
    "aggravate": ("bonus", 4.6),
    "spread": ("bonus", 5.0),
    "lunarBloom": ("lunar", 8.0),
    "lunarCharged": ("lunar", 7.2),
    "lunarCrystallize": ("lunar", 3.84),
    "stellarConduct": ("stellar", 0.0),
}

REACTION_NAMES = {
    "蒸发": "vaporize",
    "融化": "melt",
    "超激化": "aggravate",
    "蔓激化": "spread",
    "扩散": "swirl",
    "超载": "overloaded",
    "感电": "electroCharged",
    "超导": "superConduct",
    "绽放": "bloom",
    "烈绽放": "burgeon",
    "超绽放": "hyperBloom",
    "月绽放": "lunarBloom",
    "月感电": "lunarCharged",
    "月结晶": "lunarCrystallize",
    "星超导": "stellarConduct",
}


def level_base_damage(level: int) -> float:
    if level in ELEMENT_BASE_DAMAGE:
        return ELEMENT_BASE_DAMAGE[level]
    points = sorted(ELEMENT_BASE_DAMAGE)
    left = max((point for point in points if point < level), default=points[0])
    right = min((point for point in points if point > level), default=points[-1])
    if left == right:
        return ELEMENT_BASE_DAMAGE[left]
    ratio = (level - left) / (right - left)
    return (
        ELEMENT_BASE_DAMAGE[left]
        + (ELEMENT_BASE_DAMAGE[right] - ELEMENT_BASE_DAMAGE[left]) * ratio
    )


def crystallize_base_damage(level: int) -> float:
    if level in CRYSTALLIZE_BASE_DAMAGE:
        return CRYSTALLIZE_BASE_DAMAGE[level]
    points = sorted(CRYSTALLIZE_BASE_DAMAGE)
    left = max((point for point in points if point < level), default=points[0])
    right = min((point for point in points if point > level), default=points[-1])
    if left == right:
        return CRYSTALLIZE_BASE_DAMAGE[left]
    ratio = (level - left) / (right - left)
    return CRYSTALLIZE_BASE_DAMAGE[left] + (
        CRYSTALLIZE_BASE_DAMAGE[right] - CRYSTALLIZE_BASE_DAMAGE[left]
    ) * ratio


def mastery_multiplier(reaction_type: str, mastery: float) -> float:
    mastery = max(0, mastery)
    if reaction_type == "pct":
        return (25 / 9) * mastery / (mastery + 1400)
    if reaction_type == "fusion":
        return 16 * mastery / (mastery + 2000)
    if reaction_type in {"lunar", "stellar"}:
        return 6 * mastery / (mastery + 2000)
    if reaction_type == "bonus":
        return 5 * mastery / (mastery + 1200)
    if reaction_type == "shield":
        return (40 / 9) * mastery / (mastery + 1400)
    return 0


def reaction_config(name: str, element: str) -> tuple[str, float]:
    key = REACTION_NAMES.get(name, name)
    reaction_type, coefficient = REACTION_TYPE[key]
    if isinstance(coefficient, dict):
        coefficient = coefficient.get(element, coefficient["default"])
    return reaction_type, coefficient
