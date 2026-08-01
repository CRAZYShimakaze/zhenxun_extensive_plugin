import json
import inspect
import uuid
from pathlib import Path

from zhenxun.configs.path_config import TEMP_PATH
from zhenxun.services.log import logger

from .download_utils import DownloadError, download_file_checked, validate_image

QQ_LOGO_URL = "http://q1.qlogo.cn/g?b=qq&nk={}&s=640"
PLUGINS_PATH = Path(__file__).resolve().parents[1]

def get_message_at(data):
    """
    说明:
        获取消息中所有的 at 对象的 qq
    参数:
        :param data: event.json(), event.message
    """
    qq_list = []
    if isinstance(data, str):
        event = json.loads(data)
        if data and (message := event.get("message")):
            for msg in message:
                if msg and msg.get("type") == "at":
                    qq_list.append(int(msg["data"]["qq"]))
    else:
        for seg in data:
            if seg.type == "at":
                qq_list.append(seg.data["qq"])
    return qq_list


def get_message_img(data: str):
    """
    说明:
        获取消息中所有的 图片 的链接
    参数:
        :param data: event.json()
    """
    img_list = []
    if isinstance(data, str):
        event = json.loads(data)
        if data and (message := event.get("message")):
            for msg in message:
                if msg["type"] == "image":
                    img_list.append(msg["data"]["url"])
    else:
        for seg in data["image"]:
            img_list.append(seg.data["url"])
    return img_list

async def get_mes_img(event) -> list:
    """从事件中提取所有图片 URL（包括回复消息、直接发送的图片、@用户头像）"""
    img_urls = []
    # 从回复消息中提取图片
    if event.reply:
        for seg in event.reply.message:
            if seg.type == "image":
                url = seg.data.get("url") or seg.data.get("file")
                if url:
                    img_urls.append(url)
    # 从当前消息中提取图片（直接遍历 message 段，避免全量 JSON 递归导致重复）
    for seg in event.message:
        if seg.type == "image":
            url = seg.data.get("url") or seg.data.get("file")
            if url:
                img_urls.append(url)
    # 提取 @用户 头像
    for seg in event.message:
        if seg.type == "at":
            qq = seg.data.get("qq")
            if qq and str(qq) != "all":
                img_urls.append(QQ_LOGO_URL.format(qq))
    # 去重但保持顺序
    seen = set()
    unique = []
    for u in img_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

def _infer_plugin_folder(default: str = "ai_helper") -> str:
    """根据调用栈推断调用方所在的插件文件夹名。"""
    frame = inspect.currentframe()
    try:
        frame = frame.f_back if frame else None
        while frame:
            file_path = Path(frame.f_code.co_filename).resolve()
            if file_path != Path(__file__).resolve() and PLUGINS_PATH in file_path.parents:
                relative_parts = file_path.relative_to(PLUGINS_PATH).parts
                if relative_parts:
                    return relative_parts[0]
            frame = frame.f_back
    finally:
        del frame
    return default


async def download_images(url_list: list, plugin_folder: str | None = None) -> list[str]:
    """下载图片列表到临时目录，返回本地路径列表"""
    plugin_folder = plugin_folder or _infer_plugin_folder()
    batch_id = uuid.uuid4().hex[:8]
    paths = []
    for idx, img_url in enumerate(url_list):
        save_path = TEMP_PATH / plugin_folder / f"{batch_id}_{idx}.jpg"
        logger.info(f"下载图片: {img_url} -> {save_path}")
        try:
            await download_file_checked(
                str(img_url),
                save_path,
                validator=validate_image,
                follow_redirects=True,
            )
        except DownloadError as exc:
            logger.warning(f"图片下载失败: {img_url}, error={exc}")
            continue
        paths.append(str(save_path))
    return paths
