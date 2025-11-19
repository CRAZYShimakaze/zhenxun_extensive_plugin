import json
from pathlib import Path


def load_json(path: Path | str, encoding: str = "utf-8") -> dict:
    """
    说明：
        读取本地json文件，返回json字典。
    参数：
        :param path: 文件路径
        :param encoding: 编码，默认为utf-8
        :return: json字典
    """
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        save_json({}, path, encoding)
    return json.load(path.open("r", encoding=encoding))


def save_json(data: dict | list, path: Path | str = None, encoding: str = "utf-8"):
    """
    保存json文件
    :param data: json数据
    :param path: 保存路径
    :param encoding: 编码
    """
    if isinstance(path, str):
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(data, path.open("w", encoding=encoding), ensure_ascii=False, indent=4)


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
