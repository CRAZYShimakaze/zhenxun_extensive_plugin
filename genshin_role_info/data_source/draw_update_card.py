from typing import Union
from PIL import ImageDraw, Image
from ..utils.card_utils import json_path, get_font, bg_path, avatar_path
from ..utils.image_utils import load_image, draw_center_text, get_img, \
    image_build
from ..utils.json_utils import load_json

role_url = 'https://enka.network/ui/{}.png'

role_data = load_json(f'{json_path}/roles_data.json')
role_name = load_json(f'{json_path}/roles_name.json')


async def draw_update_pic(uid: str, role_dict: Union[dict, list],
                          player_info: dict):
    """
    绘制更新图片
    :param uid: 游戏uid
    :param role_dict: 角色数据
    :param player_info: 角色类
    :return: 更新图片
    """
    multiple = 3
    top_name = 1

    role_list = list(role_dict.keys()) if isinstance(role_dict,
                                                     dict) else role_dict
    nickname = player_info.get_player_info()['昵称']

    bg = Image.new('RGBA',
                   (804 * multiple, 620 * multiple) if len(role_list) > 5 else
                   (804 * multiple, 380 * multiple), (240, 236, 227, 0))
    bg_draw = ImageDraw.Draw(bg)
    draw_center_text(bg_draw, f'{nickname} UID: {uid} 数据和榜单信息更新成功',
                     60 * multiple, (60 + 680) * multiple, 28 * multiple,
                     (127, 91, 57, 0), get_font(28 * multiple, 'hywh.ttf'))

    # 上部横线
    top_line = Image.new('RGBA', (706 * multiple, 5 * multiple),
                         (224, 217, 207, 0))
    bg.paste(top_line, (51 * multiple, 84 * multiple))

    # 绘制角色卡片
    for index, role in enumerate(role_list):
        step = (30 * multiple, 240 * multiple)
        card_size = (157 * multiple, 195 * multiple)
        x = (step[0] + card_size[0]) * (index % 4)
        y = step[1] * (index // 4)

        # 角色卡阴影
        card_bg_shadow = Image.new(
            'RGBA', (card_size[0] + 1 * multiple, card_size[1] + 1 * multiple),
            (80, 78, 91, 0))

        # 角色卡背景
        card_bg = Image.new('RGBA', card_size, (240, 236, 227, 0))
        bg_img = load_image(f"{bg_path}/背景_{role_data[role]['element']}.png",
                            mode='RGBA')
        card_bg.alpha_composite(
            bg_img.resize((card_bg.width, card_bg.height), Image.ANTIALIAS),
            (0, 0))
        card_bg_draw = ImageDraw.Draw(card_bg)

        # 角色图
        role_bg = f"{avatar_path}/{role_name['Side_Name'][role].replace('_Side', '')}.png"
        role_bg = await get_img(url=role_url.format(
            role_name['Side_Name'][role].replace('_Side', '')),
                                save_path=role_bg,
                                mode='RGBA')

        card_bg.alpha_composite(
            role_bg.resize(((card_size[0], card_size[0])), Image.ANTIALIAS),
            (0, 38 * multiple if top_name else 0))

        # 角色卡内部角色名
        draw_center_text(
            card_bg_draw,
            f"{role}Lv.{(player_info.get_roles_info(role))['等级']}",
            36 * multiple, (36 + 85) * multiple,
            (5 if top_name else 164) * multiple, 'white',
            get_font(19 * multiple, '优设标题黑.ttf'))
        card_bg_shadow.paste(card_bg, (-1, -1))
        bg.paste(card_bg_shadow, (45 * multiple + x, 123 * multiple + y))

    draw_center_text(
        bg_draw,
        f"数据时间:{(player_info.get_roles_info(role))['更新时间']}   ※ 数据更新有3分钟延迟",
        226 * multiple, (226 + 350) * multiple, bg.height - 47 * multiple,
        (127, 91, 57, 0), get_font(25 * multiple, 'hywh.ttf'))
    return image_build(img=bg, quality=100, mode='RGB')
