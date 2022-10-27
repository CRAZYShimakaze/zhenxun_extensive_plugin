from io import BytesIO

from PIL import Image, ImageDraw
from PIL.Image import Image as IMG

from .utils import save_jpg, load_font


class Draw_Handle:
    def __init__(self):
        self.question = []
        self.length = 4
        self.block_size = (100, 100)  # 文字块尺寸
        self.block_padding = (20, 20)  # 文字块之间间距
        self.padding = (40, 40)  # 边界间距
        self.border_width = 4  # 边框宽度

        self.border_color = "#374151"  # 边框颜色
        self.bg_color = "#FFFFFF"  # 背景颜色
        self.font_color = "#000000"  # 文字颜色
        self.font_size_char = 60

    async def get_tff(self):
        font_size_char = 90  # 汉字字体大小
        self.font_char = await load_font("Consolas.ttf", font_size_char)

    def draw_block(self,
                   color: str,
                   char: str = "",
                   char_color: str = "") -> IMG:
        block = Image.new("RGB", self.block_size, self.border_color)
        inner_w = self.block_size[0] - self.border_width * 2
        inner_h = self.block_size[1] - self.border_width * 2
        inner = Image.new("RGB", (inner_w, inner_h), color)
        block.paste(inner, (self.border_width, self.border_width))
        draw = ImageDraw.Draw(block)

        if not char:
            return block

        char_size = self.font_char.getsize(char)
        x = (self.block_size[0] - char_size[0]) / 2
        y = (self.block_size[1] - char_size[1]) / 2
        draw.text((x, y), char, font=self.font_char, fill=char_color)
        return block

    def draw(self) -> BytesIO:
        rows = 1
        board_w = self.length * self.block_size[0]
        board_w += (self.length -
                    1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = rows * self.block_size[1]
        board_h += (rows - 1) * self.block_padding[1] + 2 * self.padding[1]
        board_size = (board_w, board_h)
        board = Image.new("RGB", board_size, self.bg_color)
        for i in range(self.length):
            char = self.question[i]
            block = self.draw_block(self.bg_color, char, self.font_color)
            x = self.padding[0] + (self.block_size[0] +
                                   self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(block, (x, y))
        return save_jpg(board)
