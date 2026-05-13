from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .common import (
    _absolute_asset_url,
    _as_list,
    _build_stat_rows,
    _cn_now,
    _display_number,
    _normalize_query_text,
    _normalize_type_values,
    _number_digits,
    _skill_category_class,
    _to_int,
)
from .constants import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_KEY,
    DEFAULT_TIMEOUT,
    DEFAULT_WIKI_BASE_URL,
    WEGAME_WIKI_RETRY_SECONDS,
    WIKI_CACHE_TTL_SECONDS,
)
from .errors import PetWikiNotFoundError, PetWikiQueryError
from .rendering import _inline_pet_wiki_images, _render_pet_wiki_image

_WALKTHROUGH_CACHE: dict[str, Any] = {}
_WALKTHROUGH_CACHE_EXPIRE_AT = 0.0
_WEGAME_WIKI_DISABLED_UNTIL = 0.0

def _extract_wegame_wiki_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "results", "list", "pets", "records", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []

def _find_matching_pet(
    items: list[dict[str, Any]],
    query: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    normalized_query = _normalize_query_text(query)
    query_digits = _number_digits(query)
    if not normalized_query:
        return None, []

    exact_hits: list[dict[str, Any]] = []
    fuzzy_hits: list[dict[str, Any]] = []
    for item in items:
        name = str(item.get("name") or item.get("pet_name") or "").strip()
        form = str(item.get("formName") or item.get("form") or "").strip()
        number = item.get("no") or item.get("number") or item.get("pet_id") or item.get("id")
        name_key = _normalize_query_text(name)
        candidates = {
            name_key,
            _normalize_query_text(f"{name}{form}"),
            _normalize_query_text(f"{name} {form}"),
            _normalize_query_text(number),
        }
        number_key = _number_digits(number)
        if normalized_query in candidates or (query_digits and query_digits == number_key):
            exact_hits.append(item)
            continue
        if name_key and (normalized_query in name_key or name_key in normalized_query):
            fuzzy_hits.append(item)

    if len(exact_hits) == 1:
        return exact_hits[0], []
    if len(exact_hits) > 1:
        return None, exact_hits[:8]
    if len(fuzzy_hits) == 1:
        return fuzzy_hits[0], []
    return None, fuzzy_hits[:8]

def _ambiguous_message(items: list[dict[str, Any]]) -> str:
    names = []
    for item in items[:8]:
        name = item.get("name") or item.get("pet_name") or "未知精灵"
        form = item.get("formName") or item.get("form") or ""
        label = f"{name}（{form}）" if form and form != "原始形态" else str(name)
        if label not in names:
            names.append(label)
    return "找到多个匹配：" + "、".join(names) + "，请发送更完整的精灵名。"

async def _fetch_wegame_wiki_pet(
    api_base_url: str,
    api_key: str,
    query: str,
) -> dict[str, Any] | None:
    global _WEGAME_WIKI_DISABLED_UNTIL
    if _WEGAME_WIKI_DISABLED_UNTIL > time.time():
        return None

    url = f"{api_base_url.rstrip('/')}/api/v1/games/rocom/wiki/pet"
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                url,
                headers=headers,
                params={"q": query, "limit": 10},
            )
            data = response.json()
    except Exception:
        _WEGAME_WIKI_DISABLED_UNTIL = time.time() + WEGAME_WIKI_RETRY_SECONDS
        return None

    if isinstance(data, dict) and data.get("code") not in (None, 0):
        return None
    payload = data.get("data") if isinstance(data, dict) and "data" in data else data
    items = _extract_wegame_wiki_items(payload)
    if not items:
        return None
    item, ambiguous = _find_matching_pet(items, query)
    if ambiguous:
        raise PetWikiQueryError(_ambiguous_message(ambiguous))
    if not item:
        return None
    return _build_api_wiki_render_data(item, query)

async def _fetch_walkthrough_json(base_url: str, endpoint: str, default: Any) -> Any:
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url)
            data = response.json()
    except Exception:
        data = None
    return default if data is None else data

def _walkthrough_cache_is_fresh(base_url: str) -> bool:
    return (
        bool(_WALKTHROUGH_CACHE)
        and _WALKTHROUGH_CACHE_EXPIRE_AT > time.time()
        and _WALKTHROUGH_CACHE.get("base_url") == base_url.rstrip("/")
    )

