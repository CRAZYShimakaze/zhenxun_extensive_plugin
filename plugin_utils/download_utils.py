from collections.abc import Awaitable, Callable
import os
from pathlib import Path
import uuid


class DownloadError(RuntimeError):
    pass


def validate_nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def validate_image(path: Path) -> bool:
    from PIL import Image

    try:
        with Image.open(path) as image:
            image.verify()
    except (OSError, ValueError):
        return False
    return True


def validate_utf8_text(path: Path) -> bool:
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeDecodeError):
        return False


async def download_file_checked(
    url: str | list[str],
    destination: str | Path,
    *,
    validator: Callable[[Path], bool] = validate_nonempty,
    downloader: Callable[..., Awaitable[bool]] | None = None,
    **kwargs,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.download"
    )
    try:
        if downloader is None:
            from zhenxun.utils.http_utils import AsyncHttpx

            downloader = AsyncHttpx.download_file
        downloaded = await downloader(url, temporary, **kwargs)
        if not downloaded:
            raise DownloadError(f"下载失败: {url}")
        if not validate_nonempty(temporary):
            raise DownloadError(f"下载文件为空: {url}")
        if not validator(temporary):
            raise DownloadError(f"下载文件校验失败: {url}")
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)
