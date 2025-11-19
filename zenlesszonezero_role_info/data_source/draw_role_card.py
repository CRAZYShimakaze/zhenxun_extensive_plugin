import copy
import math
import re

from PIL import Image, ImageDraw

from ..utils.artifact_utils import (
    check_effective,
    get_artifact_score,
    get_effective,
    integer_property,
)
from ..utils.card_utils import (
    bg_path,
    char_pic_path,
    get_font,
    other_path,
    outline_path,
    reli_path,
    skill_path,
    type_path,
    weapon_path,
    get_artifact_suit,
)
from ..utils.image_utils import draw_center_text, draw_right_text, get_img, load_image
from .damage_cal import get_role_dmg

resource_url = "https://enka.network/{}"
skill_0 = "https://enka.network/ui/zzz/IconRoleSkillKeyNormal.png"
skill_1 = "https://enka.network/ui/zzz/IconRoleSkillKeyEvade.png"
skill_2 = "https://enka.network/ui/zzz/IconRoleSkillKeySwitch.png"
skill_3 = "https://enka.network/ui/zzz/IconRoleSkillKeySpecialV2.png"
skill_4 = "https://enka.network/ui/zzz/IconRoleSkillKeyUltimateV2.png"
skill_5 = "https://api.hakush.in/zzz/UI/Icon_CoreSkill.webp"
skill_list = [skill_0, skill_1, skill_2, skill_3, skill_4, skill_5]
special_list = {
    "强攻": "https://enka.network/ui/zzz/IconAttack.png",
    "击破": "https://enka.network/ui/zzz/IconStun.png",
    "命破": "https://enka.network/ui/zzz/IconRupture.png",
    "异常": "https://enka.network/ui/zzz/IconAnomaly.png",
    "防护": "https://enka.network/ui/zzz/IconDefense.png",
    "支援": "https://enka.network/ui/zzz/IconSupport.png",
}
pos_name = [1, 2, 3, 4, 5, 6]
role_avatar_url = {
    "卢西娅": "https://patchwiki.biligame.com/images/zzz/a/aa/bewpw892egodvlvmedvwfeda48zlppy.png",
    "奥菲丝&「鬼火」": "https://patchwiki.biligame.com/images/zzz/9/9e/2hxzo9jbadg0hcxbzz2x86e1bko982n.png",
    "「席德」": "https://patchwiki.biligame.com/images/zzz/b/b2/okaku4fnrnzg61icd84jsao92wkd7db.png",
    "爱丽丝": "https://patchwiki.biligame.com/images/zzz/c/ca/d5m3r8feuu4lbskwnntt3mu3f4hdvqb.png",
    "柚叶": "https://patchwiki.biligame.com/images/zzz/b/be/p6n16r8ky85he83f9dp2yzv0pi51xjv.png",
    "橘福福": "https://patchwiki.biligame.com/images/zzz/a/a8/qkkknw4clwwy66i1zvnb9zv5cw1dfug.png",
    "仪玄": "https://patchwiki.biligame.com/images/zzz/f/f9/a1nsugpbqvqamnkj8hy9e6mzm3bdx80.png",
    "雨果": "https://patchwiki.biligame.com/images/zzz/7/73/hifxwv8qhq376yck21r9fzao66e70zr.png",
    "薇薇安": "https://patchwiki.biligame.com/images/zzz/7/79/bvjii4ks3f3azw21ablr42xk1f13n7t.png",
    "「扳机」": "https://patchwiki.biligame.com/images/zzz/2/2d/18ehwn3zvj8d04h7wyw7lu5p7iphm50.png",
    "零号·安比": "https://patchwiki.biligame.com/images/zzz/7/78/ca4mf2zqcu79wh21d86x3ocl3ijtre4.png",
    "伊芙琳": "https://patchwiki.biligame.com/images/zzz/8/83/gyh51mrzure6iav0szztvotfli2vwo9.png",
    "耀嘉音": "https://patchwiki.biligame.com/images/zzz/d/da/322lo9l3y2krzkkwukc3om19aa76l7s.png",
    "悠真": "https://patchwiki.biligame.com/images/zzz/0/00/pn3g45zabacr80qwo0qjdrz5iienb76.png",
    "雅": "https://patchwiki.biligame.com/images/zzz/3/31/6ljd0fuxbygzw1set0zvvaieqgxz9hu.png",
    "莱特": "https://patchwiki.biligame.com/images/zzz/1/1f/khvnv6fg8rauu0np5lal4n2n811lvwe.png",
    "柳": "https://patchwiki.biligame.com/images/zzz/6/6b/3irwi4x4qkmu9ubv9ek58peevgqz11p.png",
    "柏妮思": "https://patchwiki.biligame.com/images/zzz/0/00/0qs4vaonwjatcfuak8e1dc9bxtpwkac.png",
    "凯撒": "https://patchwiki.biligame.com/images/zzz/e/ee/7udos7ucca30nreqerjkrna785fvyo5.png",
    "简": "https://patchwiki.biligame.com/images/zzz/0/0b/68nwr179hb7ueguv7fu27eum3pnrjs5.png",
    "青衣": "https://patchwiki.biligame.com/images/zzz/7/7c/dvt31p5cc1xe9cxcrf1z27ipw9fwpo7.png",
    "朱鸢": "https://patchwiki.biligame.com/images/zzz/b/b9/4be11gi82faanxjl0kiq7txh5h7rvnh.png",
    "「11号」": "https://patchwiki.biligame.com/images/zzz/c/c7/5arwkgiu3yvgxeg1eqwurk20dugxzh1.png",
    "莱卡恩": "https://patchwiki.biligame.com/images/zzz/3/37/koxlptfvzl0vzq3qjyy6bu3guhb87iw.png",
    "丽娜": "https://patchwiki.biligame.com/images/zzz/8/8b/9y0kt391kj33gzaifu4uh8v2ljwguhw.png",
    "艾莲": "https://patchwiki.biligame.com/images/zzz/6/63/3o75q4xil7ifwh0azhk0nfndm5u4db3.png",
    "珂蕾妲": "https://patchwiki.biligame.com/images/zzz/1/18/6heujuc6d956o73zz15rr2lpot7rrjf.png",
    "格莉丝": "https://patchwiki.biligame.com/images/zzz/a/af/1cqpy7o7rujm7hc8rgbn1birtbfytdg.png",
    "猫又": "https://patchwiki.biligame.com/images/zzz/c/c7/szadxd50h9aq1ykccw4kb3hsql8ock7.png",
    "真斗": "https://patchwiki.biligame.com/images/zzz/6/65/nonhxe2x6vq5m02lfsijs0ipxkizp9s.png",
    "潘引壶": "https://patchwiki.biligame.com/images/zzz/2/22/24vbgnv0j02zgyvjlghxqaaz68yphbu.png",
    "波可娜": "https://patchwiki.biligame.com/images/zzz/6/6e/ndj19fh7x8d9z5g3cjnkuk7rgw5pl8c.png",
    "赛斯": "https://patchwiki.biligame.com/images/zzz/a/a5/h30yvx8psx74cu0l64asyml4in4othp.png",
    "可琳": "https://patchwiki.biligame.com/images/zzz/3/33/6uqxh23spl0wtgfk2qidooabodv0u2d.png",
    "安东": "https://patchwiki.biligame.com/images/zzz/d/d6/8zfp36j8pjwrxadhpwtqeqqa1szmrk1.png",
    "本": "https://patchwiki.biligame.com/images/zzz/6/69/ig9c0meb9fpwpvk8ivu9figyf7ei2rn.png",
    "比利": "https://patchwiki.biligame.com/images/zzz/9/96/me3g5rbobr0ibzl5hcy20zy7t95hsrx.png",
    "安比": "https://patchwiki.biligame.com/images/zzz/e/e7/e1g98nfpbfeem9p5jpe73xqinoimd35.png",
    "妮可": "https://patchwiki.biligame.com/images/zzz/a/ae/posa7yw93z9vnzep092rtnrqxksdx4k.png",
    "苍角": "https://patchwiki.biligame.com/images/zzz/1/17/co1tz6xt4fuspz27d1dp4a29mla8i8x.png",
    "派派": "https://patchwiki.biligame.com/images/zzz/9/97/pfu4zzfl1h0cwia744at26rwtzi0997.png",
    "露西": "https://patchwiki.biligame.com/images/zzz/4/4b/nun3urflupvt1lq85o81qxeoie6t9vk.png",
}


