import time
import random
from enum import Enum
from io import BytesIO
from dataclasses import dataclass
from typing import Tuple, Optional, Iterator
from PIL import Image, ImageDraw
from PIL.Image import Image as IMG

from .utils import load_skin, load_font, save_png


class GameState(Enum):
    PREPARE = 0
    GAMING = 1
    WIN = 2
    FAIL = 3


class OpenResult(Enum):
    OUT = 0
    DUP = 1
    WIN = 2
    FAIL = 3


class MarkResult(Enum):
    OUT = 0
    OPENED = 1
    WIN = 2


@dataclass
class Tile:
    is_mine: bool = False
    is_open: bool = False
    marked: bool = False
    boom: bool = False
    count: int = 0


class MineSweeper:
    def __init__(self, row: int, column: int, mine_num: int, skin_name: str = "winxp"):
        self.row = row
        self.column = column
        self.mine_num = mine_num  # 地雷数
        self.start_time = time.time()  # 游戏开始时间
        self.state: GameState = GameState.PREPARE  # 游戏状态
        self.tiles = [[Tile() for _ in range(column)] for _ in range(row)]

        self.skin = load_skin(row, column, skin_name)  # 皮肤
        self.scale: int = 4  # 缩放倍数
        self.font = load_font("00TT.TTF", 50)
        self.padding = 50  # 图片边距，用于添加序号
        self.bg = self.draw_bg()  # 添加好序号的图片

    def set_mines(self):
        # 设置地雷
        count = 0
        while count < self.mine_num:
            i = random.randint(0, self.row - 1)
            j = random.randint(0, self.column - 1)
            tile = self.tiles[i][j]
            if tile.is_mine or tile.is_open:
                continue
            tile.is_mine = True
            count += 1

        # 计算数字
        for i in range(self.row):
            for j in range(self.column):
                self.tiles[i][j].count = self.count_around(i, j)
        self.state = GameState.GAMING

    def draw_bg(self) -> IMG:
        w = self.skin.background.width * self.scale + self.padding
        h = self.skin.background.height * self.scale + self.padding
        img = Image.new("RGBA", (w, h), "silver")
        draw = ImageDraw.Draw(img)
        for i in range(self.row):
            x = 15
            dy = self.skin.numbers[0].height * self.scale
            s = chr(i + 65)
            y = 220 + dy * i + (dy - self.font.getsize(s)[1]) / 2
            draw.text((x, y), s, font=self.font, fill="black")
        for i in range(self.column):
            s = str(i + 1)
            dx = self.skin.numbers[0].width * self.scale
            x = 105 + dx * i + (dx - self.font.getsize(s)[0]) / 2
            y = h - self.padding + 3
            draw.text((x, y), s, font=self.font, fill="black")
        return img

    def draw(self) -> BytesIO:
        bg = self.skin.background
        self.draw_face(bg)
        self.draw_counts(bg)
        self.draw_time(bg)
        self.draw_tiles(bg)
        bg = bg.resize((bg.width * self.scale, bg.height * self.scale), Image.NEAREST)
        img = self.bg
        img.paste(bg, (self.padding, 0))
        return save_png(img)

    def draw_face(self, bg: IMG):
        if self.state == GameState.WIN:
            num = 3
        elif self.state == GameState.FAIL:
            num = 2
        else:
            num = 0
        face = self.skin.faces[num]
        x = int((bg.width - face.width) / 2)
        y = 15
        bg.paste(face, (x, y))

    def all_tiles(self) -> Iterator[Tile]:
        for row in self.tiles:
            for tile in row:
                yield tile

    def draw_counts(self, bg: IMG):
        mark_num = len([tile for tile in self.all_tiles() if tile.marked])
        mine_left = self.mine_num - mark_num
        nums = f"{mine_left:03d}"[:3]
        to_digit = lambda s: self.skin.digits[10 if s == "-" else int(s)]
        digits = [to_digit(s) for s in nums]
        for i in range(3):
            x = 18 + i * (digits[i].width + 2)
            y = 17
            bg.paste(digits[i], (x, y))

    def draw_time(self, bg: IMG):
        time_passed = int(time.time() - self.start_time)
        nums = f"{time_passed:03d}"[-3:]
        digits = [self.skin.digits[int(s)] for s in nums]
        for i in range(3):
            x = bg.width - 16 - (i + 1) * (digits[i].width + 2)
            y = 17
            bg.paste(digits[2 - i], (x, y))

    def draw_tiles(self, bg: IMG):
        for i in range(self.row):
            for j in range(self.column):
                tile = self.tiles[i][j]
                if tile.is_open:
                    if tile.is_mine:
                        num = 5 if tile.boom else 2
                        img = self.skin.icons[num]
                    else:
                        if tile.marked:
                            num = 4
                            img = self.skin.icons[num]
                        else:
                            num = tile.count
                            img = self.skin.numbers[num]
                else:
                    num = 3 if tile.marked else 0
                    img = self.skin.icons[num]

                x = 12 + img.width * j
                y = 55 + img.height * i
                bg.paste(img, (x, y))

    def open(self, x: int, y: int) -> Optional[OpenResult]:
        if not self.is_valid(x, y):
            return OpenResult.OUT

        tile = self.tiles[x][y]
        if tile.is_open:
            return OpenResult.DUP

        tile.is_open = True
        if self.state == GameState.PREPARE:
            self.set_mines()

        if tile.is_mine:
            self.state = GameState.FAIL
            tile.boom = True
            self.show_mines()
            return OpenResult.FAIL

        if tile.count == 0:
            for dx, dy in self.neighbors():
                self.spread_around(x + dx, y + dy)

        open_num = len([tile for tile in self.all_tiles() if tile.is_open])
        if open_num + self.mine_num >= self.row * self.column:
            self.state = GameState.WIN
            self.show_mines()
            return OpenResult.WIN

    def mark(self, x: int, y: int) -> Optional[MarkResult]:
        if not self.is_valid(x, y):
            return MarkResult.OUT
        tile = self.tiles[x][y]
        if tile.is_open:
            return MarkResult.OPENED
        tile.marked = not tile.marked

        mark_tiles = [tile for tile in self.all_tiles() if tile.marked]
        if len(mark_tiles) == self.mine_num and all(
            [tile.is_mine for tile in mark_tiles]
        ):
            self.state = GameState.WIN
            self.show_mines()
            return MarkResult.WIN

    def show_mines(self):
        for t in self.all_tiles():
            if (t.is_mine and not t.marked) or (not t.is_mine and t.marked):
                t.is_open = True

    def is_valid(self, x: int, y: int) -> bool:
        return 0 <= x < self.row and 0 <= y < self.column

    @staticmethod
    def neighbors() -> Tuple[Tuple[int, int], ...]:
        return ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

    def count_around(self, x: int, y: int) -> int:
        count = 0
        for dx, dy in self.neighbors():
            if self.is_valid(x + dx, y + dy) and self.tiles[x + dx][y + dy].is_mine:
                count += 1
        return count

    def spread_around(self, x: int, y: int):
        if not self.is_valid(x, y):
            return
        tile = self.tiles[x][y]
        if tile.is_open:
            return
        if tile.is_mine:
            return
        tile.is_open = True
        tile.marked = False
        if tile.count == 0:
            for dx, dy in self.neighbors():
                self.spread_around(x + dx, y + dy)
