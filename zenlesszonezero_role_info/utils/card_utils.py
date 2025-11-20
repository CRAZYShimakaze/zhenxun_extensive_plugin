import datetime
import os

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
path_path = data_res_path + "path"
char_pic_path = data_res_path + "character"
avatar_path = data_res_path + "avatar"
other_path = card_res_path + "other"
type_path = card_res_path + "type"
outline_path = card_res_path + "outline"
skill_path = data_res_path + "skill"
talent_path = data_res_path + "talent"
weapon_path = data_res_path + "weapon"
reli_path = data_res_path + "reli"
font_path = card_res_path + "fonts"

avatar_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/avatars.json"
equipments_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/equipments.json"
locs_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/locs.json"
medals_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/medals.json"
namecards_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/namecards.json"
pfps_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/pfps.json"
property_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/property.json"
titles_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/titles.json"
weapons_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/weapons.json"
equipmentleveltemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/EquipmentLevelTemplateTb.json"
weaponleveltemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/WeaponLevelTemplateTb.json"
weaponstartemplatetb_url = "https://git.mero.moe/dimbreath/ZenlessData/raw/branch/master/FileCfg/WeaponStarTemplateTb.json"

score_json = load_json(path=f"{json_path}/score.json")
avatars_json = load_json(path=f"{json_path}/avatars.json")
locs = load_json(path=f"{json_path}/locs.json")
locs = locs["zh-cn"]
property_json = load_json(path=f"{json_path}/property.json")
equipments_json = load_json(path=f"{json_path}/equipments.json")
equipmentleveltemplatetb_json = load_json(path=f"{json_path}/EquipmentLevelTemplateTb.json")
weaponleveltemplatetb_json = load_json(path=f"{json_path}/WeaponLevelTemplateTb.json")
weaponstartemplatetb_json = load_json(path=f"{json_path}/WeaponStarTemplateTb.json")
prop_list = {
    "生命值": "11101",
    "攻击力": "12101",
    "防御力": "13101",
    "冲击力": "12201",
    "暴击率": "20101",
    "暴击伤害": "21101",
    "异常掌控": "31401",
    "异常精通": "31201",
    "能量自动回复": "30501",
    "穿透率": "",
    "穿透值": "",
    "贯穿力": "",
    "伤害加成": "",
}


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
        if item == "":
            continue
        if artifacts.count(item) >= 4:
            suit_4.append(item)
        elif artifacts.count(item) >= 2:
            suit_2.append(item)
    return suit_4, suit_2


