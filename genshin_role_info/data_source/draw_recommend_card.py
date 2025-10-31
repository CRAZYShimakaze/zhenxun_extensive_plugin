import copy

from ..utils.artifact_utils import check_effective, get_artifact_score, get_effective, get_miao_score
from ..utils.card_utils import json_path, role_score
from ..utils.image_utils import image_build
from ..utils.json_utils import load_json
from .draw_artifact_card import draw_artifact_card
from .draw_role_card import draw_role_card

avatar_url = "https://enka.network/ui/{}.png"
qq_logo_url = "http://q1.qlogo.cn/g?b=qq&nk={}&s=640"
role_info_json = load_json(f"{json_path}/role_info.json")

convert = {
    "main_prop": {
        "爆伤": "暴击伤害",
        "暴击": "暴击率",
        "精通": "元素精通",
        "生命": "百分比生命值",
        "防御": "百分比防御力",
        "攻击": "百分比攻击力",
        "火伤": "火元素伤害加成",
        "冰伤": "冰元素伤害加成",
        "雷伤": "雷元素伤害加成",
        "物伤": "物理伤害加成",
        "风伤": "风元素伤害加成",
        "水伤": "水元素伤害加成",
        "岩伤": "岩元素伤害加成",
        "草伤": "草元素伤害加成",
        "治疗": "治疗加成",
        "充能": "元素充能效率",
    },
    "suit_name": {
        "冰风": "冰风迷途的勇士",
        "角斗": "角斗士的终幕礼",
        "余响": "来歆余响",
        "磐岩": "悠古的磐岩",
        "饰金": "饰金之梦",
        "流星": "逆飞的流星",
        "辰砂": "辰砂往生录",
        "宗室": "昔日宗室之仪",
        "剧团": "黄金剧团",
        "逐影": "逐影猎人",
        "沉沦": "沉沦之心",
        "花海": "花海甘露之光",
        "绝缘": "绝缘之旗印",
        "谐律": "谐律异想断章",
        "乐园": "乐园遗落之花",
        "海染": "海染砗磲",
        "遐思": "未竟的遐思",
        "水仙": "水仙之梦",
        "少女": "被怜爱的少女",
        "追忆": "追忆之注连",
        "华馆": "华馆梦醒形骸记",
        "染血": "染血的骑士道",
        "回声": "回声之林夜话",
        "渡火": "渡过烈火的贤人",
        "昔时": "昔时之歌",
        "平雷": "平息鸣雷的尊者",
        "深林": "深林的记忆",
        "苍白": "苍白之火",
        "沙上": "沙上楼阁史话",
        "如雷": "如雷的盛怒",
        "千岩": "千岩牢固",
        "魔女": "炽烈的炎之魔女",
        "乐团": "流浪大地的乐团",
        "翠绿": "翠绿之影",
    },
}


def sort_recommend(artifact, position):
    artifact_recommend = []
    for role_name_full, effective in role_score.items():
        role_name = role_name_full.split("-")[0]
        if "主" in role_name or "旅行者" in role_name:
            role_name = "空"
        affix_weight, point_mark, max_mark = get_miao_score(effective, role_info_json[role_name]["属性"])
        artifact_score, grade, mark = get_artifact_score(point_mark, max_mark, artifact, role_info_json[role_name]["元素"], position)

        artifact_pk_info = {"角色": role_name}
        artifact_pk_info["星级"] = artifact["星级"]
        artifact_pk_info["图标"] = artifact["图标"]
        artifact_pk_info["名称"] = role_name_full
        artifact_pk_info["评分"] = grade
        artifact_pk_info["评级"] = artifact_score
        artifact_pk_info["等级"] = artifact["等级"]
        artifact_pk_info["主属性"] = {"属性名": artifact["主属性"]["属性名"], "属性值": artifact["主属性"]["属性值"]}
        artifact_pk_info["副属性"] = []
        for j in range(len(artifact["词条"])):
            text = artifact["词条"][j]["属性名"].replace("百分比", "")
            up_num = ""
            if mark[j] != 0:
                up_num = "¹" if mark[j] == 1 else "²" if mark[j] == 2 else "³" if mark[j] == 3 else "⁴" if mark[j] == 4 else "⁵"
            if artifact["词条"][j]["属性名"] not in ["攻击力", "防御力", "生命值", "元素精通"]:
                num = "+" + str(artifact["词条"][j]["属性值"]) + "%"
            else:
                num = "+" + str(artifact["词条"][j]["属性值"])
            artifact_pk_info["副属性"].append({"属性名": text, "属性值": num, "强化次数": up_num, "颜色": "white" if check_effective(artifact["词条"][j]["属性名"], effective) else "#afafaf"})
        artifact_recommend.append(copy.deepcopy(artifact_pk_info))
        if len(artifact_recommend) > 20:
            artifact_recommend = sorted(artifact_recommend, key=lambda x: float(x["评分"]), reverse=True)[:20]
    return artifact_recommend


