import random
from enum import Enum
from io import BytesIO
from PIL import Image, ImageDraw
from PIL.Image import Image as IMG
from typing import Iterable, Tuple, List, Optional
from .utils import get_pinyin, load_font, save_jpg


class GuessResult(Enum):
    WIN = 0  # 猜出正确成语
    LOSS = 1  # 达到最大可猜次数，未猜出正确成语
    DUPLICATE = 2  # 成语重复


class Handle:
    def __init__(self, idiom: str):
        self.idiom: str = idiom  # 成语
        self.result = f"答案为：{idiom}"
        self.pinyin: List[Tuple[str, str, str]] = get_pinyin(idiom)  # 拼音
        self.length = 4
        self.times: int = 10  # 可猜次数
        self.guessed_idiom: List[str] = []  # 记录已猜成语
        self.guessed_pinyin: List[List[Tuple[str, str, str]]] = []  # 记录已猜成语的拼音

        self.block_size = (160, 160)  # 文字块尺寸
        self.block_padding = (20, 20)  # 文字块之间间距
        self.padding = (40, 40)  # 边界间距
        self.border_width = 4  # 边框宽度

        self.correct_color = "#1d9c9c"  # 存在且位置正确时的颜色
        self.exist_color = "#de7525"  # 存在但位置不正确时的颜色
        self.wrong_color = "#7F7F7F"  # 不存在时的颜色
        self.border_color = "#374151"  # 边框颜色
        self.bg_color = "#FFFFFF"  # 背景颜色
        self.font_color = "#FFFFFF"  # 文字颜色

    async def get_tff(self):
        font_size_char = 60  # 汉字字体大小
        font_size_pinyin = 36  # 拼音字体大小
        font_size_tone = 24  # 声调字体大小
        self.font_char = await load_font("SourceHanSerifSC-Regular.otf", font_size_char)
        self.font_pinyin = await load_font("Consolas.ttf", font_size_pinyin)
        self.font_tone = await load_font("Consolas.ttf", font_size_tone)

    def guess(self, idiom: str) -> Optional[GuessResult]:
        if idiom in self.guessed_idiom:
            return GuessResult.DUPLICATE
        self.guessed_idiom.append(idiom)
        self.guessed_pinyin.append(get_pinyin(idiom))
        if idiom == self.idiom:
            return GuessResult.WIN
        if len(self.guessed_idiom) == self.times:
            return GuessResult.LOSS

    def draw_block(
            self,
            color: str,
            char: str = "",
            char_color: str = "",
            initial: str = "",
            initial_color: str = "",
            final: str = "",
            final_color: str = "",
            tone: str = "",
            tone_color: str = "",
    ) -> IMG:
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
        y = (self.block_size[1] - char_size[1]) / 5 * 3
        draw.text((x, y), char, font=self.font_char, fill=char_color)

        py_size = self.font_pinyin.getsize(initial + final)
        x = (self.block_size[0] - py_size[0]) / 2
        y = self.block_size[0] / 6
        draw.text((x, y), initial, font=self.font_pinyin, fill=initial_color)
        x += self.font_pinyin.getsize(initial)[0]
        draw.text((x, y), final, font=self.font_pinyin, fill=final_color)

        tone_size = self.font_tone.getsize(tone)
        x = (self.block_size[0] + py_size[0]) / 2 + tone_size[0] / 3
        y -= tone_size[1] / 3
        draw.text((x, y), tone, font=self.font_tone, fill=tone_color)

        return block

    def draw(self) -> BytesIO:
        rows = min(len(self.guessed_idiom) + 1, self.times)
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = rows * self.block_size[1]
        board_h += (rows - 1) * self.block_padding[1] + 2 * self.padding[1]
        board_size = (board_w, board_h)
        board = Image.new("RGB", board_size, self.bg_color)

        def get_color(char1: str, char2: str, char_list: Iterable[str]) -> str:
            if char1 == char2:
                return self.correct_color
            elif char2 in char_list:
                return self.exist_color
            else:
                return self.wrong_color

        for i in range(rows):
            idiom = self.guessed_idiom[i] if len(self.guessed_idiom) > i else ""
            pinyin = self.guessed_pinyin[i] if len(self.guessed_pinyin) > i else []
            for j in range(self.length):
                char = idiom[j] if idiom else ""
                if not char:
                    block = self.draw_block(self.bg_color)
                else:
                    i1, f1, t1 = self.pinyin[j]
                    i2, f2, t2 = pinyin[j]
                    if char == self.idiom[j]:
                        color = self.correct_color
                        char_c = initial_c = final_c = tone_c = self.bg_color
                    else:
                        color = self.bg_color
                        char_c = get_color(self.idiom[j], char, self.idiom)
                        initial_c = get_color(i1, i2, [p[0] for p in self.pinyin])
                        final_c = get_color(f1, f2, [p[1] for p in self.pinyin])
                        tone_c = get_color(t1, t2, [p[2] for p in self.pinyin])
                    block = self.draw_block(
                        color, char, char_c, i2, initial_c, f2, final_c, t2, tone_c
                    )
                x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * j
                y = self.padding[1] + (self.block_size[1] + self.block_padding[1]) * i
                board.paste(block, (x, y))
        return save_jpg(board)

    def draw_hint(self) -> BytesIO:
        guessed_char = set("".join(self.guessed_idiom))
        guessed_initial = set()
        guessed_final = set()
        guessed_tone = set()
        for pinyin in self.guessed_pinyin:
            for p in pinyin:
                guessed_initial.add(p[0])
                guessed_final.add(p[1])
                guessed_tone.add(p[2])

        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.block_size[1] + 2 * self.padding[1]
        board = Image.new("RGB", (board_w, board_h), self.bg_color)

        for i in range(self.length):
            char = self.idiom[i]
            hi, hf, ht = self.pinyin[i]
            color = char_c = initial_c = final_c = tone_c = self.correct_color
            if char not in guessed_char:
                char = "?"
                color = self.bg_color
                char_c = self.wrong_color
            else:
                char_c = initial_c = final_c = tone_c = self.bg_color
            if hi not in guessed_initial:
                hi = "?"
                initial_c = self.wrong_color
            if hf not in guessed_final:
                hf = "?"
                final_c = self.wrong_color
            if ht not in guessed_tone:
                ht = "?"
                tone_c = self.wrong_color
            block = self.draw_block(
                color, char, char_c, hi, initial_c, hf, final_c, ht, tone_c
            )
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(block, (x, y))
        return save_jpg(board)
