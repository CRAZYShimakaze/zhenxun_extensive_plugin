import datetime
import os
import re

from PIL import ImageFont

from ..utils.json_utils import load_json, save_json

GENSHIN_CARD_PATH = os.path.join(os.path.dirname(__file__), "..")
player_info_path = GENSHIN_CARD_PATH + '/player_info'
group_info_path = GENSHIN_CARD_PATH + '/group_info'
res_path = GENSHIN_CARD_PATH + '/res/'
json_path = res_path + 'json_data'
bg_path = res_path + 'background'
char_pic_path = res_path + 'character'
other_path = res_path + 'other'
regoin_path = res_path + 'region'
outline_path = res_path + 'outline'
skill_path = res_path + 'skill'
talent_path = res_path + 'talent'
weapon_path = res_path + 'weapon'
reli_path = res_path + 'reli'
font_path = res_path + 'fonts'
role_data = load_json(path=f'{json_path}/role_data.json')
role_skill = load_json(path=f'{json_path}/role_skill.json')
role_talent = load_json(path=f'{json_path}/role_talent.json')
weapon = load_json(path=f'{json_path}/weapon.json')
prop_list = load_json(path=f'{json_path}/prop.json')
artifact_list = load_json(path=f'{json_path}/artifact.json')
role_score = load_json(path=f'{json_path}/score.json')
alias_file = load_json(path=f'{json_path}/alias.json')


