from ..utils.card_utils import relic, relic_sub_value, role_score, trans_data

sub_grow_max_value = {  # 词条成长值
    "攻击力": 21,
    "生命值": 42,
    "防御力": 21,
    "百分比生命值": 0.0432,
    "百分比攻击力": 0.0432,
    "百分比防御力": 0.054,
    "速度": 2.6,
    "暴击率": 0.0324,
    "暴击伤害": 0.0648,
    "效果命中": 0.0432,
    "效果抵抗": 0.0432,
    "击破特攻": 0.0648,
}
main_max_value = [
    {"生命值": 705.5},
    {"攻击": 352.7},
    {"百分比生命值": 43.2, "百分比攻击力": 43.2, "百分比防御力": 54, "暴击率": 32.4, "暴击伤害": 64.8, "治疗加成": 34.56, "效果命中": 43.2},
    {"百分比生命值": 43.2, "百分比攻击力": 43.2, "百分比防御力": 54, "速度": 25},
    {
        "百分比生命值": 43.2,
        "百分比攻击力": 43.2,
        "百分比防御力": 54,
        "伤害加成": 38.88,
    },
    {"百分比生命值": 43.2, "百分比攻击力": 43.2, "百分比防御力": 54, "击破特攻": 81, "能量恢复效率": 19},
]
integer_property = ["生命值", "攻击力", "防御力", "速度"]
small_property = ["生命值", "攻击力", "防御力"]


def get_full_times(effective, artifact, pos_idx):
    sorted_items = sorted(effective.items(), key=lambda x: x[1] if x[0] not in small_property else x[1] * 0.3, reverse=True)
    times = []
    best_find = 0
    # 只考虑副词条
    if pos_idx <= 1:
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
        print(main_name)
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
        print(times)
    return sum(times) / 100


def get_artifact_score(effective, artifact, role_info, pos_idx):
    # sub_score = []
    # for sub in artifact["词条"]:
    #     val = sub["属性值"] if sub["属性名"] in integer_property else sub["属性值"] * 100
    #     if sub["属性名"] in ["生命值", "攻击力", "防御力"]:
    #         sub_name = f"百分比{sub['属性名']}"
    #         val = val / role_info["属性"][f"基础{sub['属性名']}"] * 100
    #     else:
    #         sub_name = sub["属性名"]
    #     sub_score.append(effective.get(sub_name, 0) * val / sub_grow_max_value.get(sub_name, 1000000) / 100 * 55 / role_score["满词条"].get(role_info["名称"], [0, 0, 0, 0, 0, 0])[pos_idx])
    # # 主词条得分（与副词条计算规则一致，但只取 25%），角色元素属性与伤害属性不同时不得分，不影响物理伤害得分
    # val = artifact["主属性"]["属性值"] if artifact["主属性"]["属性名"] in integer_property else artifact["主属性"]["属性值"] * 100
    # main_name = "伤害加成" if "伤害加成" in artifact["主属性"]["属性名"] else artifact["主属性"]["属性名"]
    # main_score = (
    #     0
    #     if pos_idx < 2
    #     else 0.3 * effective.get(main_name, 0) * val / main_max_value[pos_idx].get(artifact["主属性"]["属性名"], 1000000) * 10 / 100 * 55 / role_score["满词条"].get(role_info["名称"], [0, 0, 0, 0, 0, 0])[pos_idx]
    # )
    #
    # all_score = sum(sub_score) + main_score
    # 圣遗物强化次数
    prop = relic_sub_value[relic[artifact["ID"]]["sub_affix_id"]]["affixes"]
    grow_value = {}
    for item in prop.values():
        item_prop = {trans_data["property"][item["property"]]: item["base"]}
        grow_value.update(item_prop)
    mark = []
    for index, s in enumerate(artifact["词条"]):
        print(s["属性值"], s["属性名"])
        va = s["属性值"]
        # mark.append(s["属性值"] / grow_value[s["属性名"]] - 1)
        mark.append(max(0, va / sub_grow_max_value[s["属性名"]] - 1))

    # 最终圣遗物评级
    times = get_full_times(effective, artifact, pos_idx)
    sub_score = []
    for index, sub in enumerate(artifact["词条"]):
        mark_sub = mark[index]
        score = (1 + mark_sub) * effective.get(sub["属性名"], 0) / 100
        if sub["属性名"] in small_property:
            score *= 0.3
        sub_score.append(score)
    if pos_idx < 2:
        main_score = 0
    else:
        main_name = artifact["主属性"]["属性名"]
        main_name = "伤害加成" if "伤害加成" in main_name else main_name
        print(main_name, effective.get(main_name, 0))
        main_score = effective.get(main_name, 0) / 100 * 3 * (0.25 + 0.05 * artifact["等级"])

    all_score = 55 / times * (sum(sub_score) + main_score)
    calc_rank_str = (
        "ACE" if all_score > 43.7 else "SSS" if all_score > 37.8 else "SS" if all_score > 33.5 else "S" if all_score > 29.1 else "A" if all_score > 23.3 else "B" if all_score > 17.5 else "C" if all_score > 11.6 else "D"
    )
    calc_rank_str = (
        "ACE*"
        if all_score >= 44
        else "ACE"
        if all_score >= 38.5
        else "SSS"
        if all_score >= 33
        else "SS"
        if all_score >= 27.5
        else "S"
        if all_score >= 22
        else "A"
        if all_score >= 16.5
        else "B"
        if all_score > 11.5
        else "C"
        if all_score > 6
        else "D"
    )
    mark = list(map(round, mark))
    return calc_rank_str, all_score, mark


def get_effective(data):
    """
    根据角色的武器、圣遗物来判断获取该角色有效词条列表
    :param data: 角色信息
    :return: 有效词条列表
    """
    role_name = data["名称"]
    return role_score["权重"].get(role_name, {}), role_name


def check_effective(prop_name: str, effective: dict):
    """
    检查词条是否有效
    :param prop_name: 词条属性名
    :param effective: 有效词条列表
    :return: 是否有效
    """
    if ("攻击力" in effective or "百分比攻击力" in effective) and "攻击力" in prop_name:
        return True
    if ("生命值" in effective or "百分比生命值" in effective) and "生命值" in prop_name:
        return True
    if ("防御力" in effective or "百分比防御力" in effective) and "防御力" in prop_name:
        return True
    return prop_name in effective
