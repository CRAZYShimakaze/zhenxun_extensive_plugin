import numpy as np
from PIL import ImageDraw, Image
from configs.config import Config
from configs.path_config import TEMP_PATH

from .draw_role_card import artifact_url
from ..utils.card_utils import other_path, get_font, bg_path, reli_path, json_path, avatar_path
from ..utils.image_utils import load_image, draw_center_text, draw_right_text, get_img, image_build
from ..utils.json_utils import load_json

avatar_url = 'https://enka.network/ui/{}.png'
qq_logo_url = 'http://q1.qlogo.cn/g?b=qq&nk={}&s=640'
role_name = load_json(f'{json_path}/roles_name.json')
role_data = load_json(f'{json_path}/roles_data.json')


async def draw_qq_logo_mask(artifact, mask_bottom):
    qq_logo_pic = await get_img(
        url=qq_logo_url.format(
            artifact["QQ"]),
        size=(640, 640),
        save_path=TEMP_PATH / str(artifact["QQ"]),
        mode='RGB')
    # 获取遮罩的alpha通道
    mask_array = np.array(mask_bottom)[:, :, 3]
    max_val = np.max(mask_array)
    mask_array[mask_array >= max_val] = Config.get_config("genshin_role_info", "ALPHA")
    mask_alpha = Image.fromarray(mask_array)

    qq_logo_icon = qq_logo_pic
    qq_logo_icon = qq_logo_icon.convert('RGB').resize((mask_bottom.size[1], mask_bottom.size[1]))

    qq_logo_alpha = Image.new('L', qq_logo_icon.size, 0)
    qq_logo_icon = np.array(qq_logo_icon)

    qq_logo_alpha.paste(mask_alpha,
                        ((qq_logo_icon.shape[1] - mask_array.shape[1]) // 2,
                         (qq_logo_icon.shape[0] - mask_array.shape[0]) // 2))
    qq_logo_alpha = np.array(qq_logo_alpha)
    npimage = np.dstack((qq_logo_icon, qq_logo_alpha))
    img = Image.fromarray(npimage)
    img = img.crop(((qq_logo_icon.shape[1] - mask_array.shape[1]) // 2,
                    (qq_logo_icon.shape[0] - mask_array.shape[0]) // 2 + 0,
                    (qq_logo_icon.shape[1] - mask_array.shape[1]) // 2 + mask_bottom.size[0],
                    (qq_logo_icon.shape[0] - mask_array.shape[0]) // 2 + mask_bottom.size[1]))
    return img


async def draw_artifact_card(uid, artifact_info, ace2_num, ace_num, plugin_version, is_group=0):
    bounder_offset = (70, 30)
    interval = (0, 15)
    # w317,h434
    mask_bottom = load_image(path=f'{other_path}/底遮罩.png', crop=(707, 936, 1024, 1370))
    mask_w, mask_h = mask_bottom.size
    h = 5  # len(artifact_pk)//4
    wid = bounder_offset[0] + (mask_w * 4 + interval[0] * 3) + bounder_offset[0]
    hei = bounder_offset[1] + (mask_h * h + interval[1] * (h - 1)) + bounder_offset[1] + 50
    bg = load_image(f'{bg_path}/背景_{role_data[artifact_info[0]["角色"]]["element"]}.png', size=(wid, hei),
                    mode='RGBA')
    bg_draw = ImageDraw.Draw(bg)
    artifact_pk = artifact_info
    # artifact_pk = sorted(artifact_info, key=lambda x: float(x['评分']), reverse=True)

    for index, artifact in enumerate(artifact_pk):
        x_index = index % 4
        y_index = index // 4
        grade = artifact['评分']
        artifact_score = artifact['评级']
        slice_offset_x = bounder_offset[0] + (mask_w + interval[0]) * x_index
        slice_offset_y = bounder_offset[1] + (mask_h + interval[1]) * y_index
        bg.alpha_composite(mask_bottom, (slice_offset_x, slice_offset_y))
        if is_group:
            qq_logo_img = await draw_qq_logo_mask(artifact, mask_bottom)
            bg.alpha_composite(qq_logo_img, (slice_offset_x, slice_offset_y))
        artifact_bg = load_image(f'{other_path}/star{artifact["星级"]}.png',
                                 size=(100, 100))
        bg.alpha_composite(artifact_bg, (slice_offset_x + 200, slice_offset_y + 67))
        reli_icon = f'{reli_path}/{artifact["图标"]}.png'
        reli_icon = await get_img(
            url=artifact_url.format(
                artifact["图标"]),
            size=(100, 100),
            save_path=reli_icon,
            mode='RGBA')
        bg.alpha_composite(reli_icon, (slice_offset_x + 200, slice_offset_y + 67))

        avatar_name = role_name["Side_Name"][artifact["角色"]]
        avatar_icon = f'{avatar_path}/{avatar_name}.png'
        avatar_icon = await get_img(
            url=artifact_url.format(
                avatar_name),
            size=(100, 100),
            save_path=avatar_icon,
            mode='RGBA')
        bg.alpha_composite(avatar_icon, (slice_offset_x + 200 + 30, slice_offset_y + 67 + 30))
        bg_draw.text((slice_offset_x + 24, slice_offset_y + 16),
                     artifact['名称'],
                     fill='white',
                     font=get_font(40))
        bg_draw.text((slice_offset_x + 24, slice_offset_y + 63),
                     f'{artifact_score}-{round(grade, 1)}',
                     fill='#ffde6b',
                     font=get_font(28, 'number.ttf'))
        level_mask = load_image(path=f'{other_path}/等级遮罩.png')
        bg.alpha_composite(level_mask.resize((98, 30)), (slice_offset_x + 24, slice_offset_y + 97))
        draw_center_text(bg_draw, f"LV{artifact['等级']}", slice_offset_x + 24,
                         slice_offset_x + 24 + 98, slice_offset_y + 98, 'black',
                         get_font(27, 'number.ttf'))
        bg_draw.text((slice_offset_x + 23, slice_offset_y + 134),
                     artifact['主属性']['属性名'],
                     fill='white',
                     font=get_font(25))
        if artifact['主属性']['属性名'] not in ['生命值', '攻击力', '元素精通']:
            bg_draw.text((slice_offset_x + 20, slice_offset_y + 165),
                         f"+{artifact['主属性']['属性值']}%",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        else:
            bg_draw.text((slice_offset_x + 20, slice_offset_y + 165),
                         f"+{artifact['主属性']['属性值']}",
                         fill='white',
                         font=get_font(48, 'number.ttf'))
        for j in range(len(artifact['副属性'])):
            text = artifact['副属性'][j]['属性名']
            up_num = artifact['副属性'][j]['强化次数']
            x_offset = 25 * len(text)
            bg_draw.text(
                (slice_offset_x + 23 + x_offset, slice_offset_y + 228 + 50 * j - 5),
                up_num,
                fill=artifact['副属性'][j]['颜色'],
                font=get_font(25, 'tahomabd.ttf'))
            bg_draw.text(
                (slice_offset_x + 23, slice_offset_y + 228 + 50 * j),
                text,
                fill=artifact['副属性'][j]['颜色'],
                font=get_font(25))
            num = artifact['副属性'][j]['属性值']
            draw_right_text(
                bg_draw,
                num,
                slice_offset_x + 291,
                slice_offset_y + 228 + 50 * j,
                fill=artifact['副属性'][j]['颜色'],
                font=get_font(25, 'number.ttf'))

    draw_center_text(bg_draw,
                     f'{"group" if is_group else "uid"}:{uid} | v{plugin_version} | Powered by Enka.Network',
                     0, wid, bg.size[1] - 70, '#ffffff',
                     get_font(46, '优设标题黑.ttf'))
    text_info = '' if is_group else f"\n大毕业圣遗物{ace2_num}个,小毕业圣遗物{ace_num}个.\n最高评分为{artifact_pk[0]['角色']}{round(artifact_pk[0]['评分'], 2)}分的{artifact_pk[0]['名称']}!"

    return image_build(img=bg, quality=100,
                       mode='RGB') + text_info
