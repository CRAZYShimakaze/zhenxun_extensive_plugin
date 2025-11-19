from ..utils.card_utils import score_json

integer_property = ["生命值", "攻击力", "防御力", "异常精通", "穿透值", "贯穿力"]
small_property = ["生命值", "攻击力", "防御力"]
sub_grow_max_value = {  # 词条成长值
    "攻击力": 19,
    "生命值": 112,
    "防御力": 15,
    "生命值百分比": 3,
    "攻击力百分比": 3,
    "防御力百分比": 4.8,
    "暴击率": 2.4,
    "暴击伤害": 4.8,
    "异常精通": 9,
    "穿透值": 9,
}
main_max_value = [
    {"生命值": 2200},
    {"攻击力": 316},
    {"防御力": 184},
    {"生命值百分比": 30, "攻击力百分比": 30, "防御力百分比": 48, "异常精通": 92, "暴击率": 24, "暴击伤害": 48},
    {"生命值百分比": 30, "攻击力百分比": 30, "防御力百分比": 48, "穿透率": 24, "属性加伤": 30},
    {"生命值百分比": 30, "攻击力百分比": 30, "防御力百分比": 48, "能量回复": 60, "冲击力": 18, "异常掌控": 30},
]


def get_full_times(effective, artifact, pos_idx):
    sorted_items = sorted(effective.items(), key=lambda x: x[1] if x[0] not in small_property else x[1] * 0.3, reverse=True)
    times = []
    best_find = 0
    # 只考虑副词条
    if pos_idx <= 2:
        for i, (key, value) in enumerate(sorted_items):
            if key in sub_grow_max_value.keys() and not best_find:
                if key in small_property:
                    times.append(value * 6 * 0.3)
                else:
                    times.append(value * 6)
                best_find = 1

            elif key in sub_grow_max_value.keys():
                if key in small_property:
                    times.append(value * 0.3)
                else:
                    times.append(value)
            if len(times) == 4:
                break
    else:
        # 先确定主词条
        main_find = 0
        bak_find = 0
        main_name = ""
        bak_name = ""
        times.append(0)
        for i, (key, value) in enumerate(sorted_items):
            if key in main_max_value[pos_idx].keys() and not main_find:
                if key not in sub_grow_max_value.keys():
                    times[0] = value * 3 * (0.25 + 0.05 * artifact["等级"])
                    main_find = 1
                    main_name = key
                    break
                elif not bak_find:
                    times[0] = value * 3 * (0.25 + 0.05 * artifact["等级"])
                    bak_find = 1
                    bak_name = key
        else:
            if not main_find:
                if bak_find:
                    main_name = bak_name
        #print(main_name)
        # 再确定副词条
        for i, (key, value) in enumerate(sorted_items):
            if key == main_name:
                continue
            if key in sub_grow_max_value.keys() and not best_find:
                if key in small_property:
                    times.append(value * 6 * 0.3)
                else:
                    times.append(value * 6)
                best_find = 1
            elif key in sub_grow_max_value.keys():
                if key in small_property:
                    times.append(value * 0.3)
                else:
                    times.append(value)
            if len(times) == 5:
                break
        #print(times)
    return sum(times) / 100


def get_artifact_score(effective, artifact, role_info, pos_idx):
    times = get_full_times(effective, artifact, pos_idx)
    sub_score = 0
    for sub in artifact["词条"]:
        score = (1 + sub["提升次数"]) * effective.get(sub["属性名"], 0) / 100
        if sub["属性名"] in small_property:
            score *= 0.3
        sub_score += score
    if pos_idx < 3:
        main_score = 0
    else:
        main_name = artifact["主属性"]["属性名"]
        main_name = "属性加伤" if "伤害加成" in main_name else main_name
        main_name = "能量回复" if "能量自动回复" in main_name else main_name
        main_score = effective.get(main_name, 0) / 100 * 3 * (0.25 + 0.05 * artifact["等级"])

    all_score = 55 / times * (sub_score + main_score)

    # 最终圣遗物评级

    calc_rank_str = (
        "ACE"
        if all_score >= 35
        else "SSS"
        if all_score >= 190 / 6
        else "SS"
        if all_score >= 170 / 6
        else "S"
        if all_score >= 150 / 6
        else "A"
        if all_score >= 130 / 6
        else "B"
        if all_score > 110 / 6
        else "C"
        if all_score > 90 / 6
        else "D"
    )
    calc_rank_str = (
        "ACE*"
        if all_score >= 49.5
        else "ACE"
        if all_score >= 44
        else "SSS"
        if all_score >= 38.5
        else "SS"
        if all_score >= 33
        else "S"
        if all_score >= 27.5
        else "A"
        if all_score >= 28
        else "B"
        if all_score > 22
        else "C"
        if all_score > 16.5
        else "D"
    )
    return calc_rank_str, all_score


def get_effective(data):
    """
    根据角色的武器、圣遗物来判断获取该角色有效词条列表
    :param data: 角色信息
    :return: 有效词条列表
    """
    role_name = data["名称"]
    return score_json["权重"].get(role_name, {"攻击力百分比": 75, "暴击率": 100, "暴击伤害": 100}), role_name


def check_effective(prop_name: str, effective: dict):
    """
    检查词条是否有效
    :param prop_name: 词条属性名
    :param effective: 有效词条列表
    :return: 是否有效
    """
    if ("攻击力" in effective or "攻击力百分比" in effective) and "攻击力" in prop_name:
        return True
    if ("生命值" in effective or "生命值百分比" in effective) and "生命值" in prop_name:
        return True
    if ("防御力" in effective or "防御力百分比" in effective) and "防御力" in prop_name:
        return True
    return prop_name in effective
