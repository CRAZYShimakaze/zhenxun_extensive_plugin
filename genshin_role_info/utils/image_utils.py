from io import BytesIO
from pathlib import Path
from typing import Optional, Union, Tuple

from PIL import Image
from nonebot.adapters.onebot.v11 import MessageSegment

from utils.http_utils import AsyncHttpx


def draw_right_text(draw, text: str, width: int, height: int, fill: str, font):
    """
    绘制右对齐文字
    :param draw: ImageDraw对象
    :param text: 文字
    :param width: 位置横坐标
    :param height: 位置纵坐标
    :param fill: 字体颜色
    :param font: 字体
    """
    text_length = draw.textlength(text, font=font)
    draw.text((width - text_length, height), text, fill=fill,
              font=font)


def draw_center_text(draw, text: str, left_width: int, right_width: int, height: int, fill: str, font):
    """
    绘制居中文字
    :param draw: ImageDraw对象
    :param text: 文字
    :param left_width: 左边位置横坐标
    :param right_width: 右边位置横坐标
    :param height: 位置纵坐标
    :param fill: 字体颜色
    :param font: 字体
    """
    text_length = draw.textlength(text, font=font)
    draw.text((left_width + (right_width - left_width - text_length) / 2, height), text, fill=fill,
              font=font)


async def get_img(url: str,
                  *,
                  save_path: Optional[Union[str, Path]] = None,
                  size: Optional[Union[Tuple[int, int], float]] = None,
                  mode: Optional[str] = None,
                  crop: Optional[Tuple[int, int, int, int]] = None,
                  **kwargs) -> Union[str, Image.Image]:
    if save_path and Path(save_path).exists():
        img = Image.open(save_path)
    else:
        if save_path and not Path(save_path).exists():
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
        await AsyncHttpx.download_file(url, save_path, follow_redirects=True)
        img = Image.open(save_path)
    if size:
        if isinstance(size, float):
            img = img.resize(
                (int(img.size[0] * size), int(img.size[1] * size)),
                Image.ANTIALIAS)
        elif isinstance(size, tuple):
            img = img.resize(size, Image.ANTIALIAS)
    if mode:
        img = img.convert(mode)
    if crop:
        img = img.crop(crop)
    if save_path and not Path(save_path).exists():
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
    return img


def load_image(
        path: Union[Path, str],
        *,
        size: Optional[Union[Tuple[int, int], float]] = None,
        crop: Optional[Tuple[int, int, int, int]] = None,
        mode: Optional[str] = None,
):
    """
    说明：
        读取图像，并预处理
    参数：
        :param path: 图片路径
        :param size: 预处理尺寸
        :param crop: 预处理裁剪大小
        :param mode: 预处理图像模式
        :return: 图像对象
    """
    img = Image.open(path)
    if size:
        if isinstance(size, float):
            img = img.resize(
                (int(img.size[0] * size), int(img.size[1] * size)),
                Image.ANTIALIAS)
        elif isinstance(size, tuple):
            img = img.resize(size, Image.ANTIALIAS)
    if crop:
        img = img.crop(crop)
    if mode:
        img = img.convert(mode)
    return img


def image_build(img: Union[Image.Image, Path, str],
                *,
                size: Optional[Union[Tuple[int, int], float]] = None,
                crop: Optional[Tuple[int, int, int, int]] = None,
                quality: Optional[int] = 100,
                mode: Optional[str] = None) -> MessageSegment:
    """
    说明：
        图片预处理并构造成MessageSegment
        :param img: 图片Image对象或图片路径
        :param size: 预处理尺寸
        :param crop: 预处理裁剪大小
        :param quality: 预处理图片质量
        :param mode: 预处理图像模式
        :return: MessageSegment.image
    """
    if isinstance(img, str) or isinstance(img, Path):
        img = load_image(path=img, size=size, mode=mode, crop=crop)
    else:
        if size:
            if isinstance(size, float):
                img = img.resize(
                    (int(img.size[0] * size), int(img.size[1] * size)),
                    Image.ANTIALIAS)
            elif isinstance(size, tuple):
                img = img.resize(size, Image.ANTIALIAS)
        if crop:
            img = img.crop(crop)
        if mode:
            img = img.convert(mode)
    bio = BytesIO()
    img.save(bio,
             format='JPEG' if img.mode == 'RGB' else 'PNG',
             quality=quality)
    return MessageSegment.image(bio)
