from ..utils.card_utils import role_score


def artifact_value(role_prop: dict, prop_name: str, prop_value: float,
                   effective: dict):
    """
    计算圣遗物单词条的有效词条数
    :param role_prop: 角色基础属性
    :param prop_name: 属性名
    :param prop_value: 属性值
    :param effective: 有效词条列表
    :return: 评分
    """
    prop_map = {
        '攻击力': 4.975,
        '生命值': 4.975,
        '防御力': 6.2,
        '暴击率': 3.3,
        '暴击伤害': 6.6,
        '元素精通': 19.75,
        '元素充能效率': 5.5
    }
    if prop_name in effective.keys() and prop_name in ['攻击力', '生命值', '防御力']:
        return round(
            prop_value / role_prop[prop_name] * 100 / prop_map[prop_name] *
            effective[prop_name], 2)
    if prop_name.replace('百分比', '') in effective.keys():
        return round(
            prop_value / prop_map[prop_name.replace('百分比', '')] *
            effective[prop_name.replace('百分比', '')], 2)
    return 0


def artifact_total_value(role_prop: dict, artifact: dict, effective: dict):
    """
    计算圣遗物总有效词条数以及评分
    :param role_prop: 角色基础属性
    :param artifact: 圣遗物信息
    :param effective: 有效词条列表
    :return: 总词条数，评分
    """
    new_role_prop = {
        '攻击力': role_prop['基础攻击'],
        '生命值': role_prop['基础生命'],
        '防御力': role_prop['基础防御']
    }
    value = 0
    for i in artifact['词条']:
        value += artifact_value(new_role_prop, i['属性名'], i['属性值'], effective)
    value = round(value, 2)
    return value, round(value / get_expect_score(effective) * 100, 1)


def get_effective(role_name: str,
                  role_weapon: str,
                  artifacts: list,
                  element: str = '风'):
    """
    根据角色的武器、圣遗物来判断获取该角色有效词条列表
    :param role_name: 角色名
    :param role_weapon: 角色武器
    :param artifacts: 角色圣遗物列表
    :param element: 角色元素，仅需主角传入
    :return: 有效词条列表
    """
    if role_name in ['荧', '空']:
        role_name = str(element) + '主'
    if role_name in role_score['Weight']:
        if len(artifacts) < 5:
            return role_score['Weight'][role_name]['常规']
        if role_name == '钟离':
            if artifacts[-2]['主属性']['属性名'] == '岩元素伤害加成':
                return role_score['Weight'][role_name]['岩伤']
            elif artifacts[-2]['主属性']['属性名'] in [
                '物理伤害加成', '火元素伤害加成', '冰元素伤害加成'
            ]:
                return role_score['Weight'][role_name]['武神']
        if role_name == '班尼特' and artifacts[-2]['主属性']['属性名'] == '火元素伤害加成':
            return role_score['Weight'][role_name]['输出']
        if role_name == '甘雨':
            suit = get_artifact_suit(artifacts)
            if suit and ('乐团' in suit[0][0] or
                         (len(suit) == 2 and '乐团' in suit[1][0])):
                return role_score['Weight'][role_name]['融化']
        if role_name == '申鹤' and artifacts[-2]['主属性']['属性名'] == '冰元素伤害加成':
            return role_score['Weight'][role_name]['输出']
        if role_name == '七七' and artifacts[-2]['主属性']['属性名'] == '物理伤害加成':
            return role_score['Weight'][role_name]['输出']
        if role_name in ['温迪', '砂糖'
                         ] and artifacts[-2]['主属性']['属性名'] == '风元素伤害加成':
            return role_score['Weight'][role_name]['输出']
        if '西风' in role_weapon and '西风' in role_score['Weight'][role_name]:
            return role_score['Weight'][role_name]['西风']
        return role_score['Weight'][role_name]['常规']
    else:
        return {'攻击力': 1, '暴击率': 1, '暴击伤害': 1}


def get_expect_score(effective: dict):
    """
    计算单个圣遗物小毕业所需的期望词条数
    :param effective: 有效词条列表
    :return: 期望词条数
    """
    total = 0
    if len(effective.keys()) == 2:
        average = 15 / 5
    elif effective.keys() == '西风':
        average = 17 / 5
    elif len(effective.keys()) == 3:
        average = 24 / 5
    elif len(effective.keys()) == 4:
        average = 28 / 5
    else:
        average = 30 / 5
    for name, value in effective.items():
        total += value * average
    return round(total / len(effective.keys()), 2)


def check_effective(prop_name: str, effective: dict):
    """
    检查词条是否有效
    :param prop_name: 词条属性名
    :param effective: 有效词条列表
    :return: 是否有效
    """
    if '攻击力' in effective and '攻击力' in prop_name:
        return True
    if '生命值' in effective and '生命值' in prop_name:
        return True
    if '防御力' in effective and '防御力' in prop_name:
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
