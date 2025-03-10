import datetime
import os

from PIL import ImageFont

from ..utils.json_utils import load_json, save_json

STARRAIL_CARD_PATH = os.path.join(os.path.dirname(__file__), "..")

STARRAIL_DATA_PATH = STARRAIL_CARD_PATH + '/user_data'
player_info_path = STARRAIL_DATA_PATH + '/player_info'
group_info_path = STARRAIL_DATA_PATH + '/group_info'
card_res_path = STARRAIL_CARD_PATH + '/res/'
data_res_path = STARRAIL_DATA_PATH + '/res/'
qq_logo_path = STARRAIL_DATA_PATH + '/qq_logo/'
json_path = card_res_path + 'json_data'
bg_path = card_res_path + 'background'
char_pic_path = data_res_path + 'character'
avatar_path = data_res_path + 'avatar'
other_path = card_res_path + 'other'
outline_path = card_res_path + 'outline'
path_path = data_res_path + 'path'
skill_path = data_res_path + 'skill'
talent_path = data_res_path + 'talent'
weapon_path = data_res_path + 'weapon'
reli_path = data_res_path + 'reli'
font_path = card_res_path + 'fonts'
role_skill = load_json(path=f'{json_path}/character_skill_trees.json')
weapon = load_json(path=f'{json_path}/light_cones.json')
weapon_val = load_json(path=f'{json_path}/light_cone_promotions.json')
weapon_prop = load_json(path=f'{json_path}/light_cone_ranks.json')
role_value = load_json(path=f'{json_path}/character_promotions.json')
relic = load_json(path=f'{json_path}/relics.json')
relic_main_value = load_json(path=f'{json_path}/relic_main_affixes.json')
relic_sub_value = load_json(path=f'{json_path}/relic_sub_affixes.json')
relic_sets = load_json(path=f'{json_path}/relic_sets.json')
role_score = load_json(path=f'{json_path}/score.json')
role_data = load_json(path=f'{json_path}/characters.json')
paths = load_json(path=f'{json_path}/paths.json')
trans_data = load_json(path=f'{json_path}/property_trans.json')


