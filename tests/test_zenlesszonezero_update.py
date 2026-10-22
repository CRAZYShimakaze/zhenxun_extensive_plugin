import ast
import asyncio
import copy
import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


MODULE_PATH = Path(__file__).parents[1] / "zenlesszonezero_role_info" / "__init__.py"


class UpdateFinished(Exception):
    pass


def _load_update(roles):
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_enka_info"
    )
    player = Mock()
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"PlayerInfo": {"ShowcaseDetail": {"AvatarList": roles}}},
    )
    matcher = SimpleNamespace(
        send=AsyncMock(), finish=AsyncMock(side_effect=UpdateFinished),
    )
    namespace = {
        "os": SimpleNamespace(path=SimpleNamespace(exists=lambda path: False)),
        "player_info_path": "unused",
        "api_url": ["https://example.com/{}"],
        "client": SimpleNamespace(get=AsyncMock(return_value=response)),
        "headers": {},
        "PlayerInfo": lambda uid: player,
        "get_name_by_id": lambda role_id: ("已收录角色", {}) if role_id == "1" else (None, None),
        "get_card": matcher,
    }
    exec(compile(ast.Module([function], type_ignores=[]), MODULE_PATH, "exec"), namespace)
    return namespace["get_enka_info"], player, matcher


def test_update_skips_unknown_roles_and_keeps_known_roles():
    known = {"Id": 1}
    update, player, matcher = _load_update([{"Id": 999999}, known])

    result, roles = asyncio.run(update("test-uid", True, None))

    assert result is player
    assert roles == ["已收录角色"]
    player.set_role.assert_called_once_with(known)
    player.save.assert_called_once()
    assert "999999" in matcher.send.call_args.args[0]
    matcher.finish.assert_not_called()


def test_update_with_only_unknown_roles_reports_failure_without_saving():
    update, player, matcher = _load_update([{"Id": 999999}])

    with pytest.raises(UpdateFinished):
        asyncio.run(update("test-uid", True, None))

    player.set_role.assert_not_called()
    player.save.assert_not_called()
    assert "没有可更新的角色" in matcher.finish.call_args.args[0]


PLUGIN_PATH = MODULE_PATH.parent
MODULE_PATH_CARD_UTILS = PLUGIN_PATH / "utils" / "card_utils.py"


def _load_card_utils(monkeypatch):
    package_name = "zenlesszonezero_card_utils_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_PATH)]
    utils_package = types.ModuleType(f"{package_name}.utils")
    utils_package.__path__ = [str(PLUGIN_PATH / "utils")]
    json_utils = types.ModuleType(f"{package_name}.utils.json_utils")

    def load_json(path, encoding="utf-8"):
        return json.loads(Path(path).read_text(encoding=encoding))

    json_utils.load_json = load_json
    json_utils.save_json = lambda data, path=None, encoding="utf-8": None
    monkeypatch.setitem(sys.modules, package_name, package)
    monkeypatch.setitem(sys.modules, utils_package.__name__, utils_package)
    monkeypatch.setitem(sys.modules, json_utils.__name__, json_utils)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.utils.card_utils", MODULE_PATH_CARD_UTILS
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_check_artifact():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "check_artifact"
    )

    async def draw_role_card(*args, **kwargs):
        return None, None

    namespace = {
        "copy": copy,
        "pos_name": [1, 2, 3, 4, 5, 6],
        "draw_role_card": draw_role_card,
        "__plugin_version__": "test",
        "check_group_artifact": lambda *args: None,
    }
    exec(
        compile(ast.Module([function], type_ignores=[]), MODULE_PATH, "exec"),
        namespace,
    )
    return namespace["check_artifact"]


def test_check_artifact_skips_missing_role_data(monkeypatch) -> None:
    import asyncio

    card_utils = _load_card_utils(monkeypatch)
    monkeypatch.setattr(card_utils, "load_json", lambda path: {})
    monkeypatch.setattr(card_utils, "save_json", lambda data, path=None: None)
    player = card_utils.PlayerInfo("test-uid")

    asyncio.run(_load_check_artifact()(None, player, [None, "未收录角色"], "test-uid", False))

    assert player.data["驱动盘列表"] == [[], [], [], [], [], []]


def test_pheony_and_signature_weapon_can_be_parsed(monkeypatch) -> None:
    card_utils = _load_card_utils(monkeypatch)
    load_json = card_utils.load_json
    monkeypatch.setattr(
        card_utils, "load_json",
        lambda path: {} if str(path).endswith("test-uid.json") else load_json(path),
    )
    player = card_utils.PlayerInfo("test-uid")
    player.set_role({
        "Id": 1641,
        "Level": 60,
        "PromotionLevel": 6,
        "CoreSkillEnhancement": 6,
        "TalentLevel": 0,
        "SkillLevelList": [],
        "Weapon": {"Id": 14164, "Level": 60, "BreakLevel": 5, "UpgradeLevel": 1},
    })

    role = player.get_roles_info("菲欧妮")
    assert role["特性"] == "异常"
    assert role["元素"] == "Fire"
    assert role["武器"]["名称"] == "涅槃初翎"
    assert card_utils.dictlist_to_list([{"Id": 1641}, {"Id": 999999}]) == ["菲欧妮"]