class PlayerInfo:

    def __init__(self, uid: int):
        self.path = f'{player_info_path}/{uid}.json'
        self.data = load_json(path=self.path)
        self.player_info = self.data['玩家信息'] if '玩家信息' in self.data else {}
        self.roles = self.data['角色'] if '角色' in self.data else {}

    def set_player(self, data: dict):
        self.player_info['昵称'] = data.get('nickname', 'unknown')
        self.player_info['等级'] = data.get('level', 'unknown')
        self.player_info['世界等级'] = data.get('worldLevel', 'unknown')
        self.player_info['签名'] = data.get('signature', 'unknown')
        self.player_info['成就'] = data.get('finishAchievementNum', 'unknown')
        self.player_info['角色列表'] = dictlist_to_list(
            data.get('showAvatarInfoList'))
        self.player_info['名片列表'] = data.get('showNameCardIdList', 'unknown')
        self.player_info['头像'] = data['profilePicture']['avatarId']
        self.player_info['更新时间'] = datetime.datetime.strftime(
            datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')

    def set_role(self, data: dict):
        role_info = {}
        role_name = get_name_by_id(str(data['avatarId']))
        if role_name not in ['unknown', 'None']:
            role_info['名称'] = role_name
            role_info['角色ID'] = data['avatarId']
            role_info['等级'] = int(data['propMap']['4001']['val'])
            role_info['好感度'] = data['fetterInfo']['expLevel']
            if role_name in ['荧', '空']:
                traveler_skill = role_skill['Name'][list(
                    data['skillLevelMap'].keys())[-1]]
                find_element = re.search(r'([风雷岩草水火冰])',
                                         traveler_skill).group(1)
                role_info['元素'] = find_element
                role_name = find_element + '主'
            else:
                role_info['元素'] = role_data[role_name]["element"]

            if 'talentIdList' in data:
                if len(data['talentIdList']) >= 3:
                    data['skillLevelMap'][list(data['skillLevelMap'].keys())[
                        role_skill['Talent'][role_name][0]]] += 3
                if len(data['talentIdList']) >= 5:
                    data['skillLevelMap'][list(data['skillLevelMap'].keys())[
                        role_skill['Talent'][role_name][1]]] += 3

            role_info['天赋'] = []
            for skill in data['skillLevelMap']:
                skill_detail = {
                    '名称': role_skill['Name'][skill],
                    '等级': data['skillLevelMap'][skill],
                    '图标': role_skill['Icon'][skill]
                }
                role_info['天赋'].append(skill_detail)
            if role_info['名称'] == '神里绫华':
                role_info['天赋'][0], role_info['天赋'][-1] = role_info['天赋'][
                                                                  -1], role_info['天赋'][0]
                role_info['天赋'][2], role_info['天赋'][-1] = role_info['天赋'][
                                                                  -1], role_info['天赋'][2]
            if role_info['名称'] == '安柏':
                role_info['天赋'][0], role_info['天赋'][-1] = role_info['天赋'][
                                                                  -1], role_info['天赋'][0]
            if role_info['名称'] in ['空', '荧']:
                role_info['天赋'][0], role_info['天赋'][-1] = role_info['天赋'][
                                                                  -1], role_info['天赋'][0]
                role_info['天赋'][1], role_info['天赋'][-1] = role_info['天赋'][
                                                                  -1], role_info['天赋'][1]
            if role_info['名称'] == '达达利亚':
                role_info['天赋'][0]['等级'] += 1

            role_info['命座'] = []
            if 'talentIdList' in data:
                for talent in data['talentIdList']:
                    talent_detail = {
                        '名称': role_talent['Name'][str(talent)],
                        '图标': role_talent['Icon'][str(talent)]
                    }
                    role_info['命座'].append(talent_detail)

            prop = {}
            prop['基础生命'] = round(data['fightPropMap']['1'])
            prop['额外生命'] = round(data['fightPropMap']['2000'] - prop['基础生命'])
            prop['基础攻击'] = round(data['fightPropMap']['4'])
            prop['额外攻击'] = round(data['fightPropMap']['2001'] - prop['基础攻击'])
            prop['基础防御'] = round(data['fightPropMap']['7'])
            prop['额外防御'] = round(data['fightPropMap']['2002'] - prop['基础防御'])
            prop['暴击率'] = round(data['fightPropMap']['20'], 3)
            prop['暴击伤害'] = round(data['fightPropMap']['22'], 3)
            prop['元素精通'] = round(data['fightPropMap']['28'])
            prop['元素充能效率'] = round(data['fightPropMap']['23'], 3)
            prop['治疗加成'] = round(data['fightPropMap']['26'], 3)
            prop['受治疗加成'] = round(data['fightPropMap']['27'], 3)
            prop['伤害加成'] = [round(data['fightPropMap']['30'], 3)]
            for i in range(40, 47):
                prop['伤害加成'].append(round(data['fightPropMap'][str(i)], 3))
            role_info['属性'] = prop

            weapon_info = {}
            weapon_data = data['equipList'][-1]
            weapon_info['名称'] = weapon['Name'][weapon_data['flat']
            ['nameTextMapHash']]
            weapon_info['图标'] = weapon_data['flat']['icon']
            weapon_info['类型'] = weapon['Type'][weapon_info['名称']]
            weapon_info['等级'] = weapon_data['weapon']['level']
            weapon_info['星级'] = weapon_data['flat']['rankLevel']
            if 'promoteLevel' in weapon_data['weapon']:
                weapon_info['突破等级'] = weapon_data['weapon']['promoteLevel']
            else:
                weapon_info['突破等级'] = 0
            if 'affixMap' in weapon_data['weapon']:
                weapon_info['精炼等级'] = list(
                    weapon_data['weapon']['affixMap'].values())[0] + 1
            else:
                weapon_info['精炼等级'] = 1
            weapon_info['基础攻击'] = weapon_data['flat']['weaponStats'][0][
                'statValue']
            try:
                weapon_info['副属性'] = {
                    '属性名':
                        prop_list[weapon_data['flat']['weaponStats'][1]
                        ['appendPropId']],
                    '属性值':
                        weapon_data['flat']['weaponStats'][1]['statValue']
                }
            except IndexError:
                weapon_info['副属性'] = {'属性名': '无属性', '属性值': 0}
            weapon_info['特效'] = '待补充'
            role_info['武器'] = weapon_info

            artifacts = []
            for artifact in data['equipList'][:-1]:
                artifact_info = {}
                artifact_info['名称'] = artifact_list['Name'][artifact['flat']
                ['icon']]
                artifact_info['图标'] = artifact['flat']['icon']
                artifact_info['部位'] = artifact_list['Piece'][
                    artifact['flat']['icon'].split('_')[-1]][1]
                artifact_info['所属套装'] = artifact_list['Mapping'][
                    artifact_info['名称']]
                artifact_info['等级'] = artifact['reliquary']['level'] - 1
                artifact_info['星级'] = artifact['flat']['rankLevel']
                artifact_info['主属性'] = {
                    '属性名':
                        prop_list[artifact['flat']['reliquaryMainstat']
                        ['mainPropId']],
                    '属性值':
                        artifact['flat']['reliquaryMainstat']['statValue']
                }
                artifact_info['词条'] = []
                for reliquary in artifact['flat'].get('reliquarySubstats', []):
                    artifact_info['词条'].append({
                        '属性名':
                            prop_list[reliquary['appendPropId']],
                        '属性值':
                            reliquary['statValue']
                    })
                artifacts.append(artifact_info)
            role_info['圣遗物'] = artifacts
            role_info['更新时间'] = datetime.datetime.strftime(
                datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
            self.roles[role_info['名称']] = role_info

    def get_player_info(self):
        return self.player_info

    def get_update_roles_list(self):
        return self.player_info['角色列表']

    def get_roles_list(self):
        return list(self.roles.keys())

    def get_roles_info(self, role_name):
        if role_name in self.roles:
            return self.roles[role_name]
        else:
            return None

    def save(self):
        self.data['玩家信息'] = self.player_info
        self.data['角色'] = self.roles
        save_json(data=self.data, path=self.path)


def get_name_by_id(role_id: str):
    """
        根据角色id获取角色名
        :param role_id: 角色id
        :return: 角色名字符串
    """
    name_list = alias_file['roles']
    if role_id in name_list:
        return name_list[role_id][0]
    else:
        return None


def dictlist_to_list(data):
    if not isinstance(data, list):
        return 'unknown'
    new_data = {}
    for d in data:
        name = get_name_by_id(str(d['avatarId']))
        new_data[name] = d['avatarId']
    return new_data


def get_font(size, font='hywh.ttf'):
    return ImageFont.truetype(str(res_path + 'fonts/' + font), size)
