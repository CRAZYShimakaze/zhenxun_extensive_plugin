from typing import Union

from PIL import ImageDraw, Image

from .draw_role_card import weapon_url
from ..utils.card_utils import json_path, get_font, bg_path, avatar_path
from ..utils.image_utils import load_image, draw_center_text, get_img, image_build
from ..utils.json_utils import load_json
from ...starrail_role_info.utils.card_utils import other_path, weapon_path

role_url = 'https://enka.network/ui/{}.png'

role_data = load_json(f'{json_path}/roles_data.json')
role_name = load_json(f'{json_path}/roles_name.json')


async def draw_role_pic(uid: str, role_dict: Union[dict, list], player_info):
    """
    绘制更新图片
    :param uid: 游戏uid
    :param role_dict: 角色数据
    :param player_info: 角色类
    :return: 更新图片
    """
    multiple = 2
    top_name = 1
    role_list = list(role_dict.keys()) if isinstance(role_dict, dict) else role_dict
    nickname = player_info.get_player_info()['昵称']
    row_num = 4 + (len(role_list) + 3) // 12

    bg = Image.new('RGBA',
                   ((56 + 187 * row_num) * multiple,
                    (380 + ((len(role_list) + row_num - 1) // row_num - 1) * 240) * multiple),
                   (240, 236, 227, 0))
    bg_draw = ImageDraw.Draw(bg)
    draw_center_text(bg_draw, f'{nickname} UID: {uid} 数据和榜单信息更新成功' if len(
        role_list) < 9 else f'{nickname} UID: {uid} 已缓存角色信息',
                     60 * multiple, (56 + 187 * row_num - 60) * multiple, 28 * multiple,
                     '#7f5b39', get_font(28 * multiple, 'hywh.ttf'))

    # 上部横线
    top_line = Image.new('RGBA', ((56 + 187 * row_num - 100) * multiple, 5 * multiple),
                         (224, 217, 207, 0))
    bg.paste(top_line, (51 * multiple, 84 * multiple))
    role = role_list[-1]
    role_list = sorted(role_list,
                       key=lambda x: (player_info.get_roles_info(x)['等级'], len(player_info.get_roles_info(x)['命座']), player_info.get_roles_info(x)['武器']['精炼等级'],
                                      -['火', '水', '草', '雷', '冰', '风', '岩'].index(
                                          player_info.get_roles_info(x)['元素'])),
                       reverse=True)
    # 绘制角色卡片
    for index, role in enumerate(role_list):
        step = (30 * multiple, 240 * multiple)
        card_size = (157 * multiple, 195 * multiple)
        x = (step[0] + card_size[0]) * (index % row_num)
        y = step[1] * (index // row_num)

        # 角色卡阴影
        card_bg_shadow = Image.new(
            'RGBA', (card_size[0] + 1 * multiple, card_size[1] + 1 * multiple),
            (80, 78, 91, 0))

        data = player_info.get_roles_info(role)
        # 角色卡背景
        card_bg = Image.new('RGBA', card_size, (240, 236, 227, 0))
        bg_img = load_image(f"{bg_path}/背景_{data['元素']}.png",
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
            role_bg.resize((card_size[0], card_size[0]), Image.ANTIALIAS),
            (0, 38 * multiple if top_name else 0))

        # 角色卡内部角色名
        draw_center_text(
            card_bg_draw,
            f"{role}Lv.{data['等级']}",
            36 * multiple, (36 + 85) * multiple,
            (5 if top_name else 164) * multiple, 'white',
            get_font(19 * multiple, '优设标题黑.ttf'))
        # 命座
        card_bg_draw.rounded_rectangle((0, card_size[1] + 1 * multiple - 80, 60, card_size[1] + 1 * multiple), 10,
                                       fill=(101, 101, 101) if len(data['命座']) == 0 else (86, 190, 191) if len(data['命座']) == 1 else (45, 158, 98) if len(
                                           data['命座']) == 2 else (61, 146, 183) if len(data['命座']) == 3 else (55, 85, 183) if len(
                                           data['命座']) == 4 else (119, 71, 177) if len(data['命座']) == 5 else (245, 89, 40))
        draw_center_text(
            card_bg_draw,
            f"{len(data['命座'])}",
            0, 60,
            card_size[1] + 1 * multiple - 80, 'white',
            get_font(30 * multiple, '优设标题黑.ttf'))

        # 武器
        weapon_bg = load_image(f'{other_path}/star{data["武器"]["星级"]}.png',
                               size=(60, 60))
        card_bg.alpha_composite(weapon_bg, (card_size[0] + 1 * multiple - 60, card_size[1] + 1 * multiple - 140))
        weapon_icon = f'{weapon_path}/{data["武器"]["图标"]}.png'
        weapon_icon = await get_img(
            url=weapon_url.format(data["武器"]["图标"]),
            size=(60, 60),
            save_path=weapon_icon,
            mode='RGBA')
        card_bg.alpha_composite(weapon_icon, (card_size[0] + 1 * multiple - 60, card_size[1] + 1 * multiple - 140))

        card_bg_draw.rounded_rectangle((card_size[0] + 1 * multiple - 60, card_size[1] + 1 * multiple - 80, card_size[0] + 1 * multiple, card_size[1] + 1 * multiple), 10,
                                       fill=(86, 190, 191) if data["武器"]["精炼等级"] == 1 else (45, 158, 98) if
                                       data["武器"]["精炼等级"] == 2 else (61, 146, 183) if data['命座'] == 3 else (55, 85, 183) if
                                       data["武器"]["精炼等级"] == 4 else (119, 71, 177))
        draw_center_text(
            card_bg_draw,
            f'{data["武器"]["精炼等级"]}',
            card_size[0] + 1 * multiple - 60, card_size[0] + 1 * multiple,
            card_size[1] + 1 * multiple - 80, 'white',
            get_font(30 * multiple, '优设标题黑.ttf'))

        card_bg_shadow.paste(card_bg, (-1, -1))
        bg.paste(card_bg_shadow, (45 * multiple + x, 123 * multiple + y))

    draw_center_text(
        bg_draw,
        f"数据时间:{(player_info.get_roles_info(role))['更新时间']}   ※ 数据更新有3分钟延迟",
        226 * multiple, (56 + 187 * row_num - 226) * multiple, bg.height - 47 * multiple,
        '#7f5b39', get_font(25 * multiple, 'hywh.ttf'))
    return image_build(img=bg, quality=100, mode='RGB')