def draw_dmg_pic(dmg: dict[str, tuple | list]):
    """
    绘制伤害图片
    :param dmg: 伤害字典
    :return: 伤害图片
    """
    # 读取图片资源
    mask_top = load_image(path=f"{other_path}/遮罩top.png")
    mask_body = load_image(path=f"{other_path}/遮罩body.png")
    mask_bottom = load_image(path=f"{other_path}/遮罩bottom.png")
    if len(dmg.get("额外说明", [""])[0]) >= 26:
        height = 60 * (len(dmg) + 1) - 20
    else:
        height = 60 * len(dmg) - 20
    # 创建画布
    bg = Image.new("RGBA", (948, height + 80), (0, 0, 0, 0))
    bg.alpha_composite(mask_top, (0, 0))
    bg.alpha_composite(mask_body.resize((948, height)), (0, 60))
    bg.alpha_composite(mask_bottom, (0, height + 60))
    bg_draw = ImageDraw.Draw(bg)
    # 绘制顶栏
    bg_draw.line((250, 0, 250, 948), (255, 255, 255, 75), 2)
    bg_draw.line((599, 0, 599, 60), (255, 255, 255, 75), 2)
    bg_draw.line((0, 60, 948, 60), (255, 255, 255, 75), 2)
    draw_center_text(bg_draw, "伤害计算", 0, 250, 11, "white", get_font(30, "hywh.ttf"))
    draw_center_text(
        bg_draw, "期望伤害", 250, 599, 11, "white", get_font(30, "hywh.ttf")
    )
    draw_center_text(
        bg_draw, "暴击伤害", 599, 948, 11, "white", get_font(30, "hywh.ttf")
    )
    i = 1
    for describe, dmg_list in dmg.items():
        bg_draw.line((0, 60 * i, 948, 60 * i), (255, 255, 255, 75), 2)
        if describe == "额外说明" and len(dmg.get("额外说明", [""])[0]) >= 26:
            draw_center_text(
                bg_draw,
                describe,
                0,
                250,
                60 * i + 13 + 30,
                "white",
                get_font(30, "hywh.ttf"),
            )
        else:
            draw_center_text(
                bg_draw,
                describe,
                0,
                250,
                60 * i + 13,
                "white",
                get_font(30, "hywh.ttf"),
            )
        if len(dmg_list) == 1:
            if describe == "额外说明":
                if len(dmg.get("额外说明", [""])[0]) >= 26:
                    first, second = (
                        dmg_list[0].split("，")[:2],
                        dmg_list[0].split("，")[2:],
                    )
                    draw_center_text(
                        bg_draw,
                        "，".join(first),
                        250,
                        948,
                        60 * i + 13,
                        "white",
                        get_font(30, "hywh.ttf"),
                    )
                    draw_center_text(
                        bg_draw,
                        "，".join(second),
                        250,
                        948,
                        60 * i + 13 + 60,
                        "white",
                        get_font(30, "hywh.ttf"),
                    )
                else:
                    draw_center_text(
                        bg_draw,
                        dmg_list[0],
                        250,
                        948,
                        60 * i + 13,
                        "white",
                        get_font(30, "hywh.ttf"),
                    )
            else:
                draw_center_text(
                    bg_draw,
                    dmg_list[0],
                    250,
                    948,
                    60 * i + 16,
                    "white",
                    get_font(30, "number.ttf"),
                )
        else:
            bg_draw.line((599, 60 * i, 599, 60 * (i + 1)), (255, 255, 255, 75), 2)
            draw_center_text(
                bg_draw,
                dmg_list[0],
                250,
                599,
                60 * i + 16,
                "white",
                get_font(30, "number.ttf"),
            )
            draw_center_text(
                bg_draw,
                dmg_list[1],
                599,
                948,
                60 * i + 16,
                "white",
                get_font(30, "number.ttf"),
            )
        i += 1

    return bg