async def gen_artifact_adapt(title, artifact, uid, role, pos, plugin_version):
    artifact_info = sort_recommend(artifact, pos)
    return await draw_artifact_card(title, role, uid, artifact_info, ace2_num=0, ace_num=0, plugin_version=plugin_version)


async def gen_artifact_recommend(title, data, artifact_list, uid, role_name, pos, element, suit, plugin_version):
    artifact_all = []

    ori_artifact = data["圣遗物"][pos]
    for artifact in artifact_list:
        if convert["main_prop"].get(element, "") not in artifact["主属性"]["属性名"]:
            continue
        if suit not in artifact["所属套装"]:
            continue
        artifact_pk_info = {}
        if ori_artifact == artifact:
            artifact_pk_info["角色"] = role_name
        elif "角色" in artifact:
            # pass
            artifact_pk_info["角色"] = artifact["角色"]
        data["圣遗物"][pos] = artifact
        effective, _ = get_effective(data)
        affix_weight, point_mark, max_mark = get_miao_score(effective, role_info_json[role_name]["属性"])
        artifact_score, grade, mark = get_artifact_score(point_mark, max_mark, artifact, role_info_json[role_name]["元素"], pos)
        artifact_pk_info["星级"] = artifact["星级"]
        artifact_pk_info["图标"] = artifact["图标"]
        artifact_pk_info["名称"] = artifact["名称"]
        artifact_pk_info["评分"] = grade
        artifact_pk_info["评级"] = artifact_score
        artifact_pk_info["等级"] = artifact["等级"]
        artifact_pk_info["主属性"] = {"属性名": artifact["主属性"]["属性名"], "属性值": artifact["主属性"]["属性值"]}
        artifact_pk_info["副属性"] = []
        for j in range(len(artifact["词条"])):
            text = artifact["词条"][j]["属性名"].replace("百分比", "")
            up_num = ""
            if mark[j] != 0:
                up_num = "¹" if mark[j] == 1 else "²" if mark[j] == 2 else "³" if mark[j] == 3 else "⁴" if mark[j] == 4 else "⁵"
            if artifact["词条"][j]["属性名"] not in ["攻击力", "防御力", "生命值", "元素精通"]:
                num = "+" + str(artifact["词条"][j]["属性值"]) + "%"
            else:
                num = "+" + str(artifact["词条"][j]["属性值"])
            artifact_pk_info["副属性"].append({"属性名": text, "属性值": num, "强化次数": up_num, "颜色": "white" if check_effective(artifact["词条"][j]["属性名"], effective) else "#afafaf"})
        if artifact_pk_info not in artifact_all:
            artifact_all.append(copy.deepcopy(artifact_pk_info))
        artifact_all = sorted(artifact_all, key=lambda x: float(x["评分"]), reverse=True)[: 20 if len(artifact_all) > 20 else len(artifact_all)]
    if not artifact_all:
        return None, None
    return await draw_artifact_card(title, role_name, uid, artifact_all, ace2_num=0, ace_num=0, plugin_version=plugin_version)


