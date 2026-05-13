from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from zhenxun.services.log import logger

from .common import _cn_now
from .constants import DEFAULT_API_BASE_URL, DEFAULT_API_KEY, DEFAULT_TIMEOUT
from .errors import PlayerQueryError
from .rendering import _render_player_image

PLAYER_TASK_POLL_INTERVAL_SECONDS = 1
PLAYER_TASK_POLL_TIMES = 8
PLAYER_SEARCH_WAIT_MS = 5000


def _sanitize_uid(uid: Any) -> str:
    raw = str(uid or "").strip()
    return re.sub(r"[^a-zA-Z0-9_\- \u4e00-\u9fa5]", "", raw).strip()


def _api_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key} if api_key else {}


def _json_payload(response: Any, endpoint: str) -> Any:
    try:
        data = response.json()
    except Exception as e:
        logger.warning(f"[洛克玩家] {endpoint} 响应解析失败: {e}")
        raise PlayerQueryError("接口返回内容无法解析") from e

    if isinstance(data, dict) and data.get("code") not in (None, 0):
        raise PlayerQueryError(str(data.get("message") or "接口返回错误"))
    return data.get("data") if isinstance(data, dict) and "data" in data else data


async def _request_with_status(
    method: str,
    api_base_url: str,
    endpoint: str,
    api_key: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    accepted_statuses: tuple[int, ...] = (200,),
) -> tuple[int | None, Any]:
    """Send an HTTP request and return (status_code, parsed_data).

    Returns ``(None, None)`` on network errors or unexpected HTTP status
    codes so the caller can decide whether to fall back instead of
    crashing out.
    """
    url = f"{api_base_url.rstrip('/')}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            if method == "POST":
                response = await client.post(
                    url,
                    headers=_api_headers(api_key),
                    params=params,
                    json=json,
                )
            else:
                response = await client.get(
                    url,
                    headers=_api_headers(api_key),
                    params=params,
                )
    except Exception as e:
        logger.warning(f"[洛克玩家] {method} {endpoint} 请求失败: {e}")
        return None, None

    if response.status_code not in accepted_statuses:
        body_hint = response.text[:300] if response.text else ""
        try:
            body_json = response.json()
            body_hint = body_json.get("message") or body_hint
        except Exception:
            pass
        logger.warning(
            f"[洛克玩家] {endpoint} HTTP 错误: {response.status_code} {body_hint}"
        )
        return None, None

    try:
        parsed = _json_payload(response, endpoint)
    except PlayerQueryError as e:
        logger.warning(
            f"[洛克玩家] {endpoint} 响应数据异常: {e}"
        )
        return None, None
    return response.status_code, parsed


async def _poll_player_task(
    api_base_url: str,
    api_key: str,
    task_id: str,
) -> dict[str, Any]:
    endpoint = f"/api/v1/games/rocom/ingame/tasks/{task_id}"
    for _ in range(PLAYER_TASK_POLL_TIMES):
        await asyncio.sleep(PLAYER_TASK_POLL_INTERVAL_SECONDS)
        status, payload = await _request_with_status(
            "GET", api_base_url, endpoint, api_key,
            accepted_statuses=(200, 202),
        )
        if status is None:
            raise PlayerQueryError("玩家搜索任务轮询请求失败")
        if status == 200 and isinstance(payload, dict):
            result = _extract_player_result(payload)
            if result is not None:
                return result

        if isinstance(payload, dict):
            task_status = str(payload.get("status") or "").lower()
            if task_status in {"failed", "error"}:
                raise PlayerQueryError(
                    str(payload.get("error_message") or "玩家搜索任务失败")
                )
        # status == 202 or running/pending → continue polling
    raise PlayerQueryError(f"玩家搜索任务仍在队列中，请稍后重试（task_id: {task_id}）")


def _extract_player_result(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("rows"), list):
        return payload
    for key in ("result", "payload", "data"):
        value = payload.get(key)
        if isinstance(value, dict):
            result = _extract_player_result(value)
            if result is not None:
                return result
    return None


