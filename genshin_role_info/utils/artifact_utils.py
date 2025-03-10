import copy
import math

from ..utils.card_utils import convert, role_ori

weapon_cfg = {
    "磐岩结绿": {
        "attr": "百分比生命值",
        "abbr": "绿剑",
        "max": 30,
        "min": 15
    },
    "猎人之径": {
        "attr": "元素精通"
    },
    "薙草之稻光": {
        "attr": "元素充能效率",
        "abbr": "薙刀"
    },
    "护摩之杖": {
        "attr": "百分比生命值",
        "abbr": "护摩",
        "max": 18,
        "min": 10
    }
}

grow_max_value = {  # 词条成长值
    "暴击率": 3.89,
    "暴击伤害": 7.77,
    "元素精通": 23.31,
    "百分比攻击力": 5.83,
    "百分比生命值": 5.83,
    "百分比防御力": 7.29,
    "元素充能效率": 6.48,
    "元素伤害加成": 5.825,
    "物理伤害加成": 7.288,
    "治疗加成": 4.487,
    "攻击力": 19.45,
    "生命值": 298.75,
    "防御力": 23.15,
}
grow_min_value = {  # 词条成长值
    "暴击率": 2.72,
    "暴击伤害": 5.44,
    "元素精通": 16.32,
    "百分比攻击力": 4.08,
    "百分比生命值": 4.08,
    "百分比防御力": 5.1,
    "元素充能效率": 4.53,
    "攻击力": 13.62,
    "生命值": 209.13,
    "防御力": 16.2,
}