async def draw_role_card(uid, data, player_info, plugin_version, only_cal):
    artifact_pk = player_info.data["驱动盘榜单"]
    artifact_all = player_info.data["驱动盘列表"]
    if not only_cal:
        # bg_card = load_image(f"{bg_path}/背景_{data['元素']}.png", size=(1080, 1920), mode="RGBA")
        bg_card = load_image(f"{bg_path}/bg.png", size=(1080, 1920), mode="RGBA")

        try:
            dmg_img = get_role_dmg(data)
        except Exception as e:
            print(f"dmg error {e}")
            dmg_img = None
        if dmg_img:
            dmg_img = draw_dmg_pic(dmg_img)
            bg = Image.new("RGBA", (1080, 1920 + dmg_img.size[1] + 20), (0, 0, 0, 0))
            bg_card_center = bg_card.crop((0, 730, 1080, 1377)).resize(
                (1080, dmg_img.size[1] + 667)
            )
            bg.alpha_composite(bg_card.crop((0, 0, 1080, 730)), (0, 0))
            bg.alpha_composite(bg_card_center, (0, 730))
            bg.alpha_composite(
                bg_card.crop((0, 1377, 1080, 1920)), (0, dmg_img.size[1] + 1397)
            )
            bg.alpha_composite(dmg_img, (71, 1846))
        else:
            bg = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))  # pyright: ignore[reportArgumentType]
            bg.alpha_composite(bg_card, (0, 0))
        # 立绘
        role_pic = f"{char_pic_path}/{data['名称']}.png"
        role_pic = await get_img(
            url=resource_url.format(data["立绘"]), save_path=role_pic, mode="RGBA"
        )
        new_h = 650
        new_w = int(role_pic.size[0] * (new_h / role_pic.size[1]))
        role_pic = role_pic.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bg.alpha_composite(role_pic, (560, 50))  # 234))
        base_mask = load_image(f"{other_path}/底遮罩.png")
        bg.alpha_composite(base_mask, (0, 0))

        type_icon = load_image(f"{type_path}/{data['特性']}.png")
        # type_icon = await get_img(url=special_list.get(data["特性"]), save_path=type_icon, mode="RGBA")
        type_icon = type_icon.resize((130, 130), Image.Resampling.LANCZOS)
        bg.alpha_composite(type_icon, (0, 4))

        element_icon = load_image(f"{type_path}/{data['元素']}.png")
        # element_icon = await get_img(url=resource_url.format(data["元素"]), save_path=element_icon, mode='RGBA')
        element_icon = element_icon.resize((130, 130), Image.Resampling.LANCZOS)
        bg.alpha_composite(element_icon, (1080 - 130, 4))

        bg_draw = ImageDraw.Draw(bg)
        bg_draw.text(
            (131, 40), f"UID{uid}", fill="white", font=get_font(48, "number.ttf")
        )
        bg_draw.text(
            (134, 90), data["名称"], fill="white", font=get_font(72, "优设标题黑.ttf")
        )

        level_mask = load_image(path=f"{other_path}/等级遮罩.png")
        bg.alpha_composite(level_mask, (298 + 60 * (len(data["名称"]) - 2), 112))
        draw_center_text(
            bg_draw,
            f"LV{data['等级']}",
            298 + 60 * (len(data["名称"]) - 2),
            298 + 60 * (len(data["名称"]) - 2) + 171,
            114,
            "black",
            get_font(48, "number.ttf"),
        )
        # 属性值
        prop = data["属性"]
        bg_draw.text((89, 202), "生命值", fill="white", font=get_font(34, "hywh.ttf"))
        text_length = bg_draw.textlength(
            f"+{int(prop.get('额外生命值', 0))}", font=get_font(34, "number.ttf")
        )
        draw_right_text(
            bg_draw,
            f"{int(prop['基础生命值'])}",
            480 - text_length - 5,
            204,
            "white",
            get_font(34, "number.ttf"),
        )
        draw_right_text(
            bg_draw,
            f"+{int(prop.get('额外生命值', 0))}",
            480,
            204,
            "#59c538",
            get_font(34, "number.ttf"),
        )

        bg_draw.text((89, 259), "攻击力", fill="white", font=get_font(34, "hywh.ttf"))
        text_length = bg_draw.textlength(
            f"+{int(prop.get('额外攻击力', 0))}", font=get_font(34, "number.ttf")
        )
        draw_right_text(
            bg_draw,
            f"{int(prop['基础攻击力'])}",
            480 - text_length - 5,
            261,
            "white",
            get_font(34, "number.ttf"),
        )
        draw_right_text(
            bg_draw,
            f"+{int(prop.get('额外攻击力', 0))}",
            480,
            261,
            "#59c538",
            get_font(34, "number.ttf"),
        )

        bg_draw.text((89, 317), "防御力", fill="white", font=get_font(34, "hywh.ttf"))
        text_length = bg_draw.textlength(
            f"+{int(prop.get('额外防御力', 0))}", font=get_font(34, "number.ttf")
        )
        draw_right_text(
            bg_draw,
            f"{int(prop['基础防御力'])}",
            480 - text_length - 5,
            319,
            "white",
            get_font(34, "number.ttf"),
        )
        draw_right_text(
            bg_draw,
            f"+{int(prop.get('额外防御力', 0))}",
            480,
            319,
            "#59c538",
            get_font(34, "number.ttf"),
        )

        # bg_draw.text((89, 377), "冲击力", fill="white", font=get_font(34, "hywh.ttf"))
        # text_length = bg_draw.textlength(f"+{int(prop.get('额外冲击力', 0))}", font=get_font(34, "number.ttf"))
        # draw_right_text(bg_draw, f"{int(prop['基础冲击力'])}", 480 - text_length - 5, 379, "white", get_font(34, "number.ttf"))
        # draw_right_text(bg_draw, f"+{int(prop.get('额外冲击力', 0))}", 480, 379, "#59c538", get_font(34, "number.ttf"))
        prop_list = [
            "暴击率",
            "暴击伤害",
            "异常掌控",
            "异常精通",
            "贯穿力",
            "穿透率",
            "穿透值",
            "冲击力",
            "伤害加成",
            "能量自动回复",
        ]
        effective, weight_name = get_effective(data)
        sorted_items = sorted(effective.items(), key=lambda x: x[1], reverse=True)

        # prop_list=dict(sorted_items).keys()
        y = 377  # 436

        b = 379  # 438
        for item in prop_list:
            if prop.get(f"额外{item}", 0) == 0:
                continue
            if "能量" in item:
                text = math.floor(
                    prop.get(f"基础{item}", 0)
                    * (10000 + prop.get(f"额外{item}", 0))
                    / 10000
                )
            else:
                text = math.floor(
                    prop.get(f"基础{item}", 0) + prop.get(f"额外{item}", 0)
                )
            if item not in integer_property:
                text = text / 100
            if int(text) == 0:
                continue
            bg_draw.text((89, y), item, fill="white", font=get_font(34, "hywh.ttf"))
            if item not in integer_property and "能量" not in item:
                draw_right_text(
                    bg_draw, f"{text}%", 480, b, "white", get_font(34, "number.ttf")
                )
            else:
                draw_right_text(
                    bg_draw, f"{text}", 480, b, "white", get_font(34, "number.ttf")
                )
            y += 58
            b += 58
            if y >= 669:
                break
        # text = math.floor(prop["基础暴击率"] + prop.get("额外暴击率", 0)) / 100
        # bg_draw.text((89, 436), "暴击率", fill="white", font=get_font(34, "hywh.ttf"))
        # draw_right_text(bg_draw, f"{text}%", 480, 438, "white", get_font(34, "number.ttf"))

        # text = math.floor(prop["基础暴击伤害"] + prop.get("额外暴击率", 0)) / 100
        # bg_draw.text((89, 493), "暴击伤害", fill="white", font=get_font(34, "hywh.ttf"))
        # draw_right_text(bg_draw, f"{text}%", 480, 495, "white", get_font(34, "number.ttf"))

        # text = math.floor(prop["基础穿透率"] + prop.get("额外穿透率", 0)) / 100
        # bg_draw.text((89, 551), "穿透率", fill="white", font=get_font(34, "hywh.ttf"))
        # draw_right_text(bg_draw, f"{text}%", 480, 553, "white", get_font(34, "number.ttf"))

        # text = math.floor(prop["基础异常掌控"] + prop.get("额外异常掌控", 0))
        # bg_draw.text((89, 610), "异常掌控", fill="white", font=get_font(34, "hywh.ttf"))
        # draw_right_text(bg_draw, f"{text}%", 480, 612, "white", get_font(34, "number.ttf"))

        # text = math.floor(prop["基础异常精通"] + prop.get("额外异常精通", 0))
        # bg_draw.text((89, 669), "异常精通", fill="white", font=get_font(34, "hywh.ttf"))
        # draw_right_text(bg_draw, f"{text}%", 480, 671, "white", get_font(34, "number.ttf"))

        # 天赋

        base_icon = load_image(f"{outline_path}/图标_{data['元素']}.png", mode="RGBA")

        # base_icon_grey = load_image(f'{outline_path}/图标_灰.png', mode='RGBA')
        x_len = 150
        x_offset = 30
        for i in range(3):
            bg.alpha_composite(
                base_icon.resize((83, 90)), (x_offset + 565 + x_len * i, 253 + 495)
            )
            draw_center_text(
                bg_draw,
                str(data["技能"][i]),
                x_offset + 525 + x_len * i,
                x_offset + 567 + x_len * i,
                310 + 470,
                "white",
                get_font(34, "number.ttf"),
            )
            skill_icon = f"{skill_path}/{i}.png"
            skill_icon = await get_img(
                url=skill_list[i], size=(36, 36), save_path=skill_icon, mode="RGBA"
            )
            bg.alpha_composite(skill_icon, (x_offset + 589 + x_len * i, 776))
        x_offset = -420
        y_offset = 80
        for i in range(3, 6):
            bg.alpha_composite(
                base_icon.resize((83, 90)),
                (x_offset + 565 + x_len * i, 253 + 495 + y_offset),
            )
            draw_center_text(
                bg_draw,
                str(data["技能"][i]),
                x_offset + 525 + x_len * i,
                x_offset + 567 + x_len * i,
                310 + 470 + y_offset,
                "white",
                get_font(34, "number.ttf"),
            )
            skill_icon = f"{skill_path}/{i}.png"
            skill_icon = await get_img(
                url=skill_list[i], size=(36, 36), save_path=skill_icon, mode="RGBA"
            )
            bg.alpha_composite(skill_icon, (x_offset + 589 + x_len * i, 776 + y_offset))

        # 命座
        # lock = load_image(f'{other_path}/锁.png', mode='RGBA', size=(45, 45))
        # t = 0
        # for talent in data['星魂']:
        #     bg.alpha_composite(base_icon.resize((83, 90)), (510 + t * 84, 790 + 45))
        #     rank_icon = f'{talent_path}/{talent["图标"]}.png'
        #     rank_icon = await get_img(url=rank_url.format(talent["图标"]), size=(45, 45), save_path=rank_icon, mode='RGBA')
        #     bg.alpha_composite(rank_icon, (529 + t * 84, 813 + 45))
        #     t += 1
        # for t2 in range(t, 6):
        #     bg.alpha_composite(base_icon_grey.resize((83, 90)), (510 + t2 * 84, 790 + 45))
        #     bg.alpha_composite(lock, (530 + t2 * 84, 813 + 45))

        # 武器
        if data["武器"]:
            weapon_bg = load_image(
                f"{other_path}/star{data['武器']['星级'] + 1}.png", size=(150, 150)
            )
            bg.alpha_composite(weapon_bg, (91, 760))
            weapon_icon = f"{weapon_path}/{data['武器']['名称']}.png"
            weapon_icon = await get_img(
                url=resource_url.format("ui/zzz/" + data["武器"]["图标"] + ".png"),
                size=(150, 150),
                save_path=weapon_icon,
                mode="RGBA",
            )
            bg.alpha_composite(weapon_icon, (91, 760))
            bg_draw.text(
                (268, 758),
                data["武器"]["名称"],
                fill="white",
                font=get_font(30, "hywh.ttf"),
            )
            star = load_image(f"{other_path}/star.png")
            for i in range(data["武器"]["星级"] + 1):
                bg.alpha_composite(star, (267 + i * 30, 799))
            draw_center_text(
                bg_draw,
                f"LV{data['武器']['等级']}",
                268,
                268 + 98,
                835,
                "black",
                get_font(27, "number.ttf"),
            )
            bg_draw.text(
                (266, 869),
                f"精炼{data['武器']['精炼等级']}星",
                fill="white",
                font=get_font(30, "hywh.ttf"),
            )
    else:
        bg = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg)
    # 驱动盘
    no_list = ""
    effective, weight_name = get_effective(data)
    # effective = {"生命值"}
    # weight_name = "默认"
    total_all = 0
    total_cnt = 0
    artifact_pk_info = {"角色": data["名称"]}
    artifact_list = [{} for _ in range(6)]

    for i in range(len(data["驱动盘"])):
        if data["驱动盘"][i]:
            artifact_list[pos_name.index(data["驱动盘"][i]["部位"])] = data["驱动盘"][i]
    # 第一排
    for i in range(6):
        offset_y = 437 * (i // 3)
        offset_x = i % 3
        artifact = artifact_list[i]
        if not artifact:
            continue
        artifact_score, grade = get_artifact_score(effective, artifact, data, i)
        # artifact_score = grade = mark = 0
        player_info.data["大毕业驱动盘"] = (
            player_info.data["大毕业驱动盘"] + 1
            if artifact_score == "ACE"
            else player_info.data["大毕业驱动盘"]
        )
        player_info.data["小毕业驱动盘"] = (
            player_info.data["小毕业驱动盘"] + 1
            if artifact_score == "SSS"
            else player_info.data["小毕业驱动盘"]
        )

        artifact_pk_info["星级"] = artifact["星级"]
        artifact_pk_info["图标"] = artifact["图标"]
        artifact_pk_info["名称"] = artifact["名称"]
        artifact_pk_info["评分"] = grade
        artifact_pk_info["评级"] = artifact_score
        artifact_pk_info["等级"] = artifact["等级"]
        artifact_pk_info["主属性"] = {
            "属性名": artifact["主属性"]["属性名"],
            "属性值": artifact["主属性"]["属性值"],
        }
        artifact_pk_info["副属性"] = []
        print(f"grade{grade}")

        total_all += round(grade, 1)
        total_cnt += 1
        if not only_cal:
            # artifact_bg = load_image(f'{other_path}/star{artifact["星级"]+1}.png', size=(100, 100))
            # bg.alpha_composite(artifact_bg, (270 + 317 * offset_x, 1002 + offset_y))
            reli_icon = f"{reli_path}/{artifact['名称']}.png"
            reli_icon = await get_img(
                url=resource_url.format(artifact["图标"]),
                size=(100, 100),
                save_path=reli_icon,
                mode="RGBA",
            )
            bg.alpha_composite(reli_icon, (270 + 317 * offset_x, 1002 + offset_y))
            bg_draw.text(
                (94 + 317 * offset_x, 951 + offset_y),
                artifact["名称"],
                fill="white",
                font=get_font(30),
            )
            bg_draw.text(
                (95 + 317 * offset_x, 998 + offset_y),
                f"{artifact_score}-{round(grade, 1)}",
                fill="#ffde6b",
                font=get_font(28, "number.ttf"),
            )
            level_mask = load_image(path=f"{other_path}/等级遮罩.png")
            bg.alpha_composite(
                level_mask.resize((98, 30)), (95 + 317 * offset_x, 1032 + offset_y)
            )
            if artifact["等级"] != 15 or not artifact_score:
                no_list = "*"
            draw_center_text(
                bg_draw,
                f"LV{artifact['等级']}",
                95 + 317 * offset_x,
                95 + 317 * offset_x + 98,
                1033 + offset_y,
                "black",
                get_font(27, "number.ttf"),
            )
            bg_draw.text(
                (94 + 317 * offset_x, 1069 + offset_y),
                artifact["主属性"]["属性名"],
                fill="white",
                font=get_font(25),
            )
            if artifact["主属性"]["属性名"] not in integer_property:
                bg_draw.text(
                    (91 + 317 * offset_x, 1100 + offset_y),
                    f"+{math.floor(artifact['主属性']['属性值']) / 100}%",
                    fill="white",
                    font=get_font(48, "number.ttf"),
                )
            else:
                bg_draw.text(
                    (91 + 317 * offset_x, 1100 + offset_y),
                    f"+{math.floor(artifact['主属性']['属性值'])}",
                    fill="white",
                    font=get_font(48, "number.ttf"),
                )
        for j in range(len(artifact["词条"])):
            text = artifact["词条"][j]["属性名"].replace("百分比", "")
            up_num = ""
            if (up := artifact["词条"][j]["提升次数"]) > 0:
                up_num = (
                    "¹"
                    if up == 1
                    else "²"
                    if up == 2
                    else "³"
                    if up == 3
                    else "⁴"
                    if up == 4
                    else "⁵"
                )
                x_offset = 25 * len(text)
                bg_draw.text(
                    (94 + 317 * offset_x + x_offset, 1163 + offset_y + 50 * j - 5),
                    up_num,
                    fill="white"
                    if check_effective(artifact["词条"][j]["属性名"], effective)
                    else "#afafaf",
                    font=get_font(25, "tahomabd.ttf"),
                )
            bg_draw.text(
                (94 + 317 * offset_x, 1163 + offset_y + 50 * j),
                text,
                fill="white"
                if check_effective(artifact["词条"][j]["属性名"], effective)
                else "#afafaf",
                font=get_font(25),
            )
            if artifact["词条"][j]["属性名"] not in integer_property:
                num = "+" + str(math.floor(artifact["词条"][j]["属性值"]) / 100) + "%"
            else:
                num = "+" + str(math.floor(artifact["词条"][j]["属性值"]))
            artifact_pk_info["副属性"].append(
                {
                    "属性名": text,
                    "属性值": artifact["词条"][j]["属性值"],
                    "强化次数": up_num,
                    "颜色": "white"
                    if check_effective(artifact["词条"][j]["属性名"], effective)
                    else "#afafaf",
                }
            )
            draw_right_text(
                bg_draw,
                num,
                362 + 317 * offset_x,
                1163 + offset_y + 50 * j,
                fill="white"
                if check_effective(artifact["词条"][j]["属性名"], effective)
                else "#afafaf",
                font=get_font(25, "number.ttf"),
            )
        if artifact_pk_info not in artifact_pk:
            artifact_pk.append(copy.deepcopy(artifact_pk_info))
        if artifact not in artifact_all[i] and artifact["等级"] == 15:
            artifact_all[i].append(copy.deepcopy(artifact))

    player_info.data["驱动盘榜单"] = sorted(
        player_info.data["驱动盘榜单"], key=lambda x: float(x["评分"]), reverse=True
    )[:20]
    data["评分"] = total_all
    if total_cnt != 6:
        no_list = "*"
    if not only_cal:
        # 驱动盘评分
        if total_cnt and total_all <= 55 * total_cnt:
            # score_ave = total_all / total_cnt
            # score_ave = round(score_ave)
            """
            total_rank = 'ACE' if score_ave > 66 else 'ACE' if score_ave > 56.1 else 'ACE' if score_ave > 49.5 \
                else 'SSS' if score_ave > 42.9 else 'SS' if score_ave > 36.3 else 'S' if score_ave > 29.7 else 'A' \
                if score_ave > 23.1 else 'B' if score_ave > 16.5 else 'C' if score_ave > 10 else 'D'
            """
            total_rank = (
                "ACE"
                if total_all >= 210
                else "SSS"
                if total_all >= 190
                else "SS"
                if total_all >= 170
                else "S"
                if total_all >= 150
                else "A"
                if total_all >= 130
                else "B"
                if total_all >= 110
                else "C"
                if total_all >= 90
                else "D"
            )
            total_rank = (
                "ACE*"
                if total_all >= 297
                else "ACE"
                if total_all >= 264
                else "SSS"
                if total_all >= 231
                else "SS"
                if total_all >= 198
                else "S"
                if total_all >= 165
                else "A"
                if total_all >= 132
                else "B"
                if total_all >= 99
                else "C"
                if total_all >= 66
                else "D"
            )
        else:
            total_rank = "D"
        total_int = round(total_all)

        # bg_draw.text((119 + 480 - 90 + 38, 1057 - 360 - 20 - 33), "总评分", fill="#afafaf", font=get_font(50))
        bg_draw.text(
            (119 + 480 - 90 + 38, 1057 - 360 - 20 - 33),
            f"影画 {data['影画']}",
            fill="white",
            font=get_font(50),
        )

        rank_icon = load_image(f"{other_path}/评分{total_rank[0]}.png", mode="RGBA")
        x_offset = 204 + 440 - 20
        y_offset = -193 - 110 + 3 + 3 - 33
        score_x_offset = 204 + 440
        score_y_offset = -193 - 110 + 3 - 33

        if total_rank in ["ACE", "ACE*"]:
            rank_icon = load_image(
                f"{other_path}/ACE-A.png", mode="RGBA", size=(55, 73)
            )
            bg.alpha_composite(rank_icon, (95 + x_offset, 967 + y_offset))
            rank_icon = load_image(
                f"{other_path}/ACE-C.png", mode="RGBA", size=(55, 73)
            )
            bg.alpha_composite(rank_icon, (145 + x_offset, 967 + y_offset))
            rank_icon = load_image(
                f"{other_path}/ACE-E.png", mode="RGBA", size=(55, 73)
            )
            bg.alpha_composite(rank_icon, (195 + x_offset, 967 + y_offset))
            bg_draw.text(
                (250 + score_x_offset, 974 + score_y_offset),
                str(total_int),
                fill="white",
                font=get_font(60, "number.ttf"),
            )
        elif len(total_rank) == 3:
            bg.alpha_composite(rank_icon, (95 + x_offset, 967 + y_offset))
            bg.alpha_composite(rank_icon, (145 + x_offset, 967 + y_offset))
            bg.alpha_composite(rank_icon, (195 + x_offset, 967 + y_offset))
            bg_draw.text(
                (250 + score_x_offset, 974 + score_y_offset),
                str(total_int),
                fill="white",
                font=get_font(60, "number.ttf"),
            )
        elif len(total_rank) == 2:
            bg.alpha_composite(rank_icon, (125 + x_offset - 11, 967 + y_offset))
            bg.alpha_composite(rank_icon, (175 + x_offset - 11, 967 + y_offset))
            bg_draw.text(
                (235 + score_x_offset, 974 + score_y_offset),
                str(total_int),
                fill="white",
                font=get_font(60, "number.ttf"),
            )
        else:
            bg.alpha_composite(rank_icon, (143 + x_offset - 18, 967 + y_offset))
            bg_draw.text(
                (217 + score_x_offset, 974 + score_y_offset),
                str(total_int),
                fill="white",
                font=get_font(60, "number.ttf"),
            )

        # 驱动盘套装
        suit_4, suit_2 = get_artifact_suit(
            [item.get("所属套装", "") for item in data["驱动盘"]]
        )
        if len(suit_4) != 1 and (len(suit_2) != 3 and len(suit_2) != 1):
            no_list = "*"
        """
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
        """
    effect = {}
    for item in effective:
        name = (
            item.replace("百分比", "%")
            .replace("暴击率", "暴击")
            .replace("暴击伤害", "爆伤")
            .replace("异常", "")
            .replace("能量回复", "回能")
            .replace("力", "")
            .replace("值", "")
        )
        if name not in effect:
            effect[name] = effective.get(item)
    effect = dict(sorted(effect.items(), key=lambda x: x[1], reverse=True))
    effect = str(effect).replace("'", "").replace(" ", "").strip("{}")

    if "-" not in weight_name:
        weight_name = "通用"
    else:
        weight_name = weight_name[-2:]
    draw_center_text(
        bg_draw,
        f"{weight_name}:{effect}",
        0,
        1080,
        bg.size[1] - 85,
        "#afafaf",
        get_font(30),
    )
    date = re.sub(r"\d{4}-", "", data["更新时间"])
    draw_center_text(
        bg_draw,
        f"Updated on {date[:-3]} | v{plugin_version} | Powered by Enka",
        0,
        1080,
        bg.size[1] - 50,
        "#ffffff",
        get_font(36, "优设标题黑.ttf"),
    )
    return bg, str(total_all) + no_list if no_list == "*" else total_all