async def _fetch_walkthrough_index(base_url: str) -> dict[str, Any]:
    global _WALKTHROUGH_CACHE, _WALKTHROUGH_CACHE_EXPIRE_AT
    now = time.time()
    if _walkthrough_cache_is_fresh(base_url) and _WALKTHROUGH_CACHE.get("pokemon"):
        return _WALKTHROUGH_CACHE

    pokemon_res = await _fetch_walkthrough_json(base_url, "/api/pokemon", {})
    pokemon = pokemon_res.get("pokemon") if isinstance(pokemon_res, dict) else []
    if not isinstance(pokemon, list) or not pokemon:
        raise PetWikiQueryError("精灵数据源暂时不可用")

    _WALKTHROUGH_CACHE = {
        "pokemon": [item for item in pokemon if isinstance(item, dict)],
        "details": {},
        "skills": {},
        "sprite_map": {},
        "details_ready": False,
        "base_url": base_url.rstrip("/"),
    }
    _WALKTHROUGH_CACHE_EXPIRE_AT = now + WIKI_CACHE_TTL_SECONDS
    return _WALKTHROUGH_CACHE

async def _fetch_walkthrough_data(base_url: str) -> dict[str, Any]:
    global _WALKTHROUGH_CACHE, _WALKTHROUGH_CACHE_EXPIRE_AT
    cache = await _fetch_walkthrough_index(base_url)
    if cache.get("details_ready"):
        return cache

    pokemon_res, details_res, skills_res, sprite_map = await asyncio.gather(
        _fetch_walkthrough_json(base_url, "/api/pokemon", {}),
        _fetch_walkthrough_json(base_url, "/api/details", {}),
        _fetch_walkthrough_json(base_url, "/api/skills", {}),
        _fetch_walkthrough_json(base_url, "/data/sprite-map.json", {}),
    )
    pokemon = pokemon_res.get("pokemon") if isinstance(pokemon_res, dict) else cache.get("pokemon", [])
    if not isinstance(pokemon, list) or not pokemon:
        raise PetWikiQueryError("精灵数据源暂时不可用")

    _WALKTHROUGH_CACHE = {
        "pokemon": [item for item in pokemon if isinstance(item, dict)],
        "details": details_res if isinstance(details_res, dict) else {},
        "skills": skills_res if isinstance(skills_res, dict) else {},
        "sprite_map": sprite_map if isinstance(sprite_map, dict) else {},
        "details_ready": True,
        "base_url": base_url.rstrip("/"),
    }
    _WALKTHROUGH_CACHE_EXPIRE_AT = time.time() + WIKI_CACHE_TTL_SECONDS
    return _WALKTHROUGH_CACHE