def get_artifact_score(point_mark, max_mark, artifact, element, pos_idx):
    # 主词条得分（与副词条计算规则一致，但只取 25%），角色元素属性与伤害属性不同时不得分，不影响物理伤害得分
    main_name = artifact['主属性']['属性名'].replace(element, '')
    calc_main = (0.0 if pos_idx < 2 else point_mark.get(main_name, 0) * artifact['主属性'][
        '属性值'] * 46.6 / 6 / 100 / 4)
    # 副词条得分
    calc_subs = [
        # [词条名, 词条数值, 词条得分]
        [s['属性名'], s['属性值'],
         point_mark.get(s['属性名'], 0) * s[
             '属性值'] * 46.6 / 6 / 100, ] for s in
        artifact['词条']]
    # 主词条收益系数（百分数），沙杯头位置主词条不正常时对圣遗物总分进行惩罚，最多扣除 50% 总分
    calc_main_pct = (100 if pos_idx < 2 else (100 - 50 * (
            1 - point_mark.get(main_name, 0) * artifact['主属性']['属性值'] /
            max_mark[str(pos_idx)]["main"] / 2 / 4)))
    # 总分对齐系数（百分数），按满分 66 对齐各位置圣遗物的总分
    calc_total_pct = 66 / (max_mark[str(pos_idx)]["total"] * 46.6 / 6 / 100) * 100
    # 最终圣遗物总分
    calc_total = ((calc_main + sum(s[2] for s in calc_subs)) * calc_main_pct / 100 * calc_total_pct / 100)
    # 圣遗物强化次数
    mark = []
    diff = []
    for index, s in enumerate(artifact['词条']):
        max_num = min(artifact['等级'] // 4, math.floor(round(s['属性值'] / grow_min_value.get(s['属性名']) * 1, 1)))
        min_num = max(1, math.ceil(round(s['属性值'] / grow_max_value.get(s['属性名']) * 1, 1)))
        avg_num = max(1,
                      round(s['属性值'] * 2 / (grow_min_value.get(s['属性名']) + grow_max_value.get(s['属性名'])) * 1))
        if max_num != min_num:
            diff.append(index)
            mark.append(avg_num - 1)
        else:
            mark.append(min_num - 1)
    while sum(mark) > artifact['等级'] // 4 and len(diff) != 0:
        mark[diff[0]] -= 1
        diff.pop(0)
    if calc_total > 42.9:
        while sum(mark) < artifact['等级'] // 4 and len(diff) != 0:
            mark[diff[0]] += 1
            diff.pop(0)
    # 最终圣遗物评级
    calc_rank_str = 'ACE*' if calc_total > 66.1 else 'ACE*' if calc_total > 56.1 else 'ACE' if calc_total > 49.5 \
        else 'SSS' if calc_total > 42.9 else 'SS' if calc_total > 36.3 else 'S' if calc_total > 29.7 else 'A' \
        if calc_total > 23.1 else 'B' if calc_total > 16.5 else 'C' if calc_total > 10 else 'D'
    return calc_rank_str, calc_total, mark


def get_miao_score(affix_weight, base_info):
    grow_value = {  # 词条成长值
        "暴击率": 3.89,
        "暴击伤害": 7.77,
        "元素精通": 23.31,
        "百分比攻击力": 5.83,
        "百分比生命值": 5.83,
        "百分比防御力": 7.29,
        "元素充能效率": 6.48,
        "元素伤害加成": 5.825,
        "物理伤害加成": 7.288,
        "治疗加成": 4.487,
        "攻击力": 19.45,
        "生命值": 298.75,
        "防御力": 23.15,
    }
    main_affixs = {  # 可能的主词条
        "2": "百分比攻击力,百分比防御力,百分比生命值,元素精通,元素充能效率".split(","),  # EQUIP_SHOES
        "3": "百分比攻击力,百分比防御力,百分比生命值,元素精通,元素伤害加成,物理伤害加成".split(","),  # EQUIP_RING
        "4": "百分比攻击力,百分比防御力,百分比生命值,元素精通,治疗加成,暴击率,暴击伤害".split(","),  # EQUIP_DRESS
    }
    sub_affixs = "攻击力,百分比攻击力,防御力,百分比防御力,生命值,百分比生命值,元素精通,元素充能效率,暴击率,暴击伤害".split(
        ",")
    pointmark = {k: v / grow_value[k] for k, v in affix_weight.items()}
    if pointmark.get("百分比攻击力"):
        pointmark["攻击力"] = pointmark["百分比攻击力"] / (float(base_info["攻击力"]) + 520) * 100
        affix_weight["攻击力"] = pointmark["百分比攻击力"] * grow_value["攻击力"] / (
                float(base_info["攻击力"]) + 520) * 100
    if pointmark.get("百分比防御力"):
        pointmark["防御力"] = pointmark["百分比防御力"] / float(base_info["防御力"]) * 100
        affix_weight["防御力"] = pointmark["百分比防御力"] * grow_value["防御力"] / (
            float(base_info["防御力"])) * 100
    if pointmark.get("百分比生命值"):
        pointmark["生命值"] = pointmark["百分比生命值"] / float(base_info["生命值"]) * 100
        affix_weight["生命值"] = pointmark["百分比生命值"] * grow_value["生命值"] / (float(base_info["生命值"])) * 100
    affix_weight = dict(  # 排序影响最优主词条选择，通过特定排序使同等权重时非百分比的生命攻击防御词条优先级最低
        sorted(
            affix_weight.items(),
            key=lambda item: (
                item[1],
                "暴击" in item[0],
                "加成" in item[0],
                "元素" in item[0],
            ),
            reverse=True,
        )
    )
    # 各位置圣遗物的总分理论最高分、主词条理论最高得分
    max_mark = {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}}
    for posIdx in range(0, 5):
        if posIdx <= 1:
            # 花和羽不计算主词条得分
            main_affix = "生命值" if posIdx == 0 else "攻击力"
            max_mark[str(posIdx)]["main"] = 0
            max_mark[str(posIdx)]["total"] = 0
        else:
            # 沙杯头计算该位置评分权重最高的词条得分
            aval_main_affix = {
                k: v for k, v in affix_weight.items() if k in main_affixs[str(posIdx)]
            }
            main_affix = list(aval_main_affix)[0]
            max_mark[str(posIdx)]["main"] = affix_weight[main_affix]
            max_mark[str(posIdx)]["total"] = affix_weight[main_affix] * 2

        max_sub_affixs = {
            k: v
            for k, v in affix_weight.items()
            if k in sub_affixs and k != main_affix and affix_weight.get(k)
        }
        # 副词条中评分权重最高的词条得分大幅提升
        max_mark[str(posIdx)]["total"] += sum(
            affix_weight[k] * (1 if kIdx else 6)
            for kIdx, k in enumerate(list(max_sub_affixs)[0:4])
        )
    return affix_weight, pointmark, max_mark