async def _fetch_player_search(
    api_base_url: str,
    api_key: str,
    uid: str,
) -> dict[str, Any]:
    uid = _sanitize_uid(uid)
    if not uid:
        raise PlayerQueryError("UID 不能为空")

    endpoint = "/api/v1/games/rocom/ingame/player/search"

    # Step 1: try POST first (matches reference repo behaviour)
    status, payload = await _request_with_status(
        "POST",
        api_base_url,
        endpoint,
        api_key,
        json={"uid": uid, "wait_ms": PLAYER_SEARCH_WAIT_MS},
        accepted_statuses=(200, 202),
    )
    if status == 200 and isinstance(payload, dict):
        result = _extract_player_result(payload)
        if result is not None:
            return result

    # Step 2: POST failed or returned non-200 → fallback to GET
    if status is None:
        status, payload = await _request_with_status(
            "GET",
            api_base_url,
            endpoint,
            api_key,
            params={"uid": uid, "wait_ms": PLAYER_SEARCH_WAIT_MS},
            accepted_statuses=(200, 202),
        )
        if status == 200 and isinstance(payload, dict):
            result = _extract_player_result(payload)
            if result is not None:
                return result

    # Step 3: handle async task (202) – poll for result
    task_id = (payload or {}).get("task_id") if isinstance(payload, dict) else ""
    if not task_id:
        if status == 202:
            raise PlayerQueryError("玩家搜索任务已入队，但未返回 task_id")
        if status is None:
            raise PlayerQueryError("玩家搜索接口请求失败，请稍后重试")
        # status was 200 but no extractable result and no task_id
        if isinstance(payload, dict):
            task_status = str(payload.get("status") or "").lower()
            if task_status in {"failed", "error"}:
                raise PlayerQueryError(
                    str(payload.get("error_message") or "玩家搜索任务失败")
                )
        raise PlayerQueryError("接口未返回玩家资料")

    return await _poll_player_task(api_base_url, api_key, str(task_id))


def _clean_player_field_value(field: str, value: Any) -> str:
    text = str(value or "").strip().strip("'")
    if text in {"<0B>", "<0b>", "<0B >", "<0b >", ""}:
        return "未设置"
    if field in {
        "is_online",
        "online",
        "chat_top_unlock",
        "is_friend",
        "is_black",
        "is_black_role",
        "is_chat_node_unlock",
    }:
        return "是" if text in {"1", "true", "True"} else "否"
    if field in {"sex", "gender"}:
        return {"0": "未知", "1": "男", "2": "女"}.get(text, text)
    if field == "friend_type":
        return {"0": "默认", "1": "特殊"}.get(text, text)
    if field == "battle_state":
        return {"0": "空闲", "1": "对战中"}.get(text, text)
    return text


def _parse_player_payload(payload: dict[str, Any], uid: str) -> dict[str, Any]:
    rows = payload.get("rows") or []
    notes = payload.get("notes") or []
    row_map: dict[str, str] = {}
    label_map: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        field = str(row.get("field") or "")
        if not field:
            continue
        row_map[field] = str(row.get("value") or "")
        label_map[field] = str(row.get("label") or row.get("field") or "")

    nickname = _clean_player_field_value("name", row_map.get("name", "-"))
    player_uid = _clean_player_field_value("uin", row_map.get("uin", uid))
    level = _clean_player_field_value("level", row_map.get("level", "-"))
    signature = _clean_player_field_value("signature", row_map.get("signature", ""))
    if signature == "未设置":
        signature = ""

    cleaned_row_map = {
        key: _clean_player_field_value(key, value) for key, value in row_map.items()
    }
    return {
        "title": payload.get("title") or "玩家搜索",
        "nickname": nickname if nickname and nickname != "-" else player_uid,
        "uid": player_uid,
        "level": level,
        "signature": signature,
        "ret_code": _clean_player_field_value("ret_code", row_map.get("ret_code", "0")),
        "online": _clean_player_field_value(
            "online", row_map.get("online", row_map.get("is_online", ""))
        ),
        "row_map": cleaned_row_map,
        "label_map": label_map,
        "notes": [str(note) for note in notes[:6]],
    }


def _player_field(parsed: dict[str, Any], field: str, default: str = "-") -> str:
    value = str((parsed.get("row_map") or {}).get(field, default) or default).strip()
    return value if value else default


def _pack_section(
    title: str,
    pairs: list[tuple[str, str]],
) -> dict[str, Any] | None:
    items = [
        {"label": label, "value": value}
        for label, value in pairs
        if value and value not in {"-", "未设置"}
    ]
    return {"title": title, "items": items} if items else None


