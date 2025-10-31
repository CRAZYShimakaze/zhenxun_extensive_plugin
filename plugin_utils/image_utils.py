import io
from pathlib import Path

from nonebot.adapters.onebot.v11.message import MessageSegment
from PIL import Image


def image(
    file: str | Path | bytes | io.BytesIO | None = None,
    b64: str | None = None,
) -> MessageSegment:
    """
    说明:
        生成一个 MessageSegment.image 消息
        生成顺序：绝对路径(abspath) > base64(b64) > img_name
    参数:
        :param file: 图片文件
        :param b64: 图片base64（兼容旧方法）
    """
    if b64:
        file = b64 if b64.startswith("base64://") else ("base64://" + b64)
    if isinstance(file, str):
        if file.startswith(("http", "base64://")):
            return MessageSegment.image(file)
        else:
            if Path(file).exists():
                check_image = Image.open(file)
                out_img = io.BytesIO()
                check_image.save(out_img, format="PNG")
                return image(out_img)
                # return MessageSegment.image(IMAGE_PATH / file)
            print(f"图片 {(file)}缺失...")
            return MessageSegment.image("")
    if isinstance(file, Path):
        if file.exists():
            check_image = Image.open(file)
            out_img = io.BytesIO()
            check_image.save(out_img, format="PNG")
            return image(out_img)
            # return MessageSegment.image(file)
        print(f"图片 {file.absolute()}缺失...")
    if isinstance(file, (bytes, io.BytesIO)):
        return MessageSegment.image(file)
    return MessageSegment.image("")