class PlayerInfo:
    def __init__(self, uid: [int, str]):
        self.path = f"{player_info_path}/{uid}.json"
        self.data = load_json(path=self.path)
        self.player_info = self.data["玩家信息"] if "玩家信息" in self.data else {}
        self.roles = self.data["角色"] if "角色" in self.data else {}
        if "驱动盘榜单" not in self.data:
            self.data["驱动盘榜单"] = []
        if "小毕业驱动盘" not in self.data:
            self.data["小毕业驱动盘"] = 0
        if "大毕业驱动盘" not in self.data:
            self.data["大毕业驱动盘"] = 0
        if "驱动盘列表" not in self.data:
            self.data["驱动盘列表"] = [[], [], [], [], [], []]

    def set_player(self, data: dict):
        player_info = data["SocialDetail"]["ProfileDetail"]
        self.player_info["昵称"] = player_info.get("Nickname", "unknown")
        self.player_info["等级"] = player_info.get("Level", "unknown")
        # self.player_info["世界等级"] = data.get("worldLevel", "unknown")
        # self.player_info["签名"] = data.get("signature", "unknown")
        # self.player_info["成就"] = data.get("finishAchievementNum", "unknown")
        self.player_info["角色列表"] = dictlist_to_list(data["ShowcaseDetail"].get("AvatarList", []))
        # self.player_info["名片列表"] = data.get("showNameCardIdList", "unknown")
        # self.player_info["头像"] = data["profilePicture"].get("avatarId", "unknown")
        self.player_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

    def set_role(self, data: dict):
        role_info = {}
        role_name, role_json = get_name_by_id(str(data["Id"]))
        if role_name is not None:
            role_info["名称"] = role_name
            role_info["等级"] = data["Level"]
            role_info["元素"] = role_json["ElementTypes"][0]
            role_info["特性"] = role_json["Specialty"]["Name"]
            role_info["技能"] = [0] * 6
            role_info["立绘"] = avatars_json[str(data["Id"])]["Image"]
            index_conver = [0, 3, 1, 4, -1, 5, 2]
            for item in data["SkillLevelList"]:
                # if item["Index"] == 5:
                #     continue
                role_info["技能"][index_conver[item["Index"]]] = item["Level"]
            role_info["影画"] = data["TalentLevel"]
            if role_info["影画"] >= 5:
                role_info["技能"] = [item + 2 for item in role_info["技能"]]
            if role_info["影画"] >= 3:
                role_info["技能"] = [item + 2 for item in role_info["技能"]]

            artifacts = [{}] * 6
            for artifact in data.get("EquippedList", []):
                artifact_info = {}
                suitid = equipments_json["Items"][str(artifact["Equipment"]["Id"])]["SuitId"]
                artifact_json = load_json(path=f"{json_path}/Suits/{suitid}.json")
                artifact_info["名称"] = artifact_json["Name"]
                artifact_info["图标"] = equipments_json["Suits"][str(suitid)]["Icon"]
                artifact_info["部位"] = artifact["Slot"]
                artifact_info["所属套装"] = suitid
                artifact_info["等级"] = artifact["Equipment"]["Level"]
                artifact_info["星级"] = equipments_json["Items"][str(artifact["Equipment"]["Id"])]["Rarity"]
                val = 0
                for inffo in equipmentleveltemplatetb_json["MOFGFFKBLLC"]:
                    if inffo["DJEPJPBAFCE"] == artifact_info["等级"] and inffo["OANJJBHJLHD"] == artifact_info["星级"]:
                        val = inffo["GMJIPPMIIIF"]
                        break
                artifact_info["主属性"] = {
                    "属性名": locs.get(property_json.get(str(artifact["Equipment"]["MainPropertyList"][0]["PropertyId"]))["Name"]),
                    "属性值": artifact["Equipment"]["MainPropertyList"][0]["PropertyValue"] * (1 + val / 10000),
                }
                artifact_info["词条"] = []
                for reliquary in artifact["Equipment"].get("RandomPropertyList", []):
                    artifact_info["词条"].append(
                        {
                            "属性名": locs.get(property_json.get(str(reliquary["PropertyId"]))["Name"]),
                            "属性值": reliquary["PropertyValue"] * reliquary["PropertyLevel"],
                            "提升次数": reliquary["PropertyLevel"] - 1,
                        }
                    )
                artifacts[artifact_info["部位"] - 1] = artifact_info
            role_info["驱动盘"] = artifacts

            prop = {}
            prop_json = avatars_json[str(data["Id"])]
            for i in prop_list.items():
                growth_value = (prop_json["GrowthProps"].get(i[1], 0) * (data["Level"] - 1)) / 10000
                promotion_value = prop_json["PromotionProps"][data["PromotionLevel"] - 1].get(i[1], 0)
                core_enhancement_value = prop_json["CoreEnhancementProps"][data["CoreSkillEnhancement"]].get(i[1], 0)
                prop[f"基础{i[0]}"] = prop_json["BaseProps"].get(i[1], 0) + growth_value + promotion_value + core_enhancement_value

            weapon_info = {}
            if data.get("Weapon") is not None:
                weapon_data = data["Weapon"]
                weapon_json = load_json(path=f"{json_path}/Weapons/{weapon_data['Id']}.json")
                weapon_info["名称"] = weapon_json["ItemName"]
                weapon_info["图标"] = weapon_json["ImagePath"]
                weapon_info["类型"] = weapon_json["Profession"]["Name"]
                weapon_info["等级"] = weapon_data["Level"]
                weapon_info["星级"] = weapon_json["Rarity"]
                weapon_info["突破等级"] = weapon_data["BreakLevel"]
                weapon_info["精炼等级"] = weapon_data["UpgradeLevel"]
                weapon_info["基础攻击"] = weapon_json["MainStat"]["PropertyValue"] * (
                    1 + weaponleveltemplatetb_json["MOFGFFKBLLC"][weapon_info["等级"]]["GMJIPPMIIIF"] / 10000 + weaponstartemplatetb_json["MOFGFFKBLLC"][weapon_info["突破等级"]]["IDDHKNJKBBK"] / 10000
                )
                try:
                    weapon_info["副属性"] = {
                        "属性名": locs.get(property_json.get(str(weapon_json["SecondaryStat"]["PropertyId"]))["Name"]),
                        "属性值": weapon_json["SecondaryStat"]["PropertyValue"] * (1 + weaponstartemplatetb_json["MOFGFFKBLLC"][weapon_info["突破等级"]]["POLGGADDPLI"] / 10000),
                    }
                except IndexError:
                    weapon_info["副属性"] = {"属性名": "无属性", "属性值": 0}
                prop["基础攻击力"] += weapon_info["基础攻击"]

                for i in prop_list.keys():
                    if weapon_info["副属性"]["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + weapon_info["副属性"]["属性值"]
                        break
                    elif weapon_info["副属性"]["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * weapon_info["副属性"]["属性值"] / 10000
                        break
            role_info["武器"] = weapon_info
            for item in role_info["驱动盘"]:
                if not item:
                    continue
                for i in prop_list.keys():
                    if item["主属性"]["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + item["主属性"]["属性值"]
                        break
                    elif item["主属性"]["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * item["主属性"]["属性值"] / 10000
                        break
                if "伤害加成" in item["主属性"]["属性名"]:
                    prop["额外伤害加成"] = prop.get("额外伤害加成", 0) + item["主属性"]["属性值"]
                for vice in item["词条"]:
                    for i in prop_list.keys():
                        if vice["属性名"] == i:
                            prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + vice["属性值"]
                            break
                        elif vice["属性名"] == f"{i}百分比":
                            prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * vice["属性值"] / 10000
                            break
            suit_4, suit_2 = get_artifact_suit([item.get("所属套装", "") for item in artifacts])
            relic_suit_prop = []
            if suit_2 + suit_4:
                for suit in suit_2 + suit_4:
                    for key, val in equipments_json["Suits"][str(suit)]["SetBonusProps"].items():
                        suit_prop = {
                            "属性名": locs.get(property_json.get(str(key))["Name"]),
                            "属性值": val,
                        }
                        relic_suit_prop.append(suit_prop)
            for vice in relic_suit_prop:
                for i in prop_list.keys():
                    if vice["属性名"] == i:
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + vice["属性值"]
                        break
                    elif vice["属性名"] == f"{i}百分比":
                        prop[f"额外{i}"] = prop.get(f"额外{i}", 0) + prop[f"基础{i}"] * vice["属性值"] / 10000
                        break
                if "伤害加成" in vice["属性名"]:
                    prop["额外伤害加成"] = prop.get("额外伤害加成", 0) + vice["属性值"]

            if role_info["特性"] == "命破":
                prop["基础贯穿力"] = 0.3 * (prop["基础攻击力"] + prop.get("额外攻击力", 0)) + 0.1 * (prop["基础生命值"] + prop.get("额外生命值", 0))
            role_info["属性"] = prop

            role_info["更新时间"] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
            self.roles[role_info["名称"]] = role_info

    def get_player_info(self):
        return self.player_info

    def get_update_roles_list(self):
        return self.player_info["角色列表"]

    def get_roles_list(self):
        return list(self.roles.keys())

    def get_artifact_list(self, pos):
        return list(self.data["驱动盘列表"][pos])

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
    if os.path.exists(f"{json_path}/Avatars/{role_id}.json"):
        role_info_json = load_json(path=f"{json_path}/Avatars/{role_id}.json")
        return role_info_json.get("Name"), role_info_json
    print(f"未找到角色id对应的名称，id：{role_id}")
    return None, None


def dictlist_to_list(data):
    if not isinstance(data, list):
        return "unknown"
    new_data = []
    for d in data:
        name, _ = get_name_by_id(str(d["Id"]))
        new_data.append(name)
    return new_data


def get_font(size, font="hywh.ttf"):
    return ImageFont.truetype(str(font_path + "/" + font), size)
