import ast
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parents[1]
    / "genshin_role_info"
    / "utils"
    / "card_utils.py"
)


def test_resolve_ice_traveler_from_current_skill_ids() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "resolve_traveler_role"
    )
    namespace = {
        "role_info_json": {
            "风主": {"技能": {"10067": "wind"}},
            "冰主": {"技能": {"10127": "ice-e", "10128": "ice-q"}},
        }
    }
    exec(compile(ast.Module([function], type_ignores=[]), MODULE_PATH, "exec"), namespace)

    assert namespace["resolve_traveler_role"](
        {"10127": 6, "10128": 5, "100554": 1}
    ) == "冰主"
