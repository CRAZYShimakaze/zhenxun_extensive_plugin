from io import BytesIO
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
from PIL import Image, ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont

data_dir = Path(__file__).parent / "resources"
skins_dir = data_dir / "skins"
fonts_dir = data_dir / "fonts"


skin_list = [f.stem for f in skins_dir.iterdir() if f.suffix == ".bmp"]


@dataclass
class Skin:
    numbers: List[IMG]
    icons: List[IMG]
    digits: List[IMG]
    faces: List[IMG]
    background: IMG


def load_skin(row: int, column: int, skin_name: str = "winxp") -> Skin:
    image = Image.open(skins_dir / f"{skin_name}.bmp").convert("RGBA")

    def cut(box: Tuple[int, int, int, int]) -> IMG:
        return image.crop(box)

    numbers: List[IMG] = [cut((i * 16, 0, i * 16 + 16, 16)) for i in range(9)]
    icons: List[IMG] = [cut((i * 16, 16, i * 16 + 16, 32)) for i in range(8)]
    digits: List[IMG] = [cut((i * 12, 33, i * 12 + 11, 54)) for i in range(11)]
    faces: List[IMG] = [cut((i * 27, 55, i * 27 + 26, 81)) for i in range(5)]
    background: IMG

    w = column
    h = row
    background = Image.new("RGBA", (w * 16 + 24, h * 16 + 66), "silver")
    b = [
        ((0, 82, 12, 93), (0, 0, 12, 11)),
        ((13, 82, 14, 93), (12, 0, 12 + w * 16, 11)),
        ((15, 82, 27, 93), (12 + w * 16, 0, 24 + w * 16, 11)),
        ((0, 94, 12, 95), (0, 11, 12, 44)),
        ((15, 94, 27, 95), (12 + w * 16, 11, 24 + w * 16, 44)),
        ((0, 96, 12, 107), (0, 44, 12, 55)),
        ((13, 96, 14, 107), (12, 44, 12 + w * 16, 55)),
        ((15, 96, 27, 107), (12 + w * 16, 44, 24 + w * 16, 55)),
        ((0, 108, 12, 109), (0, 55, 12, 55 + h * 16)),
        ((15, 108, 27, 109), (12 + w * 16, 55, 24 + w * 16, 55 + h * 16)),
        ((0, 110, 12, 121), (0, 55 + h * 16, 12, 66 + h * 16)),
        ((13, 110, 14, 121), (12, 55 + h * 16, 12 + w * 16, 66 + h * 16)),
        ((15, 110, 27, 121), (12 + w * 16, 55 + h * 16, 24 + w * 16, 66 + h * 16)),
        ((28, 82, 69, 107), (16, 15, 57, 40)),
        ((28, 82, 69, 107), (w * 16 - 33, 15, 8 + w * 16, 40)),
    ]
    for (s, t) in b:
        background.paste(image.crop(s).resize((t[2] - t[0], t[3] - t[1])), t)

    return Skin(numbers, icons, digits, faces, background)


def save_png(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGBA")
    frame.save(output, format="png")
    return output


def load_font(name: str, fontsize: int) -> FreeTypeFont:
    return ImageFont.truetype(str(fonts_dir / name), fontsize, encoding="utf-8")
