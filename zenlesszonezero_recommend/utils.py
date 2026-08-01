import hashlib
import re
from collections.abc import Iterable, Mapping
from pathlib import Path


_IGNORED_NAME_CHARACTERS = re.compile(r'[\s·•「」『』“”"\'\-_—&]+')


def get_file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_name(name: str) -> str:
    return _IGNORED_NAME_CHARACTERS.sub("", name).casefold()


def resolve_name(
    query: str,
    available: Iterable[str],
    aliases: Mapping[str, Iterable[str]] | None = None,
) -> str | None:
    available_names = tuple(available)
    if query in available_names:
        return query

    normalized_available: dict[str, str] = {}
    for name in sorted(available_names):
        normalized_available.setdefault(normalize_name(name), name)

    normalized_query = normalize_name(query)
    if direct_match := normalized_available.get(normalized_query):
        return direct_match

    for canonical, alias_values in (aliases or {}).items():
        candidates = (canonical, *alias_values)
        if normalized_query not in {normalize_name(name) for name in candidates}:
            continue
        for candidate in candidates:
            if match := normalized_available.get(normalize_name(candidate)):
                return match
    return None


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))