class PlayerInfo:

    def __init__(self, uid: int):
        self.path = f'{player_info_path}/{uid}.json'
        self.data = load_json(path=self.path)
        self.player_info = self.data['玩家信息'] if '玩家信息' in self.data else {}
        self.roles = self.data['角色'] if '角色' in self.data else {}
        if '遗器榜单' not in self.data:
            self.data['遗器榜单'] = []
        if '小毕业遗器' not in self.data:
            self.data['小毕业遗器'] = 0
        if '大毕业遗器' not in self.data:
            self.data['大毕业遗器'] = 0
        if '遗器列表' not in self.data:
            self.data['遗器列表'] = [[], [], [], [], [], []]

    def set_player(self, data: dict):
        self.player_info['昵称'] = data.get('nickname', 'unknown')
        self.player_info['等级'] = data.get('level', 'unknown')
        self.player_info['世界等级'] = data.get('worldLevel', 'unknown')
        self.player_info['签名'] = data.get('signature', 'unknown')
        self.player_info['角色列表'] = dictlist_to_list(
            data.get('avatarDetailList'))
        self.player_info['更新时间'] = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')

    def set_role(self, data: dict):
        role_info = {}
        role_name = get_name_by_id(str(data['avatarId']))

        role_info['角色ID'] = str(data['avatarId'])
        role_info['等级'] = data['level']
        role_info['晋升'] = data.get('promotion', 0)
        role_info['元素'] = role_data[role_info['角色ID']]["element"]
        role_info['名称'] = role_name
        role_info['命途'] = role_data[role_info['角色ID']]["path"]

        role_info['星魂'] = []
        for i in range(data.get('rank', 0)):
            talent_detail = {
                '图标': f"{role_info['角色ID']}_skill" if i == 2 else f"{role_info['角色ID']}_technique" if i == 4 else f"{role_info['角色ID']}_rank{i + 1}"
            }
            role_info['星魂'].append(talent_detail)
        if data.get('rank', 0) >= 3:
            data.get('skillTreeList')[0]['level'] += 1
            data.get('skillTreeList')[1]['level'] += 2
        if data.get('rank', 0) >= 5:
            data.get('skillTreeList')[2]['level'] += 2
            data.get('skillTreeList')[3]['level'] += 2

        prop = {}
        prop['基础生命值'] = self.get_role_value('hp', role_info['角色ID'], role_info['晋升'], role_info['等级'])
        prop['基础攻击力'] = self.get_role_value('atk', role_info['角色ID'], role_info['晋升'], role_info['等级'])
        prop['基础防御力'] = self.get_role_value('def', role_info['角色ID'], role_info['晋升'], role_info['等级'])
        prop['基础暴击率'] = self.get_role_value('crit_rate', role_info['角色ID'], role_info['晋升'], role_info['等级'])
        prop['基础暴击伤害'] = self.get_role_value('crit_dmg', role_info['角色ID'], role_info['晋升'], role_info['等级'])
        prop['基础速度'] = self.get_role_value('spd', role_info['角色ID'], role_info['晋升'], role_info['等级'])

        prop['额外生命值'] = 0
        prop['额外攻击力'] = 0
        prop['额外防御力'] = 0
        prop['暴击率'] = 0
        prop['暴击伤害'] = 0
        prop['额外速度'] = 0
        prop['治疗加成'] = 0
        prop['效果命中'] = 0
        prop['效果抵抗'] = 0
        prop['伤害加成'] = 0
        # prop['物理伤害加成'] = 0
        # prop['火元素伤害加成'] = 0
        # prop['冰元素伤害加成'] = 0
        # prop['雷元素伤害加成'] = 0
        # prop['风元素伤害加成'] = 0
        # prop['量子伤害加成'] = 0
        # prop['虚数伤害加成'] = 0
        prop['击破特攻'] = 0
        prop['能量恢复效率'] = 0

        prop['最大生命值'] = self.get_role_value('hp', role_info['角色ID'], 6, 80)
        prop['最大攻击力'] = self.get_role_value('atk', role_info['角色ID'], 6, 80)
        prop['最大防御力'] = self.get_role_value('def', role_info['角色ID'], 6, 80)

        weapon_info = {}
        weapon_prop_info = {'属性名': '能量恢复效率', '属性值': 0}
        if data.get('equipment', ''):
            weapon_data = data['equipment']
            weapon_data['tid'] = str(weapon_data['tid'])
            weapon_info['名称'] = weapon[weapon_data['tid']]['name']
            weapon_info['图标'] = weapon_data['tid']
            weapon_info['类型'] = weapon[weapon_data['tid']]['path']
            weapon_info['等级'] = weapon_data['level']
            weapon_info['星级'] = weapon[weapon_data['tid']]['rarity']
            weapon_info['突破等级'] = weapon_data.get('promotion', 0)
            weapon_info['精炼等级'] = weapon_data.get('rank')
            weapon_info['生命值'] = self.get_weapon_value('hp', weapon_data['tid'], weapon_info['突破等级'], weapon_info['等级'])
            weapon_info['攻击力'] = self.get_weapon_value('atk', weapon_data['tid'], weapon_info['突破等级'], weapon_info['等级'])
            weapon_info['防御力'] = self.get_weapon_value('def', weapon_data['tid'], weapon_info['突破等级'], weapon_info['等级'])

            if weapon_prop[weapon_data['tid']]['properties'][weapon_info['精炼等级'] - 1]:
                weapon_prop_info = weapon_prop[weapon_data['tid']]['properties'][weapon_info['精炼等级'] - 1]
                if weapon_prop_info[0]['type'] != 'AllDamageTypeAddedRatio':
                    weapon_prop_info = {'属性名': trans_data['property'][weapon_prop_info[0]['type']],
                                        '属性值': weapon_prop_info[0]['value']}
                else:
                    weapon_prop_info = {'属性名': '能量恢复效率', '属性值': 0}
            prop['额外生命值'] += weapon_info['生命值']
            prop['额外攻击力'] += weapon_info['攻击力']
            prop['额外防御力'] += weapon_info['防御力']

        role_info['光锥'] = weapon_info

        role_info['行迹'] = [
            {
                '名称': '普攻',
                '等级': data.get('skillTreeList')[0]['level'],
                '图标': f"{role_info['角色ID']}_basic_atk"
            },
            {
                '名称': '战技',
                '等级': data.get('skillTreeList')[1]['level'],
                '图标': f"{role_info['角色ID']}_skill"
            },
            {
                '名称': '终结技',
                '等级': data.get('skillTreeList')[2]['level'],
                '图标': f"{role_info['角色ID']}_ultimate"
            },
            {
                '名称': '天赋',
                '等级': data.get('skillTreeList')[3]['level'],
                '图标': f"{role_info['角色ID']}_talent"
            }
        ]
        skill_prop_list = [{'属性名': '能量恢复效率', '属性值': 0}]
        for item in data.get('skillTreeList'):
            if skill_prop := role_skill.get(str(item['pointId']))['levels'][0]['properties']:
                skill_prop = {'属性名': trans_data['property'][skill_prop[0]['type']],
                              '属性值': skill_prop[0]['value']}
                skill_prop_list.append(skill_prop)

        artifacts = []
        if data.get('relicList', ''):
            relic_list = data['relicList']
            for relic_info in relic_list:
                artifact_info = {}
                relic_info['tid'] = str(relic_info['tid'])
                relic_item = relic[relic_info['tid']]
                artifact_info['ID'] = relic_info['tid']
                artifact_info['名称'] = relic_item['name']
                artifact_info['图标'] = relic_item['icon'].split('/')[-1].strip('.png')
                artifact_info['部位'] = relic_item['type']
                artifact_info['所属套装'] = relic_item['set_id']
                artifact_info['等级'] = relic_info.get('level', 0)
                artifact_info['星级'] = relic_item['rarity']
                artifact_info['主属性'] = {
                    '属性名': trans_data['property'][relic_main_value[relic_item['main_affix_id']]['affixes'][str(relic_info['mainAffixId'])]['property']],
                    '属性值': self.get_main_relic_value(relic_main_value[relic_item['main_affix_id']]['id'], relic_info['mainAffixId'], artifact_info['等级'])
                }
                artifact_info['词条'] = []
                for sub_info in relic_info.get('subAffixList', []):
                    artifact_info['词条'].append({
                        '属性名': trans_data['property'][relic_sub_value[relic_item['sub_affix_id']]['affixes'][str(sub_info['affixId'])]['property']],
                        '属性值': self.get_sub_relic_value(relic_sub_value[relic_item['sub_affix_id']]['id'], sub_info['affixId'], sub_info.get('cnt', 0), sub_info.get('step', 0))
                    })
                artifacts.append(artifact_info)
                self.cal_prop(prop, artifact_info['主属性'], artifact_info['词条'])
        suit_4, suit_2 = get_artifact_suit([item['所属套装'] for item in artifacts])
        relic_suit_prop = [{'属性名': '能量恢复效率', '属性值': 0}]
        if suit_4:
            for suit in suit_4:
                relic_prop = relic_sets[suit]['properties']
                for item in relic_prop:
                    if item:
                        for i in item:
                            if i:
                                relic_suit_prop.append({'属性名': trans_data['property'][i['type']],
                                                        '属性值': i['value']})
        if suit_2:
            for suit in suit_2:
                relic_prop = relic_sets[suit]['properties']
                for item in relic_prop:
                    if item:
                        relic_suit_prop.append({'属性名': trans_data['property'][item[0]['type']],
                                                '属性值': item[0]['value']})

        self.cal_prop(prop, {'属性名': '能量恢复效率', '属性值': 0}, skill_prop_list + [weapon_prop_info] + relic_suit_prop)
        role_info['遗器'] = artifacts
        role_info['属性'] = prop
        role_info['更新时间'] = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.roles[role_info['名称']] = role_info

    def cal_prop(self, prop, main, sub):
        if '百分比' in main['属性名']:
            prop[f"额外{main['属性名'].replace('百分比', '')}"] += prop[f"基础{main['属性名'].replace('百分比', '')}"] * main['属性值']
        elif main['属性名'] in ['生命值', '攻击力', '防御力', '速度']:
            prop[f"额外{main['属性名']}"] += main['属性值']
        elif '伤害加成' in main['属性名']:
            prop['伤害加成'] += main['属性值']
        else:
            prop[main['属性名']] += main['属性值']
        for item in sub:
            if '百分比' in item['属性名']:
                prop[f"额外{item['属性名'].replace('百分比', '')}"] += prop[f"基础{item['属性名'].replace('百分比', '')}"] * item['属性值']
            elif item['属性名'] in ['生命值', '攻击力', '防御力', '速度']:
                prop[f"额外{item['属性名']}"] += item['属性值']
            elif '伤害加成' in item['属性名']:
                prop['伤害加成'] += item['属性值']
            else:
                prop[item['属性名']] += item['属性值']

    def get_role_value(self, item, id, prop, level):
        if prop == 0:
            val = role_value[id]['values'][prop][item]['base'] + \
                  role_value[id]['values'][prop][item]['step'] * (level - 1)
        else:
            val = role_value[id]['values'][prop][item]['base'] + \
                  role_value[id]['values'][prop][item]['step'] * (level - 1)
        return val

    def get_weapon_value(self, item, id, prop, level):
        if prop == 0:
            val = weapon_val[id]['values'][prop][item]['base'] + \
                  weapon_val[id]['values'][prop][item]['step'] * (level - 1)
        else:
            val = weapon_val[id]['values'][prop][item]['base'] + \
                  weapon_val[id]['values'][prop][item]['step'] * (level - 1)
        return val

    def get_main_relic_value(self, id, affixes_id, level):
        val = relic_main_value[id]['affixes'][str(affixes_id)]['base'] + \
              relic_main_value[id]['affixes'][str(affixes_id)]['step'] * level  # ((level if level else 1) - 1)
        return val

    def get_sub_relic_value(self, id, affixes_id, level, step_num):
        val = relic_sub_value[id]['affixes'][str(affixes_id)]['base'] * level + \
              relic_sub_value[id]['affixes'][str(affixes_id)]['step'] * step_num
        return val

    def get_player_info(self):
        return self.player_info

    def get_update_roles_list(self):
        return self.player_info['角色列表']

    def get_roles_list(self):
        return list(self.roles.keys())

    def get_artifact_list(self, pos):
        return list(self.data['遗器列表'][pos])

    def get_roles_info(self, role_name):
        if role_name in self.roles:
            return self.roles[role_name]
        else:
            return None

    def save(self):
        self.data['玩家信息'] = self.player_info
        self.data['角色'] = self.roles
        save_json(data=self.data, path=self.path)


def get_artifact_suit(artifacts: list):
    """
    获取遗器套装
    :param artifacts: 遗器列表
    :return: 套装列表
    """

    artifacts_type = set(artifacts)
    suit_2 = []
    suit_4 = []
    for item in artifacts_type:
        if artifacts.count(item) >= 4:
            suit_4.append(item)
        elif artifacts.count(item) >= 2:
            suit_2.append(item)
    return suit_4, suit_2


def get_name_by_id(role_id: str):
    """
        根据角色id获取角色名
        :param role_id: 角色id
        :return: 角色名字符串
    """
    return role_data.get(role_id, '').get('name')


def dictlist_to_list(data):
    if not isinstance(data, list):
        return 'unknown'
    new_data = {}
    for d in data:
        name = get_name_by_id(str(d['avatarId']))
        new_data[name] = str(d['avatarId'])
    return new_data


def get_font(size, font='hywh.ttf'):
    return ImageFont.truetype(str(font_path + '/' + font), size)