def _build_api_wiki_evolution_data(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_chain = (
        item.get("evolution_chain")
        or item.get("evolutionChain")
        or item.get("evolutions")
        or item.get("evolution")
        or []
    )
    chain = []
    for evo in _as_list(raw_chain):
        if not isinstance(evo, dict):
            continue
        evo_name = evo.get("name") or evo.get("pet_name") or "未知形态"
        evo_number = evo.get("no") or evo.get("number") or evo.get("pet_id") or item.get("no")
        chain.append(
            {
                "name": evo_name,
                "number": _display_number(evo_number),
                "image": evo.get("image") or evo.get("image_url") or "",
                "icon": evo.get("icon") or evo.get("icon_url") or "",
                "condition": evo.get("condition") or evo.get("how") or evo.get("requirement") or "",
                "is_current": bool(
                    evo.get("is_current")
                    or evo_name == item.get("name")
                    or evo_number == item.get("no")
                ),
            }
        )
    if chain:
        return chain
    return [
        {
            "name": item.get("name", "未知精灵"),
            "number": _display_number(item.get("no") or item.get("number")),
            "image": item.get("image_url") or item.get("pet_image") or "",
            "icon": item.get("icon_url") or item.get("pet_icon") or "",
            "condition": "",
            "is_current": True,
        }
    ]

def _build_api_wiki_render_data(item: dict[str, Any], query: str) -> dict[str, Any]:
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    pet_stats, total_stats = _build_stat_rows(stats)
    skills = item.get("skills") or item.get("skill_list") or []
    sprite_skills = []
    for skill in _as_list(skills)[:24]:
        if isinstance(skill, str):
            skill_data = {"name": skill}
        elif isinstance(skill, dict):
            skill_data = skill
        else:
            continue
        category = str(skill_data.get("category") or skill_data.get("type") or "未知")
        sprite_skills.append(
            {
                "name": skill_data.get("name", "未知技能"),
                "type": skill_data.get("attribute") or skill_data.get("attr") or "未知",
                "category": category,
                "category_class": _skill_category_class(category),
                "power": skill_data.get("power", "?"),
                "pp": skill_data.get("cost") or skill_data.get("consume") or "?",
                "effect": skill_data.get("description") or skill_data.get("desc") or "暂无描述",
                "level": skill_data.get("level", "-"),
                "icon": skill_data.get("icon") or skill_data.get("icon_url") or "",
            }
        )
    ability_name = item.get("ability_name") or item.get("ability") or "暂无"
    ability_desc = item.get("ability_desc") or item.get("ability_description") or "暂无特性描述"
    pet_types = [
        {"name": attr}
        for attr in _normalize_type_values(item.get("attributes") or item.get("types"))
    ] or [{"name": "未知"}]
    matchup = item.get("type_matchup") or {}
    traits = [{"name": ability_name, "type": "特性", "effect": ability_desc}]
    for label, key in [
        ("克制", "strong_against"),
        ("被克制", "weak_to"),
        ("抗性", "resists"),
        ("被抗", "resisted_by"),
    ]:
        values = _normalize_type_values(matchup.get(key))
        traits.append({"name": label, "type": "属性", "effect": "、".join(values) if values else "暂无"})
    description = (
        item.get("description")
        or item.get("summary")
        or item.get("intro")
        or item.get("profile")
        or f"{item.get('name', query)} 的图鉴信息。"
    )
    return {
        "name": item.get("name", query),
        "number": _display_number(item.get("no") or item.get("number") or item.get("pet_id")),
        "query": query,
        "form": item.get("form", ""),
        "kind": item.get("typeName") or item.get("type_name") or "",
        "pet_types": pet_types,
        "pet_icon": item.get("icon_url") or item.get("pet_icon") or item.get("image_url") or "",
        "main_image": item.get("image_url") or item.get("pet_image") or item.get("icon_url") or "",
        "total_stats": total_stats,
        "pet_stats": pet_stats,
        "description": description,
        "pet_traits": traits,
        "pet_evolution": _build_api_wiki_evolution_data(item),
        "sprite_skills": sprite_skills,
        "skill_total_count": len(_as_list(skills)),
        "updated_at": item.get("updated_at") or _cn_now().strftime("%Y-%m-%d %H:%M"),
        "wiki_url": item.get("url", ""),
        "command_hint": f"{query}图鉴",
        "data_source": DEFAULT_API_BASE_URL,
    }

def _build_walkthrough_evolution_data(
    pokemon: dict[str, Any],
    detail: dict[str, Any],
    base_url: str,
) -> list[dict[str, Any]]:
    evolution = detail.get("evolution") if isinstance(detail.get("evolution"), dict) else {}
    stages = [
        ("base", ""),
        ("stage2", f"{evolution.get('level2')}级进化" if evolution.get("level2") else "进化"),
        ("stage3", f"{evolution.get('level3')}级进化" if evolution.get("level3") else "进化"),
    ]
    chain = []
    current_name = pokemon.get("name")
    current_no = pokemon.get("no")
    for key, condition in stages:
        for evo in _as_list(evolution.get(key)):
            if not isinstance(evo, dict):
                continue
            evo_name = evo.get("name") or "未知形态"
            evo_no = evo.get("no") or ""
            chain.append(
                {
                    "name": evo_name,
                    "number": _display_number(evo_no),
                    "image": _absolute_asset_url(evo.get("image"), base_url),
                    "icon": _absolute_asset_url(evo.get("image"), base_url),
                    "condition": condition if key != "base" else "",
                    "is_current": evo_name == current_name or evo_no == current_no,
                }
            )
    if chain:
        return chain
    image = _absolute_asset_url(pokemon.get("image"), base_url)
    return [
        {
            "name": pokemon.get("name", "未知精灵"),
            "number": _display_number(pokemon.get("no")),
            "image": image,
            "icon": image,
            "condition": "",
            "is_current": True,
        }
    ]

def _build_walkthrough_render_data(
    pokemon: dict[str, Any],
    details: dict[str, Any],
    skills_db: dict[str, Any],
    sprite_map: dict[str, Any],
    base_url: str,
    query: str,
) -> dict[str, Any]:
    name = str(pokemon.get("name") or query)
    detail = details.get(name) if isinstance(details.get(name), dict) else {}
    stats = detail.get("stats") if isinstance(detail.get("stats"), dict) else {}
    pet_stats, total_stats = _build_stat_rows(stats)
    trait = detail.get("trait") if isinstance(detail.get("trait"), dict) else {}
    restrain = detail.get("restrain") if isinstance(detail.get("restrain"), dict) else {}
    attr_names = _normalize_type_values(pokemon.get("attrNames"))
    type_name = pokemon.get("typeName") or ""
    form_name = pokemon.get("formName") or ""
    attr_text = "、".join(attr_names)
    description_parts = []
    if attr_text or type_name:
        description_parts.append(f"{name} 是洛克王国世界{attr_text + '系' if attr_text else ''}{type_name or '精灵'}。")
    if form_name and form_name != "原始形态":
        description_parts.append(f"形态：{form_name}。")
    if trait.get("name"):
        description_parts.append(f"特性：{trait.get('name')}，{trait.get('desc') or '暂无描述'}")
    description = "".join(description_parts) or f"{name} 的图鉴信息。"

    traits = [
        {
            "name": trait.get("name") or "暂无",
            "type": "特性",
            "effect": trait.get("desc") or "暂无特性描述",
        }
    ]
    for label, key in [
        ("克制", "strongAgainst"),
        ("被克制", "weakAgainst"),
        ("抗性", "resist"),
        ("被抗", "resisted"),
    ]:
        values = _normalize_type_values(restrain.get(key))
        traits.append({"name": label, "type": "属性", "effect": "、".join(values) if values else "暂无"})

    skill_names = _as_list(detail.get("skills"))
    sprite_skills = []
    for skill_name in skill_names[:24]:
        skill = skills_db.get(str(skill_name))
        skill = skill if isinstance(skill, dict) else {"name": str(skill_name)}
        category = str(skill.get("type") or "未知")
        sprite_skills.append(
            {
                "name": skill.get("name") or str(skill_name),
                "type": skill.get("attr") or "未知",
                "category": category,
                "category_class": _skill_category_class(category),
                "power": skill.get("power") if skill.get("power") not in (None, "") else "?",
                "pp": skill.get("consume") if skill.get("consume") not in (None, "") else "?",
                "effect": skill.get("desc") or "暂无描述",
                "level": "-",
                "icon": _absolute_asset_url(skill.get("icon"), base_url),
            }
        )

    main_image = _absolute_asset_url(sprite_map.get(name) or pokemon.get("image"), base_url)
    pet_icon = _absolute_asset_url(pokemon.get("image") or sprite_map.get(name), base_url)
    return {
        "name": name,
        "number": _display_number(pokemon.get("no")),
        "query": query,
        "form": form_name,
        "kind": type_name,
        "pet_types": [{"name": attr} for attr in attr_names] or [{"name": "未知"}],
        "pet_icon": pet_icon,
        "main_image": main_image,
        "total_stats": total_stats,
        "pet_stats": pet_stats,
        "description": description,
        "pet_traits": traits,
        "pet_evolution": _build_walkthrough_evolution_data(pokemon, detail, base_url),
        "sprite_skills": sprite_skills,
        "skill_total_count": len(skill_names),
        "updated_at": _cn_now().strftime("%Y-%m-%d %H:%M"),
        "wiki_url": pokemon.get("detailUrl") or "",
        "command_hint": f"{query}图鉴",
        "data_source": base_url.rstrip("/"),
    }

async def _fetch_walkthrough_wiki_pet(base_url: str, query: str) -> dict[str, Any]:
    index_data = await _fetch_walkthrough_index(base_url)
    item, ambiguous = _find_matching_pet(index_data["pokemon"], query)
    if ambiguous:
        raise PetWikiQueryError(_ambiguous_message(ambiguous))
    if not item:
        raise PetWikiNotFoundError(f"未找到精灵：{query}")
    data = await _fetch_walkthrough_data(base_url)
    return _build_walkthrough_render_data(
        item,
        data["details"],
        data["skills"],
        data["sprite_map"],
        data["base_url"],
        query,
    )

def _build_pet_wiki_text(data: dict[str, Any]) -> str:
    attr = "、".join(item["name"] for item in data.get("pet_types", [])) or "未知"
    stats = " / ".join(
        f"{item['label']}{item['value']}" for item in data.get("pet_stats", [])
    )
    skills = "、".join(item["name"] for item in data.get("sprite_skills", [])[:8]) or "暂无"
    trait = next(iter(data.get("pet_traits", [])), {})
    return "\n".join(
        [
            f"{data.get('name')} 图鉴",
            f"编号：{data.get('number')}  属性：{attr}",
            f"种族值：{data.get('total_stats')}（{stats}）",
            f"特性：{trait.get('name', '暂无')} - {trait.get('effect', '暂无描述')}",
            f"技能：{skills}",
        ]
    )

async def build_pet_wiki_reply(
    query: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
    wiki_base_url: str = DEFAULT_WIKI_BASE_URL,
) -> tuple[bytes | None, str]:
    query = str(query or "").strip()
    if not query:
        raise PetWikiNotFoundError("未输入精灵名")

    data = await _fetch_wegame_wiki_pet(api_base_url, api_key, query)
    if data is None:
        data = await _fetch_walkthrough_wiki_pet(wiki_base_url, query)
    text = _build_pet_wiki_text(data)
    data = await _inline_pet_wiki_images(data)
    pic = await _render_pet_wiki_image(data)
    return pic, text
