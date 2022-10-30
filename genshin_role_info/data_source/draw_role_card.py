from typing import Dict, Union

from PIL import Image, ImageDraw

from .damage_cal import get_role_dmg
from ..utils.artifact_utils import get_effective, check_effective, \
    get_artifact_suit, get_miao_score, get_artifact_score
from ..utils.card_utils import json_path, other_path, get_font, bg_path, char_pic_path, regoin_path, outline_path, \
    res_path, talent_path, weapon_path, reli_path
from ..utils.image_utils import load_image, draw_center_text, draw_right_text, get_img
from ..utils.json_utils import load_json

weapon_url = 'https://enka.network/ui/{}.png'
artifact_url = 'https://enka.network/ui/{}.png'
talent_url = 'https://enka.network/ui/{}.png'
skill_url = 'https://enka.network/ui/{}.png'
role_url = 'https://enka.network/ui/{}.png'

element_type = ['物理', '火元素', '雷元素', '水元素', '草元素', '风元素', '岩元素', '冰元素']

role_data = load_json(f'{json_path}/role_data.json')
role_name = load_json(f'{json_path}/role_name.json')


def draw_dmg_pic(dmg: Dict[str, Union[tuple, list]]):
    """
    绘制伤害图片
    :param dmg: 伤害字典
    :return: 伤害图片
    """
    # 读取图片资源
    mask_top = load_image(path=f'{other_path}/遮罩top.png')
    mask_body = load_image(path=f'{other_path}/遮罩body.png')
    mask_bottom = load_image(path=f'{other_path}/遮罩bottom.png')
    height = 60 * len(dmg) - 20
    # 创建画布
    bg = Image.new('RGBA', (948, height + 80), (0, 0, 0, 0))
    bg.alpha_composite(mask_top, (0, 0))
    bg.alpha_composite(mask_body.resize((948, height)), (0, 60))
    bg.alpha_composite(mask_bottom, (0, height + 60))
    bg_draw = ImageDraw.Draw(bg)
    # 绘制顶栏
    bg_draw.line((250, 0, 250, 948), (255, 255, 255, 75), 2)
    bg_draw.line((599, 0, 599, 60), (255, 255, 255, 75), 2)
    bg_draw.line((0, 60, 948, 60), (255, 255, 255, 75), 2)
    draw_center_text(bg_draw, '伤害计算', 0, 250, 11, 'white',
                     get_font(30, 'hywh.ttf'))
    draw_center_text(bg_draw, '期望伤害', 250, 599, 11, 'white',
                     get_font(30, 'hywh.ttf'))
    draw_center_text(bg_draw, '暴击伤害', 599, 948, 11, 'white',
                     get_font(30, 'hywh.ttf'))
    i = 1
    for describe, dmg_list in dmg.items():
        bg_draw.line((0, 60 * i, 948, 60 * i), (255, 255, 255, 75), 2)
        draw_center_text(bg_draw, describe, 0, 250, 60 * i + 13, 'white',
                         get_font(30, 'hywh.ttf'))
        if len(dmg_list) == 1:
            if describe == '额外说明':
                draw_center_text(bg_draw, dmg_list[0], 250, 948, 60 * i + 13,
                                 'white', get_font(30, 'hywh.ttf'))
            else:
                draw_center_text(bg_draw, dmg_list[0], 250, 948, 60 * i + 16,
                                 'white', get_font(30, 'number.ttf'))
        else:
            bg_draw.line((599, 60 * i, 599, 60 * (i + 1)), (255, 255, 255, 75),
                         2)
            draw_center_text(bg_draw, dmg_list[0], 250, 599, 60 * i + 16,
                             'white', get_font(30, 'number.ttf'))
            draw_center_text(bg_draw, dmg_list[1], 599, 948, 60 * i + 16,
                             'white', get_font(30, 'number.ttf'))
        i += 1

    return bg


