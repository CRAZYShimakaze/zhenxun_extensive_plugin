from __future__ import annotations


class MerchantQueryError(RuntimeError):
    """远行商人接口异常。"""


class PetWikiQueryError(RuntimeError):
    """精灵图鉴接口异常。"""


class PetWikiNotFoundError(PetWikiQueryError):
    """未找到匹配精灵。"""


class EggSizeQueryError(RuntimeError):
    """查蛋尺寸反查接口异常。"""


class PlayerQueryError(RuntimeError):
    """玩家 ingame 查询接口异常。"""
