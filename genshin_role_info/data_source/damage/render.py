from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PLUGIN_PATH = Path(__file__).resolve().parents[2]
OTHER_PATH = PLUGIN_PATH / "res/other"
FONT_PATH = PLUGIN_PATH / "res/fonts"
IMAGE_WIDTH = 948
BASE_FONT_SIZE = 30
MIN_FONT_SIZE = 20
MIN_LABEL_WIDTH = 250
MAX_LABEL_WIDTH = 360
BUFF_LABEL_WIDTH = 210
BUFF_FONT_SIZE = 28
BUFF_HEADER_HEIGHT = 60
BUFF_LINE_HEIGHT = 46
BUFF_ROW_PADDING = 14


def _load_image(name: str) -> Image.Image:
    return Image.open(OTHER_PATH / name).convert("RGBA")


def _font(size: int, name: str) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH / name, size)


def _center_text(draw, text, left, right, top, fill, font) -> None:
    width = draw.textlength(str(text), font=font)
    draw.text(((left + right - width) / 2, top), str(text), fill=fill, font=font)


def _fit_font(
    draw,
    text,
    name,
    max_width,
    initial=BASE_FONT_SIZE,
    minimum=MIN_FONT_SIZE,
):
    for size in range(initial, minimum - 1, -1):
        font = _font(size, name)
        if draw.textlength(str(text), font=font) <= max_width:
            return font
    return _font(minimum, name)


def _wrap_note(draw, text, font, max_width) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in str(text):
        if draw.textlength(current + char, font=font) <= max_width:
            current += char
            continue
        if current:
            lines.append(current)
        current = char
    if current:
        lines.append(current)
    return lines


def _split_buff(note: str) -> tuple[str, str]:
    text = str(note)
    for separator in ("：", ":"):
        if separator in text:
            source, effect = text.split(separator, 1)
            return source.strip(), effect.strip()
    return text.strip(), ""


def draw_dmg_pic(dmg: dict[str, tuple[str, ...]]) -> Image.Image:
    mask_top = _load_image("遮罩top.png")
    mask_body = _load_image("遮罩body.png")
    mask_bottom = _load_image("遮罩bottom.png")
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    label_font = _font(BASE_FONT_SIZE, "hywh.ttf")
    damage_items = [
        (description, values)
        for description, values in dmg.items()
        if description != "额外说明"
    ]
    descriptions = [description for description, _ in damage_items]
    max_label_width = max(
        (
            measure.textlength(description, font=label_font)
            for description in descriptions
        ),
        default=0,
    )
    label_width = min(
        MAX_LABEL_WIDTH,
        max(MIN_LABEL_WIDTH, int(max_label_width + 28)),
    )
    value_width = (IMAGE_WIDTH - label_width) / 2
    notes = dmg.get("额外说明", ())
    buff_font = _font(BUFF_FONT_SIZE, "hywh.ttf")
    buff_rows = []
    for note in notes:
        source, effect = _split_buff(note)
        effect_lines = _wrap_note(
            measure,
            effect,
            buff_font,
            IMAGE_WIDTH - BUFF_LABEL_WIDTH - 32,
        )
        if not effect_lines:
            effect_lines = [""]
        row_height = max(
            60,
            len(effect_lines) * BUFF_LINE_HEIGHT + BUFF_ROW_PADDING,
        )
        source_font = _fit_font(
            measure,
            source,
            "hywh.ttf",
            BUFF_LABEL_WIDTH - 28,
            initial=BUFF_FONT_SIZE,
            minimum=16,
        )
        buff_rows.append((source, effect_lines, source_font, row_height))

    damage_height = len(damage_items) * 60
    buff_height = (
        BUFF_HEADER_HEIGHT + sum(row[3] for row in buff_rows)
        if buff_rows
        else 0
    )
    content_height = damage_height + buff_height
    height = content_height - 20
    bg = Image.new("RGBA", (IMAGE_WIDTH, height + 80), (0, 0, 0, 0))
    bg.alpha_composite(mask_top, (0, 0))
    bg.alpha_composite(mask_body.resize((IMAGE_WIDTH, height)), (0, 60))
    bg.alpha_composite(mask_bottom, (0, height + 60))
    draw = ImageDraw.Draw(bg)
    value_split = int(label_width + value_width)
    damage_bottom = 60 + damage_height
    draw.line((label_width, 0, label_width, damage_bottom), (255, 255, 255, 75), 2)
    draw.line((value_split, 0, value_split, damage_bottom), (255, 255, 255, 75), 2)
    for row in range(len(damage_items) + 1):
        top = 60 + row * 60
        draw.line((0, top, IMAGE_WIDTH, top), (255, 255, 255, 75), 2)
    _center_text(draw, "伤害计算", 0, label_width, 11, "white", label_font)
    _center_text(draw, "暴击伤害", label_width, value_split, 11, "white", label_font)
    _center_text(draw, "期望伤害", value_split, IMAGE_WIDTH, 11, "white", label_font)

    for row, (description, values) in enumerate(damage_items, start=1):
        top = 60 * row
        label_top = top + 13
        description_font = _fit_font(
            draw,
            description,
            "hywh.ttf",
            label_width - 24,
        )
        _center_text(
            draw,
            description,
            0,
            label_width,
            label_top,
            "white",
            description_font,
        )
        if len(values) == 1:
            _center_text(
                draw,
                values[0],
                label_width,
                IMAGE_WIDTH,
                top + 16,
                "white",
                _font(30, "number.ttf"),
            )
            continue
        _center_text(
            draw,
            values[1],
            label_width,
            value_split,
            top + 16,
            "white",
            _font(30, "number.ttf"),
        )
        _center_text(
            draw,
            values[0],
            value_split,
            IMAGE_WIDTH,
            top + 16,
            "white",
            _font(30, "number.ttf"),
        )

    if buff_rows:
        buff_top = damage_bottom
        buff_title_font = _font(28, "hywh.ttf")
        buff_subtitle_font = _font(22, "hywh.ttf")
        buff_title = "Buff列表"
        draw.text(
            (22, buff_top + 13),
            buff_title,
            fill=(235, 216, 168),
            font=buff_title_font,
        )
        title_width = draw.textlength(buff_title, font=buff_title_font)
        draw.text(
            (34 + title_width, buff_top + 17),
            "部分Buff的触发条件以及层数可能影响实际伤害结果",
            fill=(190, 194, 202),
            font=buff_subtitle_font,
        )
        top = buff_top + BUFF_HEADER_HEIGHT
        draw.line((0, top, IMAGE_WIDTH, top), (255, 255, 255, 75), 2)
        for source, effect_lines, source_font, row_height in buff_rows:
            bottom = top + row_height
            draw.line(
                (BUFF_LABEL_WIDTH, top, BUFF_LABEL_WIDTH, bottom),
                (255, 255, 255, 75),
                2,
            )
            source_width = draw.textlength(source, font=source_font)
            source_top = top + (row_height - source_font.size) / 2 - 3
            draw.text(
                (BUFF_LABEL_WIDTH - 16 - source_width, source_top),
                source,
                fill=(235, 216, 168),
                font=source_font,
            )
            text_height = len(effect_lines) * BUFF_LINE_HEIGHT
            text_top = top + (row_height - text_height) / 2 + 3
            for offset, line in enumerate(effect_lines):
                draw.text(
                    (BUFF_LABEL_WIDTH + 16, text_top + offset * BUFF_LINE_HEIGHT),
                    line,
                    fill="white",
                    font=buff_font,
                )
            draw.line((0, bottom, IMAGE_WIDTH, bottom), (255, 255, 255, 75), 2)
            top = bottom
    return bg
