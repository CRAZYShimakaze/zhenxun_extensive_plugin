import copy
import math
import re
from typing import Dict, Union

from PIL import Image, ImageDraw

from .damage_cal import get_role_dmg
from ..utils.artifact_utils import get_effective, check_effective, get_artifact_score
from ..utils.card_utils import json_path, other_path, get_font, bg_path, char_pic_path, skill_path, path_path, outline_path, talent_path, weapon_path, reli_path, trans_data
from ..utils.image_utils import load_image, draw_center_text, draw_right_text, get_img
from ..utils.json_utils import load_json

weapon_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/light_cone/{}.png'
artifact_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/relic/{}.png'
rank_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/skill/{}.png'
skill_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/skill/{}.png'
path_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/path/{}.png'
element_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/icon/element/{}.png'
role_url = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/image/character_portrait/{}.png'

role_data = load_json(f'{json_path}/roles_data.json')
role_name = load_json(f'{json_path}/roles_name.json')


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
    if len(dmg.get('额外说明', [''])[0]) >= 26:
        height = 60 * (len(dmg) + 1) - 20
    else:
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
    draw_center_text(bg_draw, '伤害计算', 0, 250, 11, 'white', get_font(30, 'hywh.ttf'))
    draw_center_text(bg_draw, '期望伤害', 250, 599, 11, 'white', get_font(30, 'hywh.ttf'))
    draw_center_text(bg_draw, '暴击伤害', 599, 948, 11, 'white', get_font(30, 'hywh.ttf'))
    i = 1
    for describe, dmg_list in dmg.items():
        bg_draw.line((0, 60 * i, 948, 60 * i), (255, 255, 255, 75), 2)
        if describe == '额外说明' and len(dmg.get('额外说明', [''])[0]) >= 26:
            draw_center_text(bg_draw, describe, 0, 250, 60 * i + 13 + 30, 'white', get_font(30, 'hywh.ttf'))
        else:
            draw_center_text(bg_draw, describe, 0, 250, 60 * i + 13, 'white', get_font(30, 'hywh.ttf'))
        if len(dmg_list) == 1:
            if describe == '额外说明':
                if len(dmg.get('额外说明', [''])[0]) >= 26:
                    first, second = dmg_list[0].split('，')[:2], dmg_list[0].split('，')[2:]
                    draw_center_text(bg_draw, '，'.join(first), 250, 948, 60 * i + 13, 'white', get_font(30, 'hywh.ttf'))
                    draw_center_text(bg_draw, '，'.join(second), 250, 948, 60 * i + 13 + 60, 'white', get_font(30, 'hywh.ttf'))
                else:
                    draw_center_text(bg_draw, dmg_list[0], 250, 948, 60 * i + 13, 'white', get_font(30, 'hywh.ttf'))
            else:
                draw_center_text(bg_draw, dmg_list[0], 250, 948, 60 * i + 16, 'white', get_font(30, 'number.ttf'))
        else:
            bg_draw.line((599, 60 * i, 599, 60 * (i + 1)), (255, 255, 255, 75), 2)
            draw_center_text(bg_draw, dmg_list[0], 250, 599, 60 * i + 16, 'white', get_font(30, 'number.ttf'))
            draw_center_text(bg_draw, dmg_list[1], 599, 948, 60 * i + 16, 'white', get_font(30, 'number.ttf'))
        i += 1

    return bg


