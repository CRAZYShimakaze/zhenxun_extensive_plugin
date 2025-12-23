import datetime
import os
import re

from PIL import ImageFont

from ..utils.json_utils import load_json, save_json

GENSHIN_CARD_PATH = os.path.join(os.path.dirname(__file__), "..")

GENSHIN_DATA_PATH = GENSHIN_CARD_PATH + "/user_data"
player_info_path = GENSHIN_DATA_PATH + "/player_info"
group_info_path = GENSHIN_DATA_PATH + "/group_info"
card_res_path = GENSHIN_CARD_PATH + "/res/"
data_res_path = GENSHIN_DATA_PATH + "/res/"
qq_logo_path = GENSHIN_DATA_PATH + "/qq_logo/"
json_path = card_res_path + "json_data"
bg_path = card_res_path + "background"
char_pic_path = data_res_path + "character"
avatar_path = data_res_path + "avatar"
other_path = card_res_path + "other"
regoin_path = card_res_path + "region"
outline_path = card_res_path + "outline"
skill_path = data_res_path + "skill"
talent_path = data_res_path + "talent"
weapon_path = data_res_path + "weapon"
reli_path = data_res_path + "reli"
font_path = card_res_path + "fonts"
# weapon = load_json(path=f"{json_path}/weapon.json")
weapon_loc = load_json(path=f"{json_path}/loc.json")
prop_list = {
    "FIGHT_PROP_BASE_ATTACK": "基础攻击力",
    "FIGHT_PROP_BASE_DEFENSE": "基础防御力",
    "FIGHT_PROP_BASE_HP": "基础生命值",
    "FIGHT_PROP_ATTACK": "攻击力",
    "FIGHT_PROP_ATTACK_PERCENT": "百分比攻击力",
    "FIGHT_PROP_HP": "生命值",
    "FIGHT_PROP_HP_PERCENT": "百分比生命值",
    "FIGHT_PROP_DEFENSE": "防御力",
    "FIGHT_PROP_DEFENSE_PERCENT": "百分比防御力",
    "FIGHT_PROP_ELEMENT_MASTERY": "元素精通",
    "FIGHT_PROP_CRITICAL": "暴击率",
    "FIGHT_PROP_CRITICAL_HURT": "暴击伤害",
    "FIGHT_PROP_ANTI_CRITICAL": "暴击抗性",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "元素充能效率",
    "FIGHT_PROP_FIRE_SUB_HURT": "火元素抗性",
    "FIGHT_PROP_ELEC_SUB_HURT": "雷元素抗性",
    "FIGHT_PROP_ICE_SUB_HURT": "冰元素抗性",
    "FIGHT_PROP_WATER_SUB_HURT": "水元素抗性",
    "FIGHT_PROP_WIND_SUB_HURT": "风元素抗性",
    "FIGHT_PROP_ROCK_SUB_HURT": "岩元素抗性",
    "FIGHT_PROP_GRASS_SUB_HURT": "草元素抗性",
    "FIGHT_PROP_FIRE_ADD_HURT": "火元素伤害加成",
    "FIGHT_PROP_ELEC_ADD_HURT": "雷元素伤害加成",
    "FIGHT_PROP_ICE_ADD_HURT": "冰元素伤害加成",
    "FIGHT_PROP_WATER_ADD_HURT": "水元素伤害加成",
    "FIGHT_PROP_WIND_ADD_HURT": "风元素伤害加成",
    "FIGHT_PROP_ROCK_ADD_HURT": "岩元素伤害加成",
    "FIGHT_PROP_GRASS_ADD_HURT": "草元素伤害加成",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "物理伤害加成",
    "FIGHT_PROP_HEAL_ADD": "治疗加成",
    "FIGHT_PROP_HEALED_ADD": "受治疗加成",
    "FIGHT_PROP_NONE": "",
}
artifact_list = load_json(path=f"{json_path}/artifact.json")
role_ori = load_json(path=f"{json_path}/score.json")
role_skill = load_json(path=f"{json_path}/roles_skill.json")
role_info_json = load_json(path=f"{json_path}/role_info.json")
convert = {
    "hp": "百分比生命值",
    "atk": "百分比攻击力",
    "def": "百分比防御力",
    "cpct": "暴击率",
    "cdmg": "暴击伤害",
    "mastery": "元素精通",
    "dmg": "元素伤害加成",
    "phy": "物理伤害加成",
    "recharge": "元素充能效率",
    "heal": "治疗加成",
}
role_score = {}
for item in role_ori.keys():
    role_score[item] = {}
    for info in role_ori.get(item).keys():
        if role_ori.get(item).get(info) != 0:
            role_score[item][convert.get(info)] = role_ori.get(item).get(info)