async def draw_role_card(uid, data):
    bg_card = load_image(f'{bg_path}/背景_{data["元素"]}.png',
                         mode='RGBA')
    try:
        dmg_img = get_role_dmg(data)
    except Exception as e:
        print(e)
        dmg_img = None
    if dmg_img:
        dmg_img = draw_dmg_pic(dmg_img)
        bg = Image.new('RGBA', (1080, 1920 + dmg_img.size[1] + 20),
                       (0, 0, 0, 0))
        bg_card_center = bg_card.crop((0, 730, 1080, 1377)).resize(
            (1080, dmg_img.size[1] + 667))
        bg.alpha_composite(bg_card.crop((0, 0, 1080, 730)), (0, 0))
        bg.alpha_composite(bg_card_center, (0, 730))
        bg.alpha_composite(bg_card.crop((0, 1377, 1080, 1920)),
                           (0, dmg_img.size[1] + 1397))
        bg.alpha_composite(dmg_img, (71, 1846))
    else:
        bg = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        bg.alpha_composite(bg_card, (0, 0))
    # 立绘
    role_pic = f'{char_pic_path}/{data["名称"]}.png'
    role_pic = await get_img(
        url=role_url.format(
            role_name["Name"][data["名称"]]),
        save_path=role_pic,
        mode='RGBA')
    new_h = 872
    new_w = int(role_pic.size[0] * (new_h / role_pic.size[1]))
    role_pic = role_pic.resize((new_w, new_h), Image.ANTIALIAS)
    if data['名称'] == '荧':
        bg.alpha_composite(role_pic, (450, 0))  # 234))
    elif data['名称'] == '空':
        bg.alpha_composite(role_pic, (400, 0))  # 234))
    else:
        bg.alpha_composite(role_pic, (-100, 0))  # 234))
    base_mask = load_image(f'{other_path}/底遮罩.png')
    bg.alpha_composite(base_mask, (0, 0))
    if data['名称'] not in ['荧', '空', '埃洛伊']:
        region_icon = load_image(path=f'{regoin_path}/{role_data[data["名称"]]["region"]}.png',
                                 size=(130, 130))
        bg.alpha_composite(region_icon, (0, 4))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.text((131, 100),
                 f"UID{uid}",
                 fill='white',
                 font=get_font(48, 'number.ttf'))
    bg_draw.text((134, 150),
                 data['名称'],
                 fill='white',
                 font=get_font(72, '优设标题黑.ttf'))

    level_mask = load_image(path=f'{other_path}/等级遮罩.png')
    bg.alpha_composite(level_mask, (298 + 60 * (len(data['名称']) - 2), 172))
    draw_center_text(bg_draw, f'LV{data["等级"]}',
                     298 + 60 * (len(data['名称']) - 2),
                     298 + 60 * (len(data['名称']) - 2) + 171, 174, 'black',
                     get_font(48, 'number.ttf'))
    # 属性值
    prop = data['属性']
    bg_draw.text((89, 262), '生命值', fill='white', font=get_font(34, 'hywh.ttf'))
    text_length = bg_draw.textlength(f"+{prop['额外生命']}",
                                     font=get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"{prop['基础生命']}", 480 - text_length - 5, 264,
                    'white', get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"+{prop['额外生命']}", 480, 264, '#59c538',
                    get_font(34, 'number.ttf'))

    bg_draw.text((89, 319), '攻击力', fill='white', font=get_font(34, 'hywh.ttf'))
    text_length = bg_draw.textlength(f"+{prop['额外攻击']}",
                                     font=get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"{prop['基础攻击']}", 480 - text_length - 5, 321,
                    'white', get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"+{prop['额外攻击']}", 480, 321, '#59c538',
                    get_font(34, 'number.ttf'))

    bg_draw.text((89, 377), '防御力', fill='white', font=get_font(34, 'hywh.ttf'))
    text_length = bg_draw.textlength(f"+{prop['额外防御']}",
                                     font=get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"{prop['基础防御']}", 480 - text_length - 5, 379,
                    'white', get_font(34, 'number.ttf'))
    draw_right_text(bg_draw, f"+{prop['额外防御']}", 480, 379, '#59c538',
                    get_font(34, 'number.ttf'))

    text = round(prop['暴击率'] * 100, 1)
    bg_draw.text((89, 436), '暴击率', fill='white', font=get_font(34, 'hywh.ttf'))
    draw_right_text(bg_draw, f"{text}%", 480, 438, 'white',
                    get_font(34, 'number.ttf'))

    text = round(prop['暴击伤害'] * 100, 1)
    bg_draw.text((89, 493),
                 '暴击伤害',
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))
    draw_right_text(bg_draw, f"{text}%", 480, 495, 'white',
                    get_font(34, 'number.ttf'))

    bg_draw.text((89, 551),
                 '元素精通',
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))
    draw_right_text(bg_draw, str(prop['元素精通']), 480, 553, 'white',
                    get_font(34, 'number.ttf'))

    text = round(prop['元素充能效率'] * 100, 1)
    bg_draw.text((89, 610),
                 '元素充能效率',
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))
    draw_right_text(bg_draw, f"{text}%", 480, 612, 'white',
                    get_font(34, 'number.ttf'))

    max_element = max(prop['伤害加成'])
    text = round(max_element * 100, 1)

    bg_draw.text((89, 669),
                 f'{element_type[prop["伤害加成"].index(max_element)]}伤害加成',
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))
    draw_right_text(bg_draw, f"{text}%", 480, 671, 'white',
                    get_font(34, 'number.ttf'))

    # 天赋
    base_icon = load_image(f'{outline_path}/图标_{data["元素"]}.png',
                           mode='RGBA')
    base_icon_grey = load_image(f'{outline_path}/图标_灰.png',
                                mode='RGBA')
    if data['名称'] in ['神里绫华', '莫娜']:
        data['天赋'].pop(2)
    for i in range(3):
        bg.alpha_composite(base_icon.resize((83, 90)),
                           (595 + 147 * i, 253 + 495))
        draw_center_text(bg_draw, str(data['天赋'][i]['等级']), 545 + 147 * i,
                         587 + 147 * i, 310 + 470, 'white',
                         get_font(34, 'number.ttf'))
        skill_icon = f'{res_path}/skill/{data["天赋"][i]["图标"]}.png'
        skill_icon = await get_img(
            url=skill_url.format(
                data["天赋"][i]["图标"]),
            size=(36, 36),
            save_path=skill_icon,
            mode='RGBA')
        bg.alpha_composite(skill_icon, (619 + 147 * i, 776))

    # 命座
    lock = load_image(f'{res_path}/other/锁.png',
                      mode='RGBA',
                      size=(45, 45))
    t = 0
    for talent in data['命座']:
        bg.alpha_composite(base_icon.resize((83, 90)),
                           (510 + t * 84, 790 + 45))
        talent_icon = f'{talent_path}/{talent["图标"]}.png'
        talent_icon = await get_img(
            url=talent_url.format(talent["图标"]),
            size=(45, 45),
            save_path=talent_icon,
            mode='RGBA')
        bg.alpha_composite(talent_icon, (529 + t * 84, 813 + 45))
        t += 1
    for t2 in range(t, 6):
        bg.alpha_composite(base_icon_grey.resize((83, 90)),
                           (510 + t2 * 84, 790 + 45))
        bg.alpha_composite(lock, (530 + t2 * 84, 813 + 45))

    # 武器
    weapon_bg = load_image(f'{other_path}/star{data["武器"]["星级"]}.png',
                           size=(150, 150))
    bg.alpha_composite(weapon_bg, (91, 760))
    weapon_icon = f'{weapon_path}/{data["武器"]["图标"]}.png'
    weapon_icon = await get_img(
        url=weapon_url.format(data["武器"]["图标"]),
        size=(150, 150),
        save_path=weapon_icon,
        mode='RGBA')
    bg.alpha_composite(weapon_icon, (91, 760))
    bg_draw.text((268, 758),
                 data['武器']['名称'],
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))
    star = load_image(f'{other_path}/star.png')
    for i in range(data['武器']['星级']):
        bg.alpha_composite(star, (267 + i * 30, 799))
    draw_center_text(bg_draw, f'LV{data["武器"]["等级"]}', 268, 268 + 98, 835,
                     'black', get_font(27, 'number.ttf'))
    bg_draw.text((266, 869),
                 f'精炼{data["武器"]["精炼等级"]}阶',
                 fill='white',
                 font=get_font(34, 'hywh.ttf'))

    # 圣遗物
    effective, weight_name = get_effective(data)
    affix_weight, point_mark, max_mark = get_miao_score(data, weight_name)
    total_all = 0
    total_cnt = 0
    artifact_list = [{} for _ in range(5)]
    pos_name = ['生之花', '死之羽', '时之沙', '空之杯', '理之冠']
    for i in range(len(data['圣遗物'])):
        artifact_list[pos_name.index(data['圣遗物'][i]['部位'])] = data['圣遗物'][i]
    # 第一排
    for i in range(2):
        artifact = artifact_list[i]
        if not artifact:
            continue
        artifact_score, grade = get_artifact_score(point_mark, max_mark, artifact, data['元素'], i)
        total_all += grade
        total_cnt += 1
        artifact_bg = load_image(f'{other_path}/star{artifact["星级"]}.png',
                                 size=(100, 100))
        bg.alpha_composite(artifact_bg, (587 + 317 * i, 1002))
        reli_icon = f'{reli_path}/{artifact["图标"]}.png'
        reli_icon = await get_img(
            url=artifact_url.format(
                artifact["图标"]),
            size=(100, 100),
            save_path=reli_icon,
            mode='RGBA')
        bg.alpha_composite(reli_icon, (587 + 317 * i, 1002))
        bg_draw.text((411 + 317 * i, 951),
                     artifact['名称'],
                     fill='white',
                     font=get_font(40))
        bg_draw.text((412 + 317 * i, 998),
                     f'{artifact_score}-{round(grade, 1)}',
                     fill='#ffde6b',
                     font=get_font(28, 'number.ttf'))
        bg.alpha_composite(level_mask.resize((98, 30)), (412 + 317 * i, 1032))
        draw_center_text(bg_draw, f"LV{artifact['等级']}", 412 + 317 * i,
                         412 + 317 * i + 98, 1033, 'black',
                         get_font(27, 'number.ttf'))
        bg_draw.text((411 + 317 * i, 1069),
                     artifact['主属性']['属性名'],
                     fill='white',
                     font=get_font(25))
        if artifact['主属性']['属性名'] not in ['生命值', '攻击力', '元素精通']:
            bg_draw.text((408 + 317 * i, 1100),
                         f"+{artifact['主属性']['属性值']}%",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        else:
            bg_draw.text((408 + 317 * i, 1100),
                         f"+{artifact['主属性']['属性值']}",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        for j in range(len(artifact['词条'])):
            if '百分比' in artifact['词条'][j]['属性名']:
                text = artifact['词条'][j]['属性名'].replace('百分比', '')
            else:
                text = artifact['词条'][j]['属性名']
            bg_draw.text(
                (411 + 317 * i, 1163 + 50 * j),
                text,
                fill='white' if check_effective(artifact['词条'][j]['属性名'],
                                                effective) else '#afafaf',
                font=get_font(25))
            if artifact['词条'][j]['属性名'] not in ['攻击力', '防御力', '生命值', '元素精通']:
                num = '+' + str(artifact['词条'][j]['属性值']) + '%'
            else:
                num = '+' + str(artifact['词条'][j]['属性值'])
            draw_right_text(
                bg_draw,
                num,
                679 + 317 * i,
                1163 + 50 * j,
                fill='white' if check_effective(artifact['词条'][j]['属性名'],
                                                effective) else '#afafaf',
                font=get_font(25, 'number.ttf'))
    # 第二排
    for i in range(3):
        artifact = artifact_list[i + 2]
        if not artifact:
            continue
        artifact_score, grade = get_artifact_score(point_mark, max_mark, artifact, data['元素'], i + 2)
        total_all += grade
        total_cnt += 1
        artifact_bg = load_image(f'{other_path}/star{artifact["星级"]}.png',
                                 size=(100, 100))
        bg.alpha_composite(artifact_bg, (270 + 317 * i, 1439))
        reli_icon = f'{reli_path}/{artifact["图标"]}.png'
        reli_icon = await get_img(
            url=artifact_url.format(
                artifact["图标"]),
            size=(100, 100),
            save_path=reli_icon,
            mode='RGBA')
        bg.alpha_composite(reli_icon, (270 + 317 * i, 1439))
        bg_draw.text((94 + 317 * i, 1388),
                     artifact['名称'],
                     fill='white',
                     font=get_font(40))
        bg_draw.text((95 + 317 * i, 1435),
                     f'{artifact_score}-{round(grade, 1)}',
                     fill='#ffde6b',
                     font=get_font(28, 'number.ttf'))
        bg.alpha_composite(level_mask.resize((98, 30)), (95 + 317 * i, 1469))
        draw_center_text(bg_draw, f"LV{artifact['等级']}", 95 + 317 * i,
                         95 + 317 * i + 98, 1470, 'black',
                         get_font(27, 'number.ttf'))
        bg_draw.text((94 + 317 * i, 1506),
                     artifact['主属性']['属性名'],
                     fill='white',
                     font=get_font(25))
        if artifact['主属性']['属性名'] not in ['生命值', '攻击力', '元素精通']:
            bg_draw.text((91 + 317 * i, 1537),
                         f"+{artifact['主属性']['属性值']}%",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        else:
            bg_draw.text((91 + 317 * i, 1537),
                         f"+{artifact['主属性']['属性值']}",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        for j in range(len(artifact['词条'])):
            if '百分比' in artifact['词条'][j]['属性名']:
                text = artifact['词条'][j]['属性名'].replace('百分比', '')
            else:
                text = artifact['词条'][j]['属性名']
            bg_draw.text(
                (94 + 317 * i, 1600 + 50 * j),
                text,
                fill='white' if check_effective(artifact['词条'][j]['属性名'],
                                                effective) else '#afafaf',
                font=get_font(25))
            if artifact['词条'][j]['属性名'] not in ['攻击力', '防御力', '生命值', '元素精通']:
                num = '+' + str(artifact['词条'][j]['属性值']) + '%'
            else:
                num = '+' + str(artifact['词条'][j]['属性值'])
            draw_right_text(
                bg_draw,
                num,
                362 + 317 * i,
                1600 + 50 * j,
                fill='white' if check_effective(artifact['词条'][j]['属性名'],
                                                effective) else '#afafaf',
                font=get_font(25, 'number.ttf'))

    # 圣遗物评分
    if total_cnt and total_all <= 66 * total_cnt:
        score_ave = total_all / total_cnt
        total_rank = 'ACE' if score_ave > 66 else 'ACE' if score_ave > 56.1 else 'ACE' if score_ave > 49.5 \
            else 'SSS' if score_ave > 42.9 else 'SS' if score_ave > 36.3 else 'S' if score_ave > 29.7 else 'A' \
            if score_ave > 23.1 else 'B' if score_ave > 16.5 else 'C' if score_ave > 10 else 'D'
    else:
        total_rank = 'D'
    total_int = int(total_all)
    bg_draw.text((119, 1057), '圣遗物总评分', fill='#afafaf', font=get_font(36))
    rank_icon = load_image(f'{other_path}/评分{total_rank[0]}.png',
                           mode='RGBA')
    if total_rank == 'ACE':
        rank_icon = load_image(f'{other_path}/ACE-A.png',
                               mode='RGBA')
        bg.alpha_composite(rank_icon, (95, 964))
        rank_icon = load_image(f'{other_path}/ACE-C.png',
                               mode='RGBA')
        bg.alpha_composite(rank_icon, (145, 964))
        rank_icon = load_image(f'{other_path}/ACE-E.png',
                               mode='RGBA')
        bg.alpha_composite(rank_icon, (195, 964))
        bg_draw.text((250, 974),
                     str(total_int),
                     fill='white',
                     font=get_font(60, 'number.ttf'))
    elif len(total_rank) == 3:
        bg.alpha_composite(rank_icon, (95, 964))
        bg.alpha_composite(rank_icon, (145, 964))
        bg.alpha_composite(rank_icon, (195, 964))
        bg_draw.text((250, 974),
                     str(total_int),
                     fill='white',
                     font=get_font(60, 'number.ttf'))
    elif len(total_rank) == 2:
        bg.alpha_composite(rank_icon, (125, 964))
        bg.alpha_composite(rank_icon, (175, 964))
        bg_draw.text((235, 974),
                     str(total_int),
                     fill='white',
                     font=get_font(60, 'number.ttf'))
    else:
        bg.alpha_composite(rank_icon, (143, 964))
        bg_draw.text((217, 974),
                     str(total_int),
                     fill='white',
                     font=get_font(60, 'number.ttf'))

    # 圣遗物套装
    suit = get_artifact_suit(data['圣遗物'])
    if not suit:
        bg_draw.text((184, 1168), '未激活套装', fill='white', font=get_font(36))
        bg_draw.text((184, 1292), '未激活套装', fill='white', font=get_font(36))
        total_all = str(total_all) + '*'
    elif len(suit) == 1:
        artifact_path = f'{reli_path}/{suit[0][1]}.png'
        artifact_path = await get_img(
            url=artifact_url.format(
                suit[0][1]),
            size=(110, 110),
            save_path=artifact_path,
            mode='RGBA')
        bg.alpha_composite(artifact_path, (76, 1130))
        bg_draw.text((184, 1168),
                     f'{suit[0][0][:2]}二件套',
                     fill='white',
                     font=get_font(36))
        bg_draw.text((184, 1292), '未激活套装', fill='white', font=get_font(36))
        total_all = str(total_all) + '*'
    else:
        if suit[0][0] == suit[1][0]:
            artifact_path1 = f'{reli_path}/{suit[0][1]}.png'
            artifact_path1 = artifact_path2 = await get_img(
                url=artifact_url.format(suit[0][1]),
                size=(110, 110),
                save_path=artifact_path1,
                mode='RGBA')
            bg_draw.text((184, 1168),
                         f'{suit[0][0][:2]}四件套',
                         fill='white',
                         font=get_font(36))
            bg_draw.text((184, 1292),
                         f'{suit[0][0][:2]}四件套',
                         fill='white',
                         font=get_font(36))
        else:
            artifact_path1 = f'{reli_path}/{suit[0][1]}.png'
            artifact_path1 = await get_img(
                url=artifact_url.format(
                    suit[0][1]),
                size=(110, 110),
                save_path=artifact_path1,
                mode='RGBA')
            artifact_path2 = f'{reli_path}/{suit[1][1]}.png'
            artifact_path2 = await get_img(
                url=artifact_url.format(
                    suit[1][1]),
                size=(110, 110),
                save_path=artifact_path2,
                mode='RGBA')
            bg_draw.text((184, 1168),
                         f'{suit[0][0][:2]}两件套',
                         fill='white',
                         font=get_font(36))
            bg_draw.text((184, 1292),
                         f'{suit[1][0][:2]}两件套',
                         fill='white',
                         font=get_font(36))
        bg.alpha_composite(artifact_path1, (76, 1130))
        bg.alpha_composite(artifact_path2, (76, 1255))
    '''
    effect = []
    for item in effective:
        if item not in ['元素伤害加成', '物理伤害加成', '治疗加成']:
            name = item.replace('百分比', '').replace('元素充能效率', '充能').replace('暴击率', '暴击').replace(
                '暴击伤害', '爆伤').replace('元素精通', '精通')
            effect.append(f'{name}:{effective.get(item)}')
    effect = ','.join(effect)
    '''
    if '-' not in weight_name:
        weight_name += '-通用'
    draw_center_text(bg_draw, f'评分规则:{weight_name},更新于{data["更新时间"].replace("2022-", "")[:-3]}',
                     0, 1080, bg.size[1] - 95, '#afafaf',
                     get_font(33, '优设标题黑.ttf'))
    bg_draw.text((24, bg.size[1] - 50),
                 '  Migrated by CRAZY | Powered by Enka.Network',
                 fill='white',
                 font=get_font(36, '优设标题黑.ttf'))
    return bg, total_all