async def gen_suit_recommend(title, data, player_info, uid, role_name, suit, occupy, plugin_version):
    artifact_list = player_info.data["圣遗物列表"]
    artifact_best_same = [0, 0, 0, 0, 0]
    artifact_best = [0, 0, 0, 0, 0]
    artifact_best_same_score = [0, 0, 0, 0, 0]
    artifact_best_score = [0, 0, 0, 0, 0]
    effective, _ = get_effective(data)
    prop_diff = {
        "暴击率": 0,
        "暴击伤害": 0,
        "元素精通": 0,
        "百分比攻击力": 0,
        "百分比生命值": 0,
        "百分比防御力": 0,
        "元素充能效率": 0,
        "元素伤害加成": 0,
        "物理伤害加成": 0,
        "治疗加成": 0,
        "攻击力": 0,
        "生命值": 0,
        "防御力": 0,
    }
    element_before = ""
    element_after = ""
    for pos in range(5):
        if data["圣遗物"][pos]["主属性"]["属性名"] in prop_diff:
            prop_diff[data["圣遗物"][pos]["主属性"]["属性名"]] -= data["圣遗物"][pos]["主属性"]["属性值"]
        else:
            element_before = data["圣遗物"][pos]["主属性"]["属性名"].replace("元素伤害加成", "")
            prop_diff["元素伤害加成"] -= data["圣遗物"][pos]["主属性"]["属性值"]
        for affix in data["圣遗物"][pos]["词条"]:
            prop_diff[affix["属性名"]] -= affix["属性值"]
        pos_artifact = artifact_list[pos]
        best_grade_same_score = 0
        best_grade_score = 0
        for artifact in pos_artifact:
            if occupy and artifact["角色"] not in ["", role_name]:
                continue
            best_grade_same = False
            best_grade = False
            artifact_pk_info = {}
            data["圣遗物"][pos] = artifact
            # effective, _ = get_effective(data)
            affix_weight, point_mark, max_mark = get_miao_score(effective, role_info_json[role_name]["属性"])
            artifact_score, grade, mark = get_artifact_score(point_mark, max_mark, artifact, role_info_json[role_name]["元素"], pos)
            if grade >= best_grade_score or grade >= best_grade_same_score:
                if grade >= best_grade_same_score and suit in artifact["所属套装"]:
                    best_grade_same_score = grade
                    best_grade_same = True
                if grade >= best_grade_score:
                    best_grade_score = grade
                    best_grade = True
            else:
                continue

            if best_grade_same:
                artifact_best_same[pos] = copy.deepcopy(artifact)
                artifact_best_same_score[pos] = grade
            if best_grade:
                artifact_best[pos] = copy.deepcopy(artifact)
                artifact_best_score[pos] = grade
    score_list = [0, 0, 0, 0, 0]
    for i in range(5):
        score_list[i] = sum(artifact_best_same_score) - artifact_best_same_score[i] + artifact_best_score[i]
    best_idx = score_list.index(max(score_list))
    for i in range(5):
        data["圣遗物"][i] = artifact_best_same[i] if i != best_idx else artifact_best[i]
        if not data["圣遗物"][i]:
            return 0
        if data["圣遗物"][i]["主属性"]["属性名"] in prop_diff:
            prop_diff[data["圣遗物"][i]["主属性"]["属性名"]] += data["圣遗物"][i]["主属性"]["属性值"]
        else:
            element_after = data["圣遗物"][i]["主属性"]["属性名"].replace("元素伤害加成", "")
            prop_diff["元素伤害加成"] += data["圣遗物"][i]["主属性"]["属性值"]
        for affix in data["圣遗物"][i]["词条"]:
            prop_diff[affix["属性名"]] += affix["属性值"]
    ele_list = [
        "火",
        "雷",
        "水",
        "草",
        "风",
        "岩",
        "冰",
    ]
    data["属性"]["额外生命"] += prop_diff["生命值"] + data["属性"]["基础生命"] * prop_diff["百分比生命值"] / 100
    data["属性"]["额外生命"] = round(data["属性"]["额外生命"])
    data["属性"]["额外攻击"] += prop_diff["攻击力"] + data["属性"]["基础攻击"] * prop_diff["百分比攻击力"] / 100
    data["属性"]["额外攻击"] = round(data["属性"]["额外攻击"])
    data["属性"]["额外防御"] += prop_diff["防御力"] + data["属性"]["基础防御"] * prop_diff["百分比防御力"] / 100
    data["属性"]["额外防御"] = round(data["属性"]["额外防御"])
    data["属性"]["暴击率"] += prop_diff["暴击率"] / 100
    data["属性"]["暴击伤害"] += prop_diff["暴击伤害"] / 100
    data["属性"]["元素精通"] += prop_diff["元素精通"]
    data["属性"]["元素充能效率"] += prop_diff["元素充能效率"] / 100
    data["属性"]["治疗加成"] += prop_diff["治疗加成"] / 100

    data["属性"]["暴击率"] = max(0, data["属性"]["暴击率"])
    data["属性"]["暴击伤害"] = max(0, data["属性"]["暴击伤害"])
    data["属性"]["元素精通"] = max(0, data["属性"]["元素精通"])
    data["属性"]["元素充能效率"] = max(0, data["属性"]["元素充能效率"])
    data["属性"]["治疗加成"] = max(0, data["属性"]["治疗加成"])
    if any([element_before, element_after]):
        data["属性"]["伤害加成"][ele_list.index(element_before or element_after)] = prop_diff["元素伤害加成"] / 100
    img, _ = await draw_role_card(uid, data, player_info, plugin_version, False, title)
    return image_build(img=img, quality=100, mode="RGB")
