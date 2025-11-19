import copy

from ..utils.artifact_utils import check_effective#, get_artifact_score, get_effective
from .draw_artifact_card import draw_artifact_card


async def gen_artifact_recommend(title, data, artifact_list, uid, role_name, pos, plugin_version):
    artifact_all = []
    artifact_pk_info = {"角色": role_name}
    for artifact in artifact_list:
        data["遗器"][pos] = artifact
        #effective, _ = get_effective(data)
        effective = {"生命值"}
        #artifact_score, grade, mark = get_artifact_score(effective, artifact, data, pos)
        artifact_score = grade = mark = 0

        artifact_pk_info["星级"] = artifact["星级"]
        artifact_pk_info["图标"] = artifact["图标"]
        artifact_pk_info["名称"] = artifact["名称"]
        artifact_pk_info["评分"] = grade
        artifact_pk_info["评级"] = artifact_score
        artifact_pk_info["等级"] = artifact["等级"]
        artifact_pk_info["主属性"] = {"属性名": artifact["主属性"]["属性名"], "属性值": artifact["主属性"]["属性值"]}
        artifact_pk_info["副属性"] = []
        for j in range(len(artifact["词条"])):
            up_num = ""
            if mark[j] != 0:
                up_num = "¹" if mark[j] == 1 else "²" if mark[j] == 2 else "³" if mark[j] == 3 else "⁴" if mark[j] == 4 else "⁵"
            num = artifact["词条"][j]["属性值"]
            artifact_pk_info["副属性"].append({"属性名": artifact["词条"][j]["属性名"], "属性值": num, "强化次数": up_num, "颜色": "white" if check_effective(artifact["词条"][j]["属性名"], effective) else "#afafaf"})
        if artifact_pk_info not in artifact_all:
            artifact_all.append(copy.deepcopy(artifact_pk_info))
        if len(artifact_all) > 8:
            artifact_all = sorted(artifact_all, key=lambda x: float(x["评分"]), reverse=True)[:8]
    return await draw_artifact_card(title, uid, artifact_all, ace2_num=0, ace_num=0, plugin_version=plugin_version)