def check(weight, affix, key, max_value=75, max_plus=75, is_weapon=True):
    original = weight.get(key, 0)

    if original < max_value:
        plus = max_plus * (1 + affix / 5) / 2 if is_weapon else max_plus
        weight[key] = min(round(original + plus), max_value)
        return True

    return False
def weapon_check(weight, affix, key, max_affix_attr=20, min_affix_attr=10, max_value=100):
    original = weight.get(key, 0)

    if original == max_value:
        return False
    else:
        plus = min_affix_attr + (max_affix_attr - min_affix_attr) * (affix - 1) / 4
        weight[key] = min(round(original + plus), max_value)
        return True


def get_effective(data):
    """
    根据角色的武器、圣遗物来判断获取该角色有效词条列表
    :param data: 角色信息
    :return: 有效词条列表
    """
    role_name = data['名称']
    artifacts = data['圣遗物']
    suffix = ''
    try:
        if role_name in ['荧', '空']:
            if data['元素'] == '火':
                role_name = '火主'
            elif data['元素'] == '水':
                role_name = '水主'
            elif data['元素'] == '冰':
                role_name = '冰主'
            elif data['元素'] == '雷':
                role_name = '雷主'
            elif data['元素'] == '风':
                role_name = '风主'
            elif data['元素'] == '岩':
                role_name = '岩主'
            elif data['元素'] == '草':
                role_name = '草主'

        weight = copy.deepcopy(role_ori.get(role_name))

        if role_name == '钟离':
            if data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 2.4:
                weight = { "hp": 80, "atk": 75, "cpct": 100, "cdmg": 100, "dmg": 100, "recharge": 30 }
                suffix += '战斗'
        elif role_name == '芭芭拉':
            if artifacts[3]['主属性']['属性名'] == '水元素伤害加成' and \
                    data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] >= 1.8:
                weight = { "hp": 50, "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 75, "dmg": 100, "recharge": 30, "heal": 50 }
                suffix += '暴力'
        elif role_name == '甘雨':
            suit = get_artifact_suit(artifacts)
            if '冰' in suit[0][0] and '冰' in suit[1][0]:
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "dmg": 100, "recharge": 55 }
                suffix += '永冻'
        elif role_name == '刻晴':
            if data['属性']['元素精通'] > 50:
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 75, "dmg": 100 }
                suffix += '精通'
        elif role_name == '神里绫人':
            if data['属性']['元素精通'] > 120:
                weight = { "hp": 45, "atk": 60, "cpct": 100, "cdmg": 100, "mastery": 60, "dmg": 100, "recharge": 30 }
                suffix += '精通'
        elif role_name == '温迪':
            if data['属性']['元素充能效率'] > 240:
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 75, "dmg": 100, "recharge": 100 }
                suffix += '充能'
        elif role_name == '宵宫':
            if data['属性']['元素精通'] < 50 and data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 3.2:
                weight = { "atk": 85, "cpct": 100, "cdmg": 100, "dmg": 100 }
                suffix += '纯火'
            if data['属性']['元素精通'] > 200 and artifacts[2]['主属性']['属性名'] == '元素精通':
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 100, "dmg": 100 }
                suffix += '精通'
        elif role_name == '行秋':
            if data['属性']['元素精通'] > 120:
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 75, "dmg": 100, "recharge": 75 }
                suffix += '蒸发'
        elif role_name == '云堇':
            if data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 1.8 \
                    and artifacts[3]['主属性']['属性名'] == '岩元素伤害加成' \
                    and artifacts[4]['主属性']['属性名'] in ['暴击率', '暴击伤害', '百分比防御力', '百分比攻击力']:
                weight = { "atk": 75, "def": 100, "cpct": 100, "cdmg": 100, "dmg": 100, "recharge": 75 }
                suffix += '输出'
        elif role_name == '雷电将军':
            if data['属性']['元素精通'] > 500:
                weight = { "atk": 75, "cpct": 90, "cdmg": 90, "mastery": 100, "dmg": 75, "recharge": 90 }
                suffix += '精通'
            elif data['武器']['名称'] == '薙草之稻光' and data["武器"]["精炼等级"] >= 3:
                weight = { "atk": 90, "cpct": 100, "cdmg": 100, "dmg": 90, "recharge": 90 }
                suffix += '高精'
        elif role_name == '胡桃':
            if data['属性']['暴击率'] < 0.15 and data['属性']['暴击伤害'] > 2.8:
                weight = { "hp": 90, "atk": 50, "cdmg": 100, "mastery": 90, "dmg": 100 }
                suffix += '核爆'
        elif role_name == '夜兰':
            if data['属性']['元素精通'] > 50:
                weight['mastery'] = 75
                suffix += '精通'
            if data['武器']['名称'] == '若水':
                weight['hp'] = 100
                suffix += '若水'
        elif role_name == '神里绫华':
            if data['属性']['元素精通'] > 120:
                weight = { "atk": 75, "cpct": 100, "cdmg": 100, "mastery": 75, "dmg": 100, "recharge": 45 }
                suffix += '精通'
        elif role_name == '可莉':
            if data['属性']['元素精通'] < 50 and data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 3.2:
                weight = { "atk": 85, "cpct": 100, "cdmg": 100, "dmg": 100, "recharge": 55 }
                suffix += '纯火'
        elif role_name == '优菈':
            if data['属性']['暴击率'] < 0.15 and data['属性']['暴击伤害'] > 2:
                weight = { "atk": 100, "cdmg": 100, "phy": 100 }
                suffix += '核爆'
        elif role_name == '迪希雅':
            if artifacts[2]['主属性']['属性名'] == '百分比生命值' \
                    and artifacts[3]['主属性']['属性名'] == '百分比生命值' \
                    and artifacts[4]['主属性']['属性名'] == '百分比生命值' \
                    and data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] < 1 \
                    and data['属性']['基础生命'] + data['属性']['额外生命'] > 40000:
                weight = { "hp": 100, "atk": 30, "cpct": 41, "cdmg": 41, "recharge": 30 }
                suffix += '血牛'
        elif role_name == '枫原万叶':
            if len(data['命座']) == 6:
                weight = { "hp": 0, "atk": 75, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 30, "dmg": 100, "phy": 0, "recharge": 55, "heal": 0 }
                suffix += '满命'
        elif role_name == '妮露':
            if len(data['命座']) == 6:
                weight = { "hp": 100, "atk": 0, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 80, "dmg": 100, "phy": 0, "recharge": 30, "heal": 0 }
                suffix += '满命'
        elif role_name == '闲云':
            if len(data['命座']) == 6:
                weight = { "hp": 0, "atk": 100, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 0, "dmg": 100, "phy": 0, "recharge": 35, "heal": 75 }
                suffix += '满命'
        elif role_name == '芙宁娜':
            if len(data['命座']) == 6:
                weight =  { "hp": 100, "atk": 0, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 45, "dmg": 100, "phy": 0, "recharge": 75, "heal": 95 }
                suffix += '满命'
        elif role_name == '白术':
            if len(data['命座']) == 6:
                weight = { "hp": 100, "atk": 75, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 50, "dmg": 100, "phy": 0, "recharge": 35, "heal": 100 }
                suffix += '满命'
        elif role_name == '那维莱特' and data['武器']['名称'] == '万世流涌大典':
            weight = { "hp": 100, "atk": 0, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 0, "dmg": 100, "phy": 0, "recharge": 40, "heal": 0 }
            suffix += '专武'
        elif role_name == '希格雯':
            if len(data['命座']) == 6:
                weight = { "hp": 100, "atk": 0, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 0, "dmg": 100, "phy": 0, "recharge": 75, "heal": 90 }
                suffix += '满命'
        elif role_name == '希诺宁':
            if data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 2.4:
                weight = { "hp": 0, "atk": 0, "def": 100, "cpct": 100, "cdmg": 100, "mastery": 0, "dmg": 80, "phy": 0, "recharge": 55, "heal": 70 }
                suffix += '战斗'
        elif role_name == '茜特菈莉':
            if data['属性']['暴击率'] * 2 + data['属性']['暴击伤害'] > 2.0:
                weight = { "hp": 0, "atk": 50, "def": 0, "cpct": 100, "cdmg": 100, "mastery": 100, "dmg": 80, "phy": 0, "recharge": 75, "heal": 0 }
                suffix += '战斗'
            if len(data['命座']) == 4:
                weight['recharge'] = 75
                suffix += '4命'
        elif role_name == '基尼奇':
            if len(data['命座']) == 4:
                weight['recharge'] = 35
                suffix += '4命'
        elif role_name == '玛拉妮':
            if len(data['命座']) == 4:
                weight['recharge'] = 30
                suffix += '4命'
        # weight = copy.deepcopy(role_score.get(role_name))
        role_score = {}
        for info in weight.keys():
            if weight.get(info) != 0:
                role_score[convert.get(info)] = weight.get(info)
        weight = role_score
        if suffix:
            return weight, f'{role_name}-{suffix}'
        if weight.get('百分比攻击力',0) > 0 and (weapon_weight:=weapon_cfg.get(data['武器']['名称'],'')):
            if weapon_check(weight, data['武器']['精炼等级'], weapon_weight.get('attr'), weapon_weight.get('max', 20), weapon_weight.get('min', 10)):
                suffix += f'{weapon_weight.get("abbr","")}'
        if '西风' in data['武器']['名称'] and weight.get('暴击率',0) != 100:
            weight['暴击率'] = 100
            suffix += '西风'
        max_weight = max(weight.get('百分比攻击力', 0), weight.get('百分比生命值', 0), weight.get('百分比防御力', 0), weight.get('元素精通', 0))
        suit = get_artifact_suit(artifacts)
        if len(suit) == 2:
            if suit[0][0] == suit[1][0] and suit[0][0] == '绝缘之旗印' and check(weight, data['武器']['精炼等级'],'元素充能效率', max_weight, 75, False):
                suffix += '绝缘4'
        return weight, f'{role_name}-{suffix}' if suffix else role_name
    except:
        return {'百分比攻击力': 75, '暴击率': 100, '暴击伤害': 100}, role_name


def check_effective(prop_name: str, effective: dict):
    """
    检查词条是否有效
    :param prop_name: 词条属性名
    :param effective: 有效词条列表
    :return: 是否有效
    """
    if ('攻击力' in effective or '百分比攻击力' in effective) and '攻击力' in prop_name:
        return True
    if ('生命值' in effective or '百分比生命值' in effective) and '生命值' in prop_name:
        return True
    if ('防御力' in effective or '百分比防御力' in effective) and '防御力' in prop_name:
        return True
    return prop_name in effective


def get_artifact_suit(artifacts: list):
    """
    获取圣遗物套装
    :param artifacts: 圣遗物列表
    :return: 套装列表
    """
    suit = []
    suit2 = []
    final_suit = []
    for artifact in artifacts:
        suit.append(artifact['所属套装'])
    for s in suit:
        if s not in suit2 and 1 < suit.count(s) < 4:
            suit2.append(s)
        if suit.count(s) >= 4:
            for r in artifacts:
                if r['所属套装'] == s:
                    return [(s, r['图标']), (s, r['图标'])]
    for r in artifacts:
        if r['所属套装'] in suit2:
            final_suit.append((r['所属套装'], r['图标']))
            suit2.remove(r['所属套装'])
    return final_suit
