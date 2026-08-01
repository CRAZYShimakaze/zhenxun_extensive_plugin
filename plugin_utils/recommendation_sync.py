import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import uuid


_IGNORED_NAME_CHARACTERS = re.compile(r'[\s·•「」『』“”"\'\-_—&]+')


@dataclass(frozen=True)
class ResourceCategory:
    label: str
    path: Path
    extension: str

    def destination(self, name: str) -> Path:
        return self.path / f"{name}{self.extension}"


def get_file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validated_md5_catalog(data: object, category: str) -> dict[str, str]:
    if not isinstance(data, dict) or not data:
        raise ValueError(f"{category}索引为空")
    result = {
        name: digest.lower()
        for name, digest in data.items()
        if isinstance(name, str)
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-fA-F]{32}", digest)
    }
    if len(result) != len(data):
        raise ValueError(f"{category}索引包含无效数据")
    return result


async def fetch_json(url: str) -> dict:
    from zhenxun.utils.http_utils import AsyncHttpx

    response = await AsyncHttpx.get(url, follow_redirects=True)
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"远程JSON格式无效: {url}")
    return data


async def download_verified(
    raw_base: str,
    source_path: str,
    category_name: str,
    category: ResourceCategory,
    catalog: Mapping[str, str],
    name: str,
    destination: Path | None = None,
    downloader: Callable[..., Awaitable[bool]] | None = None,
) -> bool:
    expected_md5 = catalog.get(name)
    if not expected_md5:
        raise KeyError(f"{category_name}中不存在资源{name}")

    destination = destination or category.destination(name)
    if destination.is_file() and get_file_md5(destination) == expected_md5:
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    task_id = id(asyncio.current_task())
    temporary = destination.with_name(f".{destination.name}.{task_id}.tmp")
    try:
        if downloader is None:
            from zhenxun.utils.http_utils import AsyncHttpx

            downloader = AsyncHttpx.download_file
        downloaded = await downloader(
            f"{raw_base}{source_path}{category_name}/{name}{category.extension}",
            temporary,
            follow_redirects=True,
        )
        if not downloaded:
            raise RuntimeError(f"下载失败: {category_name}/{name}")
        actual_md5 = get_file_md5(temporary)
        if actual_md5 != expected_md5:
            raise ValueError(
                f"{category_name}/{name}校验失败: "
                f"expected={expected_md5}, actual={actual_md5}"
            )
        os.replace(temporary, destination)
        return True
    finally:
        temporary.unlink(missing_ok=True)


def normalize_name(name: str) -> str:
    return _IGNORED_NAME_CHARACTERS.sub("", name).casefold()


def resolve_alias(
    query: str,
    aliases: Mapping[str, Iterable[str]],
    available: Iterable[str],
) -> str | None:
    available_names = set(available)
    normalized_query = normalize_name(query)
    for canonical, alias_values in aliases.items():
        if canonical not in available_names:
            continue
        candidates = (canonical, *alias_values)
        if normalized_query in {normalize_name(item) for item in candidates}:
            return canonical
    return None


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def extract_update_info(readme: str) -> str:
    match = re.search(
        r"\*\*[^*]+\*\*\[v[0-9.]+\]\s*(.*?)(?=\n\*\*|\Z)",
        readme,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""