def _build_player_sections(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    sections = [
        _pack_section(
            "核心档案",
            [
                ("等级", str(parsed.get("level") or "-")),
                ("在线状态", _player_field(parsed, "online")),
                ("性别", _player_field(parsed, "gender", _player_field(parsed, "sex"))),
                ("世界等级", _player_field(parsed, "world_level")),
                ("图鉴收集", _player_field(parsed, "card_handbook_collect_num")),
                ("最后离线", _player_field(parsed, "last_logout_time")),
            ],
        ),
        _pack_section(
            "家园信息",
            [
                ("家园名称", _player_field(parsed, "home_name")),
                ("家园等级", _player_field(parsed, "home_level")),
                ("家园经验", _player_field(parsed, "home_experience")),
                ("舒适度", _player_field(parsed, "home_comfort_level")),
                ("访客数量", _player_field(parsed, "visitor_num")),
            ],
        ),
        _pack_section(
            "名片信息",
            [
                ("名片皮肤", _player_field(parsed, "card_skin_selected")),
                ("名片头像", _player_field(parsed, "card_icon_selected")),
                ("首标签", _player_field(parsed, "card_label_first_selected")),
                ("尾标签", _player_field(parsed, "card_label_last_selected")),
            ],
        ),
    ]
    return [section for section in sections if section]


def _build_player_render_data(
    payload: dict[str, Any],
    uid: str,
    api_base_url: str,
) -> dict[str, Any]:
    parsed = _parse_player_payload(payload, uid)
    summary_cards = [
        {"label": "等级", "value": str(parsed.get("level") or "-")},
        {"label": "在线状态", "value": str(parsed.get("online") or "-")},
        {"label": "世界等级", "value": _player_field(parsed, "world_level")},
        {"label": "图鉴收集", "value": _player_field(parsed, "card_handbook_collect_num")},
        {"label": "家园等级", "value": _player_field(parsed, "home_level")},
        {"label": "舒适度", "value": _player_field(parsed, "home_comfort_level")},
    ]
    summary_cards = [
        item
        for item in summary_cards
        if item["value"] and item["value"] not in {"-", "未设置"}
    ]
    # Head tags – small pill badges below the avatar row (matches 洛克档案 style)
    head_tag_pairs = [
        ("性别", _player_field(parsed, "gender", _player_field(parsed, "sex"))),
        ("世界等级", _player_field(parsed, "world_level")),
        ("家园等级", _player_field(parsed, "home_level")),
        ("图鉴收集", _player_field(parsed, "card_handbook_collect_num")),
    ]
    head_tags = [
        {"label": label, "value": value}
        for label, value in head_tag_pairs
        if value and value not in {"-", "未设置"}
    ]
    notes = [{"label": "附加说明", "value": note} for note in parsed.get("notes", [])]
    return {
        "title": "洛克玩家",
        "subtitle": parsed["title"],
        "nickname": parsed["nickname"],
        "uid": parsed["uid"],
        "level": parsed["level"],
        "ret_code": parsed["ret_code"],
        "online": parsed["online"],
        "summary_cards": summary_cards[:6],
        "head_tags": head_tags[:4],
        "signature": parsed.get("signature") or "",
        "show_signature": bool(parsed.get("signature")),
        "sections": _build_player_sections(parsed),
        "notes": notes,
        "updated_at": _cn_now().strftime("%Y-%m-%d %H:%M"),
        "data_source": api_base_url.rstrip("/"),
        "command_hint": "洛克玩家 <UID>",
    }


def _format_player_text(data: dict[str, Any]) -> str:
    lines = [
        f"洛克玩家：{data.get('nickname')}",
        f"UID：{data.get('uid')}  等级：{data.get('level')}  在线：{data.get('online')}",
    ]
    if data.get("signature"):
        lines.append(f"个性签名：{data['signature']}")
    for section in data.get("sections") or []:
        values = "，".join(
            f"{item['label']}：{item['value']}" for item in section.get("items") or []
        )
        if values:
            lines.append(f"{section['title']}：{values}")
    return "\n".join(lines)


async def build_player_reply(
    uid: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
) -> tuple[bytes | None, str]:
    try:
        payload = await _fetch_player_search(api_base_url, api_key, uid)
    except PlayerQueryError:
        # Retry once after a short delay (upstream connection may be transient)
        logger.info("[洛克玩家] 首次请求失败，2 秒后重试")
        await asyncio.sleep(2)
        payload = await _fetch_player_search(api_base_url, api_key, uid)
    data = _build_player_render_data(payload, uid, api_base_url)
    if not data.get("sections") and not data.get("show_signature") and not data.get("summary_cards"):
        raise PlayerQueryError("接口未返回可展示的玩家资料")
    text = _format_player_text(data)
    pic = await _render_player_image(data)
    return pic, text