async def draw_role_card(uid, data, player_info, plugin_version, only_cal):
    artifact_pk = player_info.data['遗器榜单']
    artifact_all = player_info.data['遗器列表']
    if not only_cal:
        bg_card = load_image(f'{bg_path}/背景_{data["元素"]}.png', size=(1080, 1920), mode='RGBA')
        try:
            dmg_img = get_role_dmg(data)
        except Exception as e:
            print(f'dmg error {e}')
            dmg_img = None
        if dmg_img:
            dmg_img = draw_dmg_pic(dmg_img)
            bg = Image.new('RGBA', (1080, 1920 + dmg_img.size[1] + 20), (0, 0, 0, 0))
            bg_card_center = bg_card.crop((0, 730, 1080, 1377)).resize((1080, dmg_img.size[1] + 667))
            bg.alpha_composite(bg_card.crop((0, 0, 1080, 730)), (0, 0))
            bg.alpha_composite(bg_card_center, (0, 730))
            bg.alpha_composite(bg_card.crop((0, 1377, 1080, 1920)), (0, dmg_img.size[1] + 1397))
            bg.alpha_composite(dmg_img, (71, 1846))
        else:
            bg = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
            bg.alpha_composite(bg_card, (0, 0))
        # 立绘
        role_pic = f'{char_pic_path}/{data["名称"]}.png'
        role_pic = await get_img(url=role_url.format(data['角色ID']), save_path=role_pic, mode='RGBA')
        new_h = 900
        new_w = int(role_pic.size[0] * (new_h / role_pic.size[1]))
        role_pic = role_pic.resize((new_w, new_h), Image.ANTIALIAS)
        bg.alpha_composite(role_pic, (285 + 50, 0))  # 234))
        base_mask = load_image(f'{other_path}/底遮罩.png')
        bg.alpha_composite(base_mask, (0, 0))

        path_icon = f'{path_path}/{trans_data["path"][data["命途"]]}.png'
        path_icon = await get_img(url=path_url.format(trans_data["path"][data["命途"]]), save_path=path_icon, mode='RGBA')
        path_icon = path_icon.resize((130, 130), Image.ANTIALIAS)
        bg.alpha_composite(path_icon, (0, 4))

        element_icon = f'{path_path}/{data["元素"]}.png'
        element_icon = await get_img(url=element_url.format(data["元素"]), save_path=element_icon, mode='RGBA')
        element_icon = element_icon.resize((130, 130), Image.ANTIALIAS)
        bg.alpha_composite(element_icon, (1080 - 130, 4))

        bg_draw = ImageDraw.Draw(bg)
        bg_draw.text((131, 40), f"UID{uid}", fill='white', font=get_font(48, 'number.ttf'))
        bg_draw.text((134, 90), data['名称'], fill='white', font=get_font(72, '优设标题黑.ttf'))

        level_mask = load_image(path=f'{other_path}/等级遮罩.png')
        bg.alpha_composite(level_mask, (298 + 60 * (len(data['名称']) - 2), 112))
        draw_center_text(bg_draw, f'LV{data["等级"]}', 298 + 60 * (len(data['名称']) - 2), 298 + 60 * (len(data['名称']) - 2) + 171, 114, 'black', get_font(48, 'number.ttf'))
        # 属性值
        prop = data['属性']
        bg_draw.text((89, 202), '生命值', fill='white', font=get_font(34, 'hywh.ttf'))
        text_length = bg_draw.textlength(f"+{int(prop['额外生命值'])}", font=get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"{int(prop['基础生命值'])}", 480 - text_length - 5, 204, 'white', get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"+{int(prop['额外生命值'])}", 480, 204, '#59c538', get_font(34, 'number.ttf'))

        bg_draw.text((89, 259), '攻击力', fill='white', font=get_font(34, 'hywh.ttf'))
        text_length = bg_draw.textlength(f"+{int(prop['额外攻击力'])}", font=get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"{int(prop['基础攻击力'])}", 480 - text_length - 5, 261, 'white', get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"+{int(prop['额外攻击力'])}", 480, 261, '#59c538', get_font(34, 'number.ttf'))

        bg_draw.text((89, 317), '防御力', fill='white', font=get_font(34, 'hywh.ttf'))
        text_length = bg_draw.textlength(f"+{int(prop['额外防御力'])}", font=get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"{int(prop['基础防御力'])}", 480 - text_length - 5, 319, 'white', get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"+{int(prop['额外防御力'])}", 480, 319, '#59c538', get_font(34, 'number.ttf'))

        bg_draw.text((89, 377), '速度', fill='white', font=get_font(34, 'hywh.ttf'))
        text_length = bg_draw.textlength(f"+{int(prop['额外速度'])}", font=get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"{int(prop['基础速度'])}", 480 - text_length - 5, 379, 'white', get_font(34, 'number.ttf'))
        draw_right_text(bg_draw, f"+{int(prop['额外速度'])}", 480, 379, '#59c538', get_font(34, 'number.ttf'))

        text = math.floor((prop['基础暴击率'] + prop['暴击率']) * 1000) / 10
        bg_draw.text((89, 436), '暴击率', fill='white', font=get_font(34, 'hywh.ttf'))
        draw_right_text(bg_draw, f"{text}%", 480, 438, 'white', get_font(34, 'number.ttf'))

        text = math.floor((prop['基础暴击伤害'] + prop['暴击伤害']) * 1000) / 10
        bg_draw.text((89, 493), '暴击伤害', fill='white', font=get_font(34, 'hywh.ttf'))
        draw_right_text(bg_draw, f"{text}%", 480, 495, 'white', get_font(34, 'number.ttf'))

        text = math.floor(prop.get('伤害加成', 0) * 1000) / 10
        bg_draw.text((89, 551), '伤害加成', fill='white', font=get_font(34, 'hywh.ttf'))
        draw_right_text(bg_draw, f"{text}%", 480, 553, 'white', get_font(34, 'number.ttf'))

        text = math.floor(prop['击破特攻'] * 1000) / 10
        bg_draw.text((89, 610), '击破特攻', fill='white', font=get_font(34, 'hywh.ttf'))
        draw_right_text(bg_draw, f"{text}%", 480, 612, 'white', get_font(34, 'number.ttf'))

        text = math.floor(prop['效果命中'] * 1000) / 10
        bg_draw.text((89, 669), '效果命中', fill='white', font=get_font(34, 'hywh.ttf'))
        draw_right_text(bg_draw, f"{text}%", 480, 671, 'white', get_font(34, 'number.ttf'))

        # 天赋

        base_icon = load_image(f'{outline_path}/图标_{data["元素"]}.png', mode='RGBA')

        base_icon_grey = load_image(f'{outline_path}/图标_灰.png', mode='RGBA')
        for i in range(4):
            bg.alpha_composite(base_icon.resize((83, 90)), (565 + 117 * i, 253 + 495))
            draw_center_text(bg_draw, str(data['行迹'][i]['等级']), 525 + 117 * i, 567 + 117 * i, 310 + 470, 'white', get_font(34, 'number.ttf'))
            skill_icon = f'{skill_path}/{data["行迹"][i]["图标"]}.png'
            skill_icon = await get_img(url=skill_url.format(data["行迹"][i]["图标"]), size=(36, 36), save_path=skill_icon, mode='RGBA')
            bg.alpha_composite(skill_icon, (589 + 117 * i, 776))

        # 命座
        lock = load_image(f'{other_path}/锁.png', mode='RGBA', size=(45, 45))
        t = 0
        for talent in data['星魂']:
            bg.alpha_composite(base_icon.resize((83, 90)), (510 + t * 84, 790 + 45))
            rank_icon = f'{talent_path}/{talent["图标"]}.png'
            rank_icon = await get_img(url=rank_url.format(talent["图标"]), size=(45, 45), save_path=rank_icon, mode='RGBA')
            bg.alpha_composite(rank_icon, (529 + t * 84, 813 + 45))
            t += 1
        for t2 in range(t, 6):
            bg.alpha_composite(base_icon_grey.resize((83, 90)), (510 + t2 * 84, 790 + 45))
            bg.alpha_composite(lock, (530 + t2 * 84, 813 + 45))

        # 武器
        if data.get('光锥',''):
            weapon_bg = load_image(f'{other_path}/star{data["光锥"]["星级"]}.png', size=(150, 150))
            bg.alpha_composite(weapon_bg, (91, 760))
            weapon_icon = f'{weapon_path}/{data["光锥"]["图标"]}.png'
            weapon_icon = await get_img(url=weapon_url.format(data["光锥"]["图标"]), size=(150, 150), save_path=weapon_icon, mode='RGBA')
            bg.alpha_composite(weapon_icon, (91, 760))
            bg_draw.text((268, 758), data['光锥']['名称'], fill='white', font=get_font(30, 'hywh.ttf'))
            star = load_image(f'{other_path}/star.png')
            for i in range(data['光锥']['星级']):
                bg.alpha_composite(star, (267 + i * 30, 799))
            draw_center_text(bg_draw, f'LV{data["光锥"]["等级"]}', 268, 268 + 98, 835, 'black', get_font(27, 'number.ttf'))
            bg_draw.text((266, 869), f'叠影{data["光锥"]["精炼等级"]}阶', fill='white', font=get_font(30, 'hywh.ttf'))
    else:
        bg = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg)
    # 遗器
    no_list = ''
    effective, weight_name = get_effective(data)

    total_all = 0
    total_cnt = 0
    artifact_pk_info = {'角色': data["名称"]}
    artifact_list = [{} for _ in range(6)]
    pos_name = ['HEAD', 'HAND', 'BODY', 'FOOT', 'NECK', 'OBJECT']
    integer_property = ['生命值', '攻击力', '防御力', '速度']
    for i in range(len(data['遗器'])):
        artifact_list[pos_name.index(data['遗器'][i]['部位'])] = data['遗器'][i]
    # 第一排
    for i in range(6):
        offset_y = 437 * (i // 3)
        offset_x = i % 3
        artifact = artifact_list[i]
        if not artifact:
            continue
        artifact_score, grade, mark = get_artifact_score(effective, artifact, data, i)

        player_info.data['大毕业遗器'] = player_info.data['大毕业遗器'] + 1 if artifact_score == 'ACE' else player_info.data['大毕业遗器']
        player_info.data['小毕业遗器'] = player_info.data['小毕业遗器'] + 1 if artifact_score == 'SSS' else player_info.data['小毕业遗器']

        artifact_pk_info['星级'] = artifact["星级"]
        artifact_pk_info['图标'] = artifact["图标"]
        artifact_pk_info['名称'] = artifact['名称']
        artifact_pk_info['评分'] = grade
        artifact_pk_info['评级'] = artifact_score
        artifact_pk_info['等级'] = artifact['等级']
        artifact_pk_info['主属性'] = {'属性名': artifact['主属性']['属性名'], '属性值': artifact['主属性']['属性值']}
        artifact_pk_info['副属性'] = []

        total_all += round(grade, 1)
        total_cnt += 1
        if not only_cal:
            artifact_bg = load_image(f'{other_path}/star{artifact["星级"]}.png', size=(100, 100))
            bg.alpha_composite(artifact_bg, (270 + 317 * offset_x, 1002 + offset_y))
            reli_icon = f'{reli_path}/{artifact["图标"]}.png'
            reli_icon = await get_img(url=artifact_url.format(artifact["图标"]), size=(100, 100), save_path=reli_icon, mode='RGBA')
            bg.alpha_composite(reli_icon, (270 + 317 * offset_x, 1002 + offset_y))
            bg_draw.text((94 + 317 * offset_x, 951 + offset_y), artifact['名称'], fill='white', font=get_font(30))
            bg_draw.text((95 + 317 * offset_x, 998 + offset_y), f'{artifact_score}-{round(grade, 1)}', fill='#ffde6b', font=get_font(28, 'number.ttf'))
            level_mask = load_image(path=f'{other_path}/等级遮罩.png')
            bg.alpha_composite(level_mask.resize((98, 30)), (95 + 317 * offset_x, 1032 + offset_y))
            if artifact['等级'] != 15 or not artifact_score:
                no_list = '*'
            draw_center_text(bg_draw, f"LV{artifact['等级']}", 95 + 317 * offset_x, 95 + 317 * offset_x + 98, 1033 + offset_y, 'black', get_font(27, 'number.ttf'))
            bg_draw.text((94 + 317 * offset_x, 1069 + offset_y), artifact['主属性']['属性名'], fill='white', font=get_font(25))
            if artifact['主属性']['属性名'] not in integer_property:
                bg_draw.text((91 + 317 * offset_x, 1100 + offset_y), f"+{math.floor(artifact['主属性']['属性值'] * 1000) / 10}%", fill='white', font=get_font(48, 'number.ttf'))
            else:
                bg_draw.text((91 + 317 * offset_x, 1100 + offset_y), f"+{math.floor(artifact['主属性']['属性值'])}", fill='white', font=get_font(48, 'number.ttf'))
        for j in range(len(artifact['词条'])):
            text = artifact['词条'][j]['属性名'].replace('百分比', '')
            up_num = ''
            if mark[j] > 0:
                up_num = '¹' if mark[j] == 1 else '²' if mark[j] == 2 else '³' if mark[j] == 3 else '⁴' if mark[j] == 4 else '⁵'
                x_offset = 25 * len(text)
                bg_draw.text((94 + 317 * offset_x + x_offset, 1163 + offset_y + 50 * j - 5), up_num, fill='white' if check_effective(artifact['词条'][j]['属性名'], effective) else '#afafaf',
                    font=get_font(25, 'tahomabd.ttf'))
            bg_draw.text((94 + 317 * offset_x, 1163 + offset_y + 50 * j), text, fill='white' if check_effective(artifact['词条'][j]['属性名'], effective) else '#afafaf', font=get_font(25))
            if artifact['词条'][j]['属性名'] not in integer_property:
                num = '+' + str(math.floor(artifact['词条'][j]['属性值'] * 1000) / 10) + '%'
            else:
                num = '+' + str(math.floor(artifact['词条'][j]['属性值']))
            artifact_pk_info['副属性'].append({'属性名': text, '属性值': artifact['词条'][j]['属性值'], '强化次数': up_num, '颜色': 'white' if check_effective(artifact['词条'][j]['属性名'], effective) else '#afafaf'})
            draw_right_text(bg_draw, num, 362 + 317 * offset_x, 1163 + offset_y + 50 * j, fill='white' if check_effective(artifact['词条'][j]['属性名'], effective) else '#afafaf', font=get_font(25, 'number.ttf'))
        if artifact_pk_info not in artifact_pk:
            artifact_pk.append(copy.deepcopy(artifact_pk_info))
        if artifact not in artifact_all[i] and artifact['等级'] == 15:
            artifact_all[i].append(copy.deepcopy(artifact))

    player_info.data['遗器榜单'] = sorted(player_info.data['遗器榜单'], key=lambda x: float(x['评分']), reverse=True)[:20]
    data['评分'] = total_all
    if not only_cal:
        # 遗器评分
        if total_cnt and total_all <= 55 * total_cnt:
            # score_ave = total_all / total_cnt
            # score_ave = round(score_ave)
            '''
            total_rank = 'ACE' if score_ave > 66 else 'ACE' if score_ave > 56.1 else 'ACE' if score_ave > 49.5 \
                else 'SSS' if score_ave > 42.9 else 'SS' if score_ave > 36.3 else 'S' if score_ave > 29.7 else 'A' \
                if score_ave > 23.1 else 'B' if score_ave > 16.5 else 'C' if score_ave > 10 else 'D'
            '''
            total_rank = 'ACE' if total_all > 262.0 else 'SSS' if total_all > 227.0 else 'SS' if total_all > 200.8 else 'S' if total_all > 174.6 else 'A' if total_all > 139.7 else 'B' if total_all > 104.8 else 'C' if total_all > 69.9 else 'D'
        else:
            total_rank = 'D'
        total_int = round(total_all)

        bg_draw.text((119 + 480 - 90 + 38, 1057 - 360 - 20 - 33), '总评分', fill='#afafaf', font=get_font(50))
        rank_icon = load_image(f'{other_path}/评分{total_rank[0]}.png', mode='RGBA')
        x_offset = 204 + 440 - 20
        y_offset = -193 - 110 + 3 + 3 - 33
        score_x_offset = 204 + 440
        score_y_offset = -193 - 110 + 3 - 33

        if total_rank == 'ACE':
            rank_icon = load_image(f'{other_path}/ACE-A.png', mode='RGBA', size=(55, 73))
            bg.alpha_composite(rank_icon, (95 + x_offset, 967 + y_offset))
            rank_icon = load_image(f'{other_path}/ACE-C.png', mode='RGBA', size=(55, 73))
            bg.alpha_composite(rank_icon, (145 + x_offset, 967 + y_offset))
            rank_icon = load_image(f'{other_path}/ACE-E.png', mode='RGBA', size=(55, 73))
            bg.alpha_composite(rank_icon, (195 + x_offset, 967 + y_offset))
            bg_draw.text((250 + score_x_offset, 974 + score_y_offset), str(total_int), fill='white', font=get_font(60, 'number.ttf'))
        elif len(total_rank) == 3:
            bg.alpha_composite(rank_icon, (95 + x_offset, 967 + y_offset))
            bg.alpha_composite(rank_icon, (145 + x_offset, 967 + y_offset))
            bg.alpha_composite(rank_icon, (195 + x_offset, 967 + y_offset))
            bg_draw.text((250 + score_x_offset, 974 + score_y_offset), str(total_int), fill='white', font=get_font(60, 'number.ttf'))
        elif len(total_rank) == 2:
            bg.alpha_composite(rank_icon, (125 + x_offset - 11, 967 + y_offset))
            bg.alpha_composite(rank_icon, (175 + x_offset - 11, 967 + y_offset))
            bg_draw.text((235 + score_x_offset, 974 + score_y_offset), str(total_int), fill='white', font=get_font(60, 'number.ttf'))
        else:
            bg.alpha_composite(rank_icon, (143 + x_offset - 18, 967 + y_offset))
            bg_draw.text((217 + score_x_offset, 974 + score_y_offset), str(total_int), fill='white', font=get_font(60, 'number.ttf'))
        '''
        # 遗器套装
        suit = get_artifact_suit(data['遗器'])
        if not suit:
            bg_draw.text((184, 1168), '未激活套装', fill='white', font=get_font(36))
            bg_draw.text((184, 1292), '未激活套装', fill='white', font=get_font(36))
            no_list = '*'
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
            no_list = '*'
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
    effect = {}
    for item in effective:
        if item == '伤害加成':
            effect[f'元素伤害'] = effective.get(item)
        else:
            name = item.replace('百分比', '').replace('效率', '').replace('暴击率', '暴击').replace('暴击伤害', '爆伤').replace('治疗加成', '治疗')
            if name not in effect:
                effect[name] = effective.get(item)
    effect = str(effect).replace("'", "").replace(" ", "").strip("{}")

    if '-' not in weight_name:
        weight_name = '通用'
    else:
        weight_name = weight_name[-2:]
    draw_center_text(bg_draw, f'{weight_name}:{effect}', 0, 1080, bg.size[1] - 85, '#afafaf', get_font(30))
    date = data["更新时间"]# re.sub("\d{4}-", "", data["更新时间"])
    draw_center_text(bg_draw, f'Updated on {date[:-3]} | v{plugin_version}', 0, 1080, bg.size[1] - 50, '#ffffff', get_font(36, '优设标题黑.ttf'))
    return bg, str(total_all) + no_list if no_list == '*' else total_all