class PlayerInfo:
    def __init__(self, uid: [int, str]):
        self.path = f"{player_info_path}/{uid}.json"
        self.data = load_json(path=self.path)
        self.player_info = self.data["玩家信息"] if "玩家信息" in self.data else {}
        self.roles = self.data["角色"] if "角色" in self.data else {}
        if "圣遗物榜单" not in self.data:
            self.data["圣遗物榜单"] = []
        if "小毕业圣遗物" not in self.data:
            self.data["小毕业圣遗物"] = 0
        if "大毕业圣遗物" not in self.data:
            self.data["大毕业圣遗物"] = 0
        if "圣遗物列表" not in self.data:
            self.data["圣遗物列表"] = [[], [], [], [], []]

    def set_player(self, data: dict):
        self.player_info["昵称"] = data.get("nickname", "unknown")
        self.player_info["等级"] = data.get("level", "unknown")
        self.player_info["世界等级"] = data.get("worldLevel", "unknown")
        self.player_info["签名"] = data.get("signature", "unknown")
        self.player_info["成就"] = data.get("finishAchievementNum", "unknown")
        self.player_info["角色列表"] = dictlist_to_list(data.get("showAvatarInfoList"))
        self.player_info["名片列表"] = data.get("showNameCardIdList", "unknown")
        self.player_info["头像"] = data["profilePicture"].get("avatarId", "unknown")
        self.player_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

    def set_role(self, data: dict):
        role_info = {}
        role_name = get_name_by_id(str(data["avatarId"]))
        if role_name is not None:
            role_info["名称"] = role_name
            role_info["等级"] = int(data["propMap"]["4001"]["val"])
            if role_name in ["荧", "空"]:
                traveler_skill = role_skill["Name"][list(data["skillLevelMap"].keys())[-2]]
                find_element = re.search(r"([风雷岩草水火冰])", traveler_skill).group(1)
                role_info["元素"] = find_element
                role_name = find_element + "主"
            else:
                role_info["元素"] = role_info_json[role_name]["元素"]

            if "talentIdList" in data:
                if len(data["talentIdList"]) >= 3:
                    data["skillLevelMap"][list(data["skillLevelMap"].keys())[role_info_json[role_name]["命座转换"][0]]] += 3
                if len(data["talentIdList"]) >= 5:
                    data["skillLevelMap"][list(data["skillLevelMap"].keys())[role_info_json[role_name]["命座转换"][1]]] += 3

            role_info["天赋"] = []
            for skill in data["skillLevelMap"]:
                if skill[-1] == "1":
                    if role_info_json[role_name]["武器"] == "单手剑":
                        skill_detail = {
                            "等级": data["skillLevelMap"][skill],
                            "图标": "Skill_A_01",
                        }
                    elif role_info_json[role_name]["武器"] == "弓":
                        skill_detail = {
                            "等级": data["skillLevelMap"][skill],
                            "图标": "Skill_A_02",
                        }
                    elif role_info_json[role_name]["武器"] == "长柄武器":
                        skill_detail = {
                            "等级": data["skillLevelMap"][skill],
                            "图标": "Skill_A_03",
                        }
                    elif role_info_json[role_name]["武器"] == "双手剑":
                        skill_detail = {
                            "等级": data["skillLevelMap"][skill],
                            "图标": "Skill_A_04",
                        }
                    else:  # role_info_json[role_name]['武器'] == '法器':
                        skill_detail = {
                            "等级": data["skillLevelMap"][skill],
                            "图标": "Skill_A_Catalyst_MD",
                        }
                elif skill[-1] == "2":
                    skill_detail = {
                        "等级": data["skillLevelMap"][skill],
                        "图标": f"Skill_S_{role_info_json[role_name]['英文名']}_01",
                    }
                else:  # if skill[-1] == '5':
                    skill_detail = {
                        "等级": data["skillLevelMap"][skill],
                        "图标": f"Skill_E_{role_info_json[role_name]['英文名']}_01",
                    }
                role_info["天赋"].append(skill_detail)
            if role_info["名称"] == "神里绫华":
                role_info["天赋"][0], role_info["天赋"][-1] = (
                    role_info["天赋"][-1],
                    role_info["天赋"][0],
                )
                role_info["天赋"][2], role_info["天赋"][-1] = (
                    role_info["天赋"][-1],
                    role_info["天赋"][2],
                )
            if role_info["名称"] in ["神里绫华", "莫娜"]:
                role_info["天赋"].pop(2)
            if role_info["名称"] == "安柏":
                role_info["天赋"][0], role_info["天赋"][-1] = (
                    role_info["天赋"][-1],
                    role_info["天赋"][0],
                )
            if role_info["名称"] in ["空", "荧"]:
                role_info["天赋"][0], role_info["天赋"][-1] = (
                    role_info["天赋"][-1],
                    role_info["天赋"][0],
                )
                role_info["天赋"][1], role_info["天赋"][-1] = (
                    role_info["天赋"][-1],
                    role_info["天赋"][1],
                )
            if role_info["名称"] == "达达利亚":
                role_info["天赋"][0]["等级"] += 1

            role_info["命座"] = []
            if "talentIdList" in data:
                if role_name in ["空", "荧"]:
                    if role_info["元素"] == "风":
                        role_name = "风主"
                    elif role_info["元素"] == "雷":
                        role_name = "雷主"
                    elif role_info["元素"] == "岩":
                        role_name = "岩主"
                    elif role_info["元素"] == "草":
                        role_name = "草主"
                    elif role_info["元素"] == "水":
                        role_name = "水主"
                    elif role_info["元素"] == "火":
                        role_name = "火主"
                talent = [
                    f"UI_Talent_S_{role_info_json[role_name]['英文名']}_01",
                    f"UI_Talent_S_{role_info_json[role_name]['英文名']}_02",
                    f"UI_Talent_U_{role_info_json[role_name]['英文名']}_01",
                    f"UI_Talent_S_{role_info_json[role_name]['英文名']}_03",
                    f"UI_Talent_U_{role_info_json[role_name]['英文名']}_02",
                    f"UI_Talent_S_{role_info_json[role_name]['英文名']}_04",
                ]
                for i in range(len(data["talentIdList"])):
                    talent_detail = talent[i]
                    role_info["命座"].append(talent_detail)

            prop = {}
            prop["基础生命"] = round(data["fightPropMap"]["1"])
            prop["额外生命"] = round(data["fightPropMap"]["2000"] - prop["基础生命"])
            prop["基础攻击"] = round(data["fightPropMap"]["4"])
            prop["额外攻击"] = round(data["fightPropMap"]["2001"] - prop["基础攻击"])
            prop["基础防御"] = round(data["fightPropMap"]["7"])
            prop["额外防御"] = round(data["fightPropMap"]["2002"] - prop["基础防御"])
            prop["暴击率"] = round(data["fightPropMap"]["20"], 3)
            prop["暴击伤害"] = round(data["fightPropMap"]["22"], 3)
            prop["元素精通"] = round(data["fightPropMap"]["28"])
            prop["元素充能效率"] = round(data["fightPropMap"]["23"], 3)
            prop["治疗加成"] = round(data["fightPropMap"]["26"], 3)
            prop["受治疗加成"] = round(data["fightPropMap"]["27"], 3)
            prop["伤害加成"] = [round(data["fightPropMap"]["30"], 3)]
            for i in range(40, 47):
                prop["伤害加成"].append(round(data["fightPropMap"][str(i)], 3))
            role_info["属性"] = prop

            weapon_info = {}
            weapon_data = data["equipList"][-1]
            weapon_info["名称"] = weapon_loc["zh-cn"][weapon_data["flat"]["nameTextMapHash"]]
            weapon_info["图标"] = weapon_data["flat"]["icon"]
            # weapon_info["类型"] = weapon["Type"][weapon_info["名称"]]
            weapon_info["等级"] = weapon_data["weapon"]["level"]
            weapon_info["星级"] = weapon_data["flat"]["rankLevel"]
            if "promoteLevel" in weapon_data["weapon"]:
                weapon_info["突破等级"] = weapon_data["weapon"]["promoteLevel"]
            else:
                weapon_info["突破等级"] = 0
            if "affixMap" in weapon_data["weapon"]:
                weapon_info["精炼等级"] = list(weapon_data["weapon"]["affixMap"].values())[0] + 1
            else:
                weapon_info["精炼等级"] = 1
            weapon_info["基础攻击"] = weapon_data["flat"]["weaponStats"][0]["statValue"]
            try:
                weapon_info["副属性"] = {
                    "属性名": prop_list[weapon_data["flat"]["weaponStats"][1]["appendPropId"]],
                    "属性值": weapon_data["flat"]["weaponStats"][1]["statValue"],
                }
            except IndexError:
                weapon_info["副属性"] = {"属性名": "无属性", "属性值": 0}
            weapon_info["特效"] = "待补充"
            role_info["武器"] = weapon_info

            artifacts = []
            for artifact in data["equipList"][:-1]:
                artifact_info = {}
                artifact_info["名称"] = artifact_list["Name"][artifact["flat"]["icon"]]
                artifact_info["图标"] = artifact["flat"]["icon"]
                artifact_info["部位"] = artifact_list["Piece"][artifact["flat"]["icon"].split("_")[-1]][1]
                artifact_info["所属套装"] = artifact_list["Mapping"][artifact_info["名称"]]
                artifact_info["等级"] = artifact["reliquary"]["level"] - 1
                artifact_info["星级"] = artifact["flat"]["rankLevel"]
                artifact_info["主属性"] = {
                    "属性名": prop_list[artifact["flat"]["reliquaryMainstat"]["mainPropId"]],
                    "属性值": artifact["flat"]["reliquaryMainstat"]["statValue"],
                }
                artifact_info["词条"] = []
                for reliquary in artifact["flat"].get("reliquarySubstats", []):
                    artifact_info["词条"].append(
                        {
                            "属性名": prop_list[reliquary["appendPropId"]],
                            "属性值": reliquary["statValue"],
                        }
                    )
                artifacts.append(artifact_info)
            role_info["圣遗物"] = artifacts
            role_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            self.roles[role_info["名称"]] = role_info

    def get_player_info(self):
        return self.player_info

    def get_update_roles_list(self):
        return self.player_info["角色列表"]

    def get_roles_list(self):
        return list(self.roles.keys())

    def get_artifact_list(self, pos):
        return list(self.data["圣遗物列表"][pos])

    def get_roles_info(self, role_name):
        if role_name in self.roles:
            return self.roles[role_name]
        else:
            return None

    def save(self):
        self.data["玩家信息"] = self.player_info
        self.data["角色"] = self.roles
        save_json(data=self.data, path=self.path)


def get_name_by_id(role_id: str):
    """
    根据角色id获取角色名
    :param role_id: 角色id
    :return: 角色名字符串
    """
    if role_id == "10000005":
        return "空"
    if role_id == "10000007":
        return "荧"
    for i in role_info_json.keys():
        if role_id in role_info_json[i].get("id", []):
            return i
    print(f"未找到角色id对应的名称，id：{role_id}")
    return None


def dictlist_to_list(data):
    if not isinstance(data, list):
        return "unknown"
    new_data = []
    for d in data:
        name = get_name_by_id(str(d["avatarId"]))
        new_data.append(name)
    return new_data


def get_font(size, font="hywh.ttf"):
    return ImageFont.truetype(str(font_path + "/" + font), size)
