import copy

from .draw_artifact_card import draw_artifact_card
from ..utils.artifact_utils import get_effective, check_effective, get_miao_score, get_artifact_score
from ..utils.card_utils import json_path, role_score
from ..utils.json_utils import load_json

avatar_url = 'https://enka.network/ui/{}.png'
qq_logo_url = 'http://q1.qlogo.cn/g?b=qq&nk={}&s=640'
role_name = load_json(f'{json_path}/roles_name.json')
role_data = load_json(f'{json_path}/roles_data.json')
alias_file = load_json(f'{json_path}/alias.json')
name_list = alias_file['roles']


def sort_recommend(artifact, position):
    artifact_recommend = []
    for role_name_full, effective in role_score.items():
        role_name = role_name_full.split('-')[0]
        affix_weight, point_mark, max_mark = get_miao_score(effective, role_data[role_name]['attribute'])
        artifact_score, grade, mark = get_artifact_score(point_mark, max_mark, artifact,
                                                         role_data[role_name]["element"], position)

        artifact_pk_info = {'角色': role_name}
        artifact_pk_info['星级'] = artifact["星级"]
        artifact_pk_info['图标'] = artifact["图标"]
        artifact_pk_info['名称'] = role_name_full
        artifact_pk_info['评分'] = grade
        artifact_pk_info['评级'] = artifact_score
        artifact_pk_info['等级'] = artifact['等级']
        artifact_pk_info['主属性'] = {'属性名': artifact['主属性']['属性名'], '属性值': artifact['主属性']['属性值']}
        artifact_pk_info['副属性'] = []
        for j in range(len(artifact['词条'])):
            text = artifact['词条'][j]['属性名'].replace('百分比', '')
            up_num = ''
            if mark[j] != 0:
                up_num = '¹' if mark[j] == 1 else '²' if mark[j] == 2 else '³' if mark[j] == 3 else '⁴' if mark[
                                                                                                               j] == 4 else '⁵'
            if artifact['词条'][j]['属性名'] not in ['攻击力', '防御力', '生命值', '元素精通']:
                num = '+' + str(artifact['词条'][j]['属性值']) + '%'
            else:
                num = '+' + str(artifact['词条'][j]['属性值'])
            artifact_pk_info['副属性'].append({'属性名': text, '属性值': num, '强化次数': up_num,
                                               '颜色': 'white' if check_effective(artifact['词条'][j]['属性名'],
                                                                                  effective) else '#afafaf'})
        artifact_recommend.append(copy.deepcopy(artifact_pk_info))
        if len(artifact_recommend) > 20:
            artifact_recommend = sorted(artifact_recommend, key=lambda x: float(x['评分']),
                                        reverse=True)[:20]
    return artifact_recommend


async def gen_artifact_adapt(title, artifact, uid, role, pos, plugin_version):
    artifact_info = sort_recommend(artifact, pos)
    return await draw_artifact_card(title, role, uid, artifact_info, ace2_num=0, ace_num=0, plugin_version=plugin_version)


async def gen_artifact_recommend(title, data, artifact_list, uid, role_name, pos, plugin_version):
    artifact_all = []

    ori_artifact = data['圣遗物'][pos]
    for artifact in artifact_list:
        artifact_pk_info = {}
        if ori_artifact == artifact:
            artifact_pk_info['角色'] = role_name
        elif "角色" in artifact:
            #pass
            artifact_pk_info['角色'] = artifact["角色"]
        data['圣遗物'][pos] = artifact
        effective, _ = get_effective(data)
        affix_weight, point_mark, max_mark = get_miao_score(effective, role_data[role_name]['attribute'])
        artifact_score, grade, mark = get_artifact_score(point_mark, max_mark, artifact,
                                                         role_data[role_name]["element"], pos)
        artifact_pk_info['星级'] = artifact["星级"]
        artifact_pk_info['图标'] = artifact["图标"]
        artifact_pk_info['名称'] = artifact['名称']
        artifact_pk_info['评分'] = grade
        artifact_pk_info['评级'] = artifact_score
        artifact_pk_info['等级'] = artifact['等级']
        artifact_pk_info['主属性'] = {'属性名': artifact['主属性']['属性名'], '属性值': artifact['主属性']['属性值']}
        artifact_pk_info['副属性'] = []
        for j in range(len(artifact['词条'])):
            text = artifact['词条'][j]['属性名'].replace('百分比', '')
            up_num = ''
            if mark[j] != 0:
                up_num = '¹' if mark[j] == 1 else '²' if mark[j] == 2 else '³' if mark[j] == 3 else '⁴' if mark[j] == 4 else '⁵'
            if artifact['词条'][j]['属性名'] not in ['攻击力', '防御力', '生命值', '元素精通']:
                num = '+' + str(artifact['词条'][j]['属性值']) + '%'
            else:
                num = '+' + str(artifact['词条'][j]['属性值'])
            artifact_pk_info['副属性'].append({'属性名': text, '属性值': num, '强化次数': up_num, '颜色': 'white' if check_effective(artifact['词条'][j]['属性名'], effective) else '#afafaf'})
        if artifact_pk_info not in artifact_all:
            artifact_all.append(copy.deepcopy(artifact_pk_info))
        artifact_all = sorted(artifact_all, key=lambda x: float(x['评分']),
                              reverse=True)[:16 if len(artifact_all) > 16 else len(artifact_all)]
    return await draw_artifact_card(title, role_name, uid, artifact_all, ace2_num=0, ace_num=0,
                                    plugin_version=plugin_version)
