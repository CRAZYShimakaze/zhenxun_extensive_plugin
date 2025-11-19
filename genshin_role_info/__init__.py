import base64
import copy
from datetime import datetime
import os
from pathlib import Path
import random
import re
import shutil
import time

import nonebot
from nonebot import Driver, on_command, on_message, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.permission import PRIVATE
from nonebot.params import CommandArg, RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import PluginType
from zhenxun.utils.http_utils import AsyncHttpx

from ..plugin_utils.auth_utils import gold_cost
from .data_source.draw_artifact_card import draw_artifact_card
from .data_source.draw_recommend_card import (
    gen_artifact_adapt,
    gen_artifact_recommend,
    gen_suit_recommend,
)
from .data_source.draw_role_card import draw_role_card
from .data_source.draw_update_card import draw_role_pic
from .utils.card_utils import (
    PlayerInfo,
    get_name_by_id,
    group_info_path,
    json_path,
    load_json,
    other_path,
    player_info_path,
    save_json,
)
from .utils.image_utils import image_build, load_image
from .utils.json_utils import get_message_at

__plugin_meta__ = PluginMetadata(
    name="原神角色面板",
    description="原神角色面板",
    usage="""
    查询橱窗内角色的面板
    指令：
        原神绑定UID/uidXXX
        原神解绑
        角色面板 (例:刻晴面板、刻晴面板@XXX、刻晴面板+uid)
        更新原神面板 (uid)
        圣遗物导入
        XX(花羽沙杯冠)适配
        XX(花羽沙杯冠)推荐
        XX(乐团/魔女/...)套推荐
        XX(乐团/魔女/...)独立套推荐
        原神角色排行
        最强XX (例:最强甘雨)
        最菜XX
        圣遗物榜单
        群圣遗物榜单
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="4.2.1",
        plugin_type=PluginType.NORMAL,
    ).to_dict(),
)
__zx_plugin_name__ = __plugin_meta__.name
__plugin_version__ = __plugin_meta__.extra.get("version")

enka_url = "https://enka.network/api/uid/{}"
microgg_url = "https://profile.microgg.cn/api/uid/{}"
weapon_loc_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/loc.json"
api_url = [microgg_url, enka_url]
bind = on_regex(r"(?:原神绑定|绑定原神).*?(\d+)", priority=5, block=True)
unbind = on_command("原神解绑", priority=5, block=True)
card_list = on_command("原神角色排行", priority=4, block=True)

driver: Driver = nonebot.get_driver()

get_card = on_regex(r"(.*)面板(.*)", priority=4, block=False)
group_best = on_regex(r"^(最强|群最强)(.*)", priority=4)
group_worst = on_regex(r"^(最菜|群最菜)(.*)", priority=4)
artifact_adapt = on_regex("(.*?)([花羽沙杯冠])适配", priority=4)
artifact_recommend = on_regex("(.*?)([花羽沙杯冠套])推荐", priority=4)
artifact_list = on_command("圣遗物榜单", aliases={"圣遗物排行"}, priority=4, block=True)
group_artifact_list = on_command("群圣遗物榜单", aliases={"群圣遗物排行"}, priority=4, block=True)
reset_best = on_command("重置最强", permission=SUPERUSER, priority=3, block=False)
check_update = on_command("检查原神面板更新", permission=SUPERUSER, priority=3, block=True)
artifact_info = load_json(f"{json_path}/artifact.json")
role_info_json = load_json(f"{json_path}/role_info.json")
import_artifact = on_message(permission=PRIVATE, priority=1, block=False)
# import_artifact = on_notice(priority=1, block=False)
import_artifact_hint = on_command("圣遗物导入", priority=4, block=True)
check = on_command("gsck", permission=SUPERUSER, priority=4, block=True)


@check.handle()
async def _(event: MessageEvent):
    uid = await get_msg_uid(event)
    url = f"https://enka.network/u/{uid}"  # await capture(event, url)


def get_role_name(role):
    role_name = ""
    for item in role_info_json.keys():
        if role in role_info_json.get(item).get("别名", []) or role == item:
            role_name = item
            break
    return role_name


async def get_uid(user_qq):
    qq2uid = load_json(f"{player_info_path}/qq2uid.json")
    return qq2uid.get(str(user_qq), "")


def bind_uid(user_qq, uid):
    qq2uid = load_json(f"{player_info_path}/qq2uid.json")
    qq2uid[str(user_qq)] = uid
    save_json(qq2uid, f"{player_info_path}/qq2uid.json")


def unbind_uid(user_qq):
    qq2uid = load_json(f"{player_info_path}/qq2uid.json")
    qq2uid.pop(str(user_qq))
    save_json(qq2uid, f"{player_info_path}/qq2uid.json")


async def get_msg_uid(event):
    at_user = get_message_at(event.json())
    user_qq = at_user[0] if at_user else event.user_id
    uid = await get_uid(user_qq)
    # uid = genshin_user.uid if genshin_user else None
    if not uid:
        await artifact_list.finish(  # MessageSegment.reply(event.message_id) +
            "请发送'绑定原神uidxxxx'后再查询！"
        )
    print(f"UID={uid}")
    return uid


async def get_enka_info(uid, update_info, event):
    update_role_list = []
    if not os.path.exists(f"{player_info_path}/{uid}.json") or update_info:
        req = 0
        for i in range(2):
            try:
                print(f"请求{api_url[i].format(uid)}...")
                req = await AsyncHttpx.get(url=api_url[i].format(uid), follow_redirects=True)
            except Exception as e:
                print(e)
                continue
            if req.status_code == 200:
                break
            else:
                print(req.status_code)
        else:
            hint = "未知问题..."
            try:
                status_code = req.status_code
            except:
                return await get_card.finish(  # MessageSegment.reply(event.message_id) +
                    hint
                )
            if status_code == 400:
                hint = "UID 格式错误..."
            elif status_code == 404:
                hint = "玩家不存在（MHY 服务器说的）..."
            elif status_code == 424:
                hint = "游戏维护中 / 游戏更新后一切都崩溃了..."
            elif status_code == 429:
                hint = "请求频率限制（被我的或者MHY的服务器）..."
            elif status_code == 500:
                hint = "服务器错误..."
            elif status_code == 503:
                hint = "我搞砸了..."
            return await get_card.finish(  # MessageSegment.reply(event.message_id) +
                hint
            )
        data = req.json()
        player_info = PlayerInfo(uid)
        player_info.set_player(data["playerInfo"])
        if data.get("avatarInfoList", ""):
            for role in data["avatarInfoList"]:
                try:
                    player_info.set_role(role)
                    update_role_list.append(get_name_by_id(str(role["avatarId"])))
                except Exception as e:
                    await get_card.send(str(e))
            player_info.save()
        else:
            guide = load_image(f"{other_path}/collections.png")
            guide = image_build(img=guide, quality=100, mode="RGB")
            return await get_card.finish(  # MessageSegment.reply(event.message_id) +
                guide + "在游戏中打开显示详情选项!"
            )
    else:
        player_info = PlayerInfo(uid)
    return player_info, update_role_list


async def check_artifact(event, player_info, roles_list, uid, group_save):
    artifact_all = player_info.data["圣遗物列表"]
    pos_name = ["生之花", "死之羽", "时之沙", "空之杯", "理之冠"]
    for i in range(5):
        for item in player_info.data["圣遗物列表"][i]:
            if "角色" not in item:
                item["角色"] = ""
            elif item["角色"] in roles_list:
                item["角色"] = ""
        for role_name in roles_list:
            role_data = player_info.get_roles_info(role_name)
            artifact_list = [{} for _ in range(5)]
            if "圣遗物" not in role_data:
                continue
            for j in range(len(role_data["圣遗物"])):
                artifact_list[pos_name.index(role_data["圣遗物"][j]["部位"])] = role_data["圣遗物"][j]
            artifact_copy = copy.deepcopy(artifact_list[i])
            if artifact_copy.get("等级", 0) >= 10:
                for name_all in list(role_info_json.keys()) + [""]:
                    artifact_copy["角色"] = name_all
                    if artifact_copy in artifact_all[i]:
                        artifact_all[i].remove(artifact_copy)
                artifact_copy["角色"] = role_name
                artifact_all[i].append(artifact_copy)
    roles_list = player_info.get_roles_list()
    player_info.data["圣遗物榜单"] = []
    player_info.data["大毕业圣遗物"] = 0
    player_info.data["小毕业圣遗物"] = 0

    for role_name in roles_list:
        role_data = player_info.get_roles_info(role_name)
        try:
            _, _ = await draw_role_card(uid, role_data, player_info, __plugin_version__, only_cal=True)
        except:
            pass
    player_info.save()
    if group_save and isinstance(event, GroupMessageEvent):
        check_group_artifact(event, player_info)


async def check_role_avaliable(role_name, roles_list, event):
    if not roles_list:
        guide = load_image(f"{other_path}/collections.png")
        guide = image_build(img=guide, quality=100, mode="RGB")
        await get_card.finish(  # MessageSegment.reply(event.message_id) +
            guide + "无角色信息,在游戏中将角色放入展柜并输入更新原神面板!",
            at_sender=False,
        )
    if role_name not in roles_list:
        await get_card.finish(  # MessageSegment.reply(event.message_id) +
            f"角色展柜里没有{role_name}的信息哦!可查询:{','.join(roles_list)}",
            at_sender=False,
        )


@bind.handle()
async def _(event: MessageEvent, arg: tuple[str, ...] = RegexGroup()):
    msg = arg[0].strip()
    uid = await get_uid(event.user_id)
    if not msg.isdigit():
        await bind.finish(  # MessageSegment.reply(event.message_id) +
            "uid/id必须为纯数字！", at_senders=False
        )
    msg = int(msg)
    if uid:
        await bind.finish(  # MessageSegment.reply(event.message_id) +
            f"您已绑定过uid：{uid}，如果希望更换uid，请先发送原神解绑"
        )
    else:
        if not check_uid(msg):
            await bind.finish(  # MessageSegment.reply(event.message_id) +
                f"绑定的uid{msg}不合法，请重新绑定!"
            )
        bind_uid(event.user_id, msg)
        await bind.finish(  # MessageSegment.reply(event.message_id) +
            f"已成功添加原神uid：{msg}"
        )


@unbind.handle()
async def _(event: MessageEvent):
    if get_uid(event.user_id):
        unbind_uid(event.user_id)
        await unbind.send(  # MessageSegment.reply(event.message_id) +
            "用户数据删除成功..."
        )


@import_artifact_hint.handle()
async def _():
    await import_artifact_hint.send(
        "请在PC端按以下步骤操作\n1.下载https://github.com/CRAZYShimakaze/yas/releases/download/0.1.21/yas_artifact_v0.1.21.exe\n2.打开原神，切换到背包圣遗物页面，将背包拉到最上面\n3.在该目录下命令行窗口输入./yas_artifact_v0.1.21.exe -f good --min-level 20命令,开始扫描\n4.扫描完成后，添加机器人为好友，将生成的good.json文件私聊发送给机器人即可。"
    )


@import_artifact.handle()
async def import_artifact(bot: Bot, event):
    match = re.search(r"file=([\w\d_]+\.json)", str(event.message))
    if match:
        filename = match.group(1)
        print(filename)
        if filename != "good.json":
            return
    else:
        return
    match = re.search(r"file_id=([\w-]+)", str(event.message))
    if match:
        file_id = match.group(1)
        print(file_id)
    x = await bot.get_file(file_id=file_id)
    """
    if event.notice_type != "offline_file":
        return
    if event.file.get('name') != 'good.json':
        return
    """
    convert = load_json(path=f"{json_path}/convert.json")
    role = role_info_json
    name = convert.get("名称")
    # icon = artifact.get('图标')
    icon = artifact_info.get("Name")
    suit = convert.get("套装")
    pos = convert.get("位置")
    main = convert.get("主词条")
    sub = convert.get("副词条")
    # print(f'x:{x}')
    uid = await get_msg_uid(event)
    player_info, _ = await get_enka_info(uid, update_info=False, event=event)
    # await AsyncHttpx.download_file(event.file.get('url'), f'{player_info_path}/{uid}_artifact.json')
    decoded_data = base64.b64decode(x.get("base64", ""))
    with open(f"{player_info_path}/{uid}_artifact.json", "wb") as file:
        file.write(decoded_data)
    arti = load_json(path=f"{player_info_path}/{uid}_artifact.json")
    if "artifacts" in arti:
        await bot.send_private_msg(user_id=event.user_id, message="检测到圣遗物缓存文件,正在导入...")
        same = 0
        diff = 0
        player_info.data["圣遗物列表"] = [[], [], [], [], []]
        conver_name = ["生之花", "死之羽", "时之沙", "空之杯", "理之冠"]
        for item in arti.get("artifacts"):
            if item.get("level", 0) == 20 and item.get("rarity", 0) == 5:
                mainstatkey = item.get("mainStatKey", "")
                substats = item.get("substats", [])
                pos_id = pos.get(item.get("slotKey", ""))
                pos_name = conver_name[pos_id]
                arti_name = name.get(suit.get(item.get("setKey", "")))[pos_id]
                for key, value in icon.items():
                    if value == arti_name:
                        icon_name = key
                        break
                else:
                    print("wrong!")
                role_name = ""
                for key, value in role.items():
                    print(value["英文名"], item.get("location", ""))
                    if value["英文名"] == item.get("location", ""):
                        role_name = key
                        break
                artifact_single = {
                    "名称": arti_name,
                    "图标": icon_name,
                    "部位": pos_name,
                    "所属套装": suit.get(item.get("setKey", "")),
                    "等级": item.get("level", 0),
                    "星级": item.get("rarity", 0),
                    "角色": role_name,
                    "主属性": {
                        "属性名": main.get(mainstatkey, "")["属性名"],
                        "属性值": main.get(mainstatkey, "")["属性值"],
                    },
                    "词条": [
                        {
                            "属性名": sub.get(substats[0].get("key", "")),
                            "属性值": int(substats[0].get("value", 0)) if substats[0].get("value", 0) % 1 == 0 else round(substats[0].get("value", 0), 1),
                        },
                        {
                            "属性名": sub.get(substats[1].get("key", "")),
                            "属性值": int(substats[1].get("value", 0)) if substats[1].get("value", 0) % 1 == 0 else round(substats[1].get("value", 0), 1),
                        },
                        {
                            "属性名": sub.get(substats[2].get("key", "")),
                            "属性值": int(substats[2].get("value", 0)) if substats[2].get("value", 0) % 1 == 0 else round(substats[2].get("value", 0), 1),
                        },
                        {
                            "属性名": sub.get(substats[3].get("key", "")),
                            "属性值": int(substats[3].get("value", 0)) if substats[3].get("value", 0) % 1 == 0 else round(substats[3].get("value", 0), 1),
                        },
                    ],
                }
                if artifact_single not in player_info.data["圣遗物列表"][pos_id]:
                    player_info.data["圣遗物列表"][pos_id].append(copy.deepcopy(artifact_single))
                    diff += 1
                else:
                    same += 1
        player_info.save()
        await bot.send_private_msg(
            user_id=event.user_id,
            message=f"UID{uid}的缓存圣遗物已导入,本次共导入{diff}个,重复圣遗物{same}个.",
        )


@artifact_adapt.handle()
@gold_cost(coin=1, percent=1)
async def test(bot: Bot, event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    msg = args[0].strip(), args[1].strip()
    uid = await get_msg_uid(event)
    if msg[1] not in ["花", "羽", "沙", "杯", "冠"]:
        return await artifact_adapt.finish("请输入正确角色名和圣遗物名称(花羽沙杯冠)...", at_sender=True)
    role = msg[0]
    pos = ["花", "羽", "沙", "杯", "冠"].index(msg[1])
    role_name = get_role_name(role)
    if not role_name:
        return
    player_info, _ = await get_enka_info(uid, update_info=False, event=event)
    roles_list = player_info.get_roles_list()
    await check_role_avaliable(role_name, roles_list, event)
    role_data = player_info.get_roles_info(role_name)
    pos_list = 0
    for index, item in enumerate(role_data["圣遗物"]):
        if item["部位"] == ["生之花", "死之羽", "时之沙", "空之杯", "理之冠"][pos]:
            pos_list = index
            break
    else:
        await artifact_adapt.finish(  # MessageSegment.reply(event.message_id) +
            f"{role_name}{pos}号位没有圣遗物！", at_sender=False
        )
    img, _ = await gen_artifact_adapt(  # MessageSegment.reply(event.message_id) +
        f"{role}圣遗物适配({msg[1]})",
        role_data["圣遗物"][pos_list],
        uid,
        role,
        pos,
        __plugin_version__,
    )
    await artifact_adapt.send(img)


@artifact_recommend.handle()
@gold_cost(coin=1, percent=1)
async def test(bot: Bot, event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    msg = args[0].strip(), args[1].strip()
    uid = await get_msg_uid(event)
    main_prop = [
        "爆伤",
        "暴击",
        "精通",
        "生命",
        "防御",
        "攻击",
        "火伤",
        "冰伤",
        "雷伤",
        "物伤",
        "风伤",
        "水伤",
        "岩伤",
        "草伤",
        "治疗",
        "充能",
    ]
    suit_list = artifact_info.get("Info")
    element = ""
    suit_name = ""
    is_suit = False
    occupy = False
    info = msg[0]
    for item in main_prop:
        if item in info:
            element = item
            info = info.replace(item, "")
            break
    if "独立" in info:
        info = info.replace("独立", "")
        occupy = True
    for item in suit_list:
        if item[:2] in info:
            suit_name = item
            info = info.replace(item[:2], "")
            break
    role = info
    pos = ["花", "羽", "沙", "杯", "冠", "套"].index(msg[1])
    if pos == 5:
        is_suit = True
    role_name = get_role_name(role)
    if not role_name:
        return
    player_info, _ = await get_enka_info(uid, update_info=False, event=event)
    artifact_pos_list = []
    if not is_suit:
        artifact_pos_list = player_info.get_artifact_list(pos)
        if not artifact_list:
            return await artifact_recommend.finish(  # MessageSegment.reply(event.message_id) +
                f"{pos}号位没有圣遗物缓存！请先执行'更新面板'指令！", at_sender=False
            )
    roles_list = player_info.get_roles_list()
    await check_role_avaliable(role_name, roles_list, event)
    role_data = player_info.get_roles_info(role_name)
    if not is_suit:
        img, _ = await gen_artifact_recommend(
            f"{role_name}{suit_name}{element}{msg[1]}推荐",
            role_data,
            artifact_pos_list,
            uid,
            role_name,
            pos,
            element,
            suit_name,
            __plugin_version__,
        )
    else:
        img = await gen_suit_recommend(
            f"{suit_name}{element}套推荐",
            role_data,
            player_info,
            uid,
            role_name,
            suit_name,
            occupy,
            __plugin_version__,
        )
    if not img:
        await artifact_recommend.finish(  # MessageSegment.reply(event.message_id) +
            "未找到符合条件的圣遗物推荐!"
        )
    await artifact_recommend.send(  # MessageSegment.reply(event.message_id) +
        img + "注:仅根据当前缓存圣遗物进行推荐,发送'圣遗物导入'可导入背包内所有圣遗物."
    )


@group_artifact_list.handle()
@gold_cost(coin=1, percent=1)
async def _(bot: Bot, event: MessageEvent):
    group_id = event.group_id
    if not os.path.exists(f"{group_info_path}/{group_id}.json"):
        return await group_artifact_list.finish(  # MessageSegment.reply(event.message_id) +
            "未收录任何圣遗物信息,请先进行查询!"
        )
    else:
        group_artifact_info = load_json(f"{group_info_path}/{group_id}.json")
        img, _ = await draw_artifact_card(
            "群圣遗物榜单",
            None,
            group_id,
            group_artifact_info,
            None,
            None,
            __plugin_version__,
            1,
        )
        await group_artifact_list.send(  # MessageSegment.reply(event.message_id) +
            img
        )


@artifact_list.handle()
@gold_cost(coin=1, percent=1)
async def _(bot: Bot, event: MessageEvent):
    uid = await get_msg_uid(event)
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        return await artifact_list.finish(  # MessageSegment.reply(event.message_id) +
            "未收录任何角色信息,请先进行角色查询!", at_sender=False
        )
    else:
        player_info = PlayerInfo(uid)
        if not player_info.data["圣遗物榜单"]:
            return await artifact_list.finish(  # MessageSegment.reply(event.message_id) +
                "未收录任何圣遗物信息,请先输入'更新面板'命令!", at_sender=False
            )
        roles_list = player_info.get_roles_list()
        img, text = await draw_artifact_card(
            "圣遗物榜单",
            None,
            uid,
            player_info.data["圣遗物榜单"],
            player_info.data["大毕业圣遗物"],
            player_info.data["小毕业圣遗物"],
            __plugin_version__,
        )
        await artifact_list.send(  # MessageSegment.reply(event.message_id) +
            img + text, at_sender=False
        )  # + f"\n数据来源:{','.join(roles_list)}", at_sender=True)


@get_card.handle()
async def _(event: MessageEvent, args: tuple[str, ...] = RegexGroup()):
    role = args[0].strip()
    at_user = args[1].strip()
    merge_ = role + at_user
    # if role not in ["更新原神", "刷新原神"]:
    if "原神" not in merge_:
        role = get_role_name(role)
    if not role:
        return
    if at_user.isdigit():
        uid = int(at_user)
    else:
        uid = await get_msg_uid(event)
    if ("更新" in merge_ or "刷新" in merge_) and "原神" in merge_:
        if at_user:
            await update(event, uid, group_save=False)
        else:
            await update(event, uid, group_save=True)
    else:
        await gen(event, uid, role, at_user=at_user)


@group_best.handle()
async def _(event: GroupMessageEvent, args: tuple[str, ...] = RegexGroup()):
    role = args[1].strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f"{group_info_path}/{event.group_id}/{role}"
    if not os.path.exists(role_path):
        await group_best.finish(  # MessageSegment.reply(event.message_id) +
            f"本群还没有{role}的数据收录哦！赶快去查询吧！", at_sender=False
        )
    else:
        data = sorted(os.listdir(role_path), key=lambda x: float(x.split("-")[0]))
        role_info = data[-1]
        role_pic = load_image(f"{role_path}/{role_info}")
        role_pic = image_build(img=role_pic, quality=100, mode="RGB")
        bot = nonebot.get_bot()
        qq_name = await bot.get_stranger_info(user_id=int(role_info.split("-")[-1].rstrip(".png")))
        qq_name = qq_name["nickname"]
        await group_best.send(  # MessageSegment.reply(event.message_id) +
            f"本群最强{role}!仅根据圣遗物评分评判.\n由'{qq_name}'查询\n" + role_pic
        )


@group_worst.handle()
async def _(event: GroupMessageEvent, args: tuple[str, ...] = RegexGroup()):
    role = args[1].strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f"{group_info_path}/{event.group_id}/{role}"
    if not os.path.exists(role_path) or len(os.listdir(role_path)) < 2:
        await group_worst.finish(  # MessageSegment.reply(event.message_id) +
            f"本群还没有最菜{role}的数据收录哦！赶快去查询吧！", at_sender=False
        )
    else:
        data = sorted(os.listdir(role_path), key=lambda x: float(x.split("-")[0]))
        role_info = data[0]
        role_pic = load_image(f"{role_path}/{role_info}")
        role_pic = image_build(img=role_pic, quality=100, mode="RGB")
        bot = nonebot.get_bot()
        qq_name = await bot.get_stranger_info(user_id=int(role_info.split("-")[-1].rstrip(".png")))
        qq_name = qq_name["nickname"]
        await group_worst.send(  # MessageSegment.reply(event.message_id) +
            f"本群最菜{role}!仅根据圣遗物评分评判.\n由'{qq_name}'查询\n" + role_pic
        )


@reset_best.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    role = arg.extract_plain_text().strip()
    role = get_role_name(role)
    if not role:
        return
    role_path = f"{group_info_path}/{event.group_id}/{role}"
    shutil.rmtree(role_path, ignore_errors=True)
    await reset_best.finish(f"重置群{role}成功!")


@card_list.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg:
        return
    uid = await get_msg_uid(event)
    await get_char(uid, event)


async def get_char(uid, event):
    url = enka_url.format(uid)
    if not os.path.exists(f"{player_info_path}/{uid}.json"):
        try:
            req = await AsyncHttpx.get(url=url, follow_redirects=True)
        except Exception as e:
            print(e)
            return await get_card.finish("更新出错,请重试...")
        if req.status_code != 200:
            return await get_card.finish("服务器维护中,请稍后再试...")
        data = req.json()
        player_info = PlayerInfo(uid)
        try:
            player_info.set_player(data["playerInfo"])
            if data.get("avatarInfoList", ""):
                for role in data["avatarInfoList"]:
                    player_info.set_role(role)
                player_info.save()
            else:
                guide = load_image(f"{other_path}/collections.png")
                guide = image_build(img=guide, quality=100, mode="RGB")
                await get_card.finish(  # MessageSegment.reply(event.message_id) +
                    guide + "在游戏中打开显示详情选项!", at_sender=False
                )
        except Exception as e:
            print(e)
            return  # await char_card.finish("发生错误，请尝试更新命令！", at_sender=True)
    else:
        player_info = PlayerInfo(uid)
    roles_list = player_info.get_roles_list()
    if not roles_list:
        guide = load_image(f"{other_path}/collections.png")
        guide = image_build(img=guide, quality=100, mode="RGB")
        await get_card.finish(  # MessageSegment.reply(event.message_id) +
            guide + "无角色信息,在游戏中将角色放入展柜并输入更新角色卡XXXX(uid)!",
            at_sender=False,
        )
    else:
        await card_list.send(  # MessageSegment.reply(event.message_id) +
            await draw_role_pic(uid, roles_list, player_info), at_sender=False
        )


@gold_cost(coin=1, percent=1)
async def gen(event: MessageEvent, uid, role_name, at_user):
    player_info, _ = await get_enka_info(uid, update_info=False, event=event)
    roles_list = player_info.get_roles_list()
    await check_role_avaliable(role_name, roles_list, event)
    role_data = player_info.get_roles_info(role_name)
    img, score = await draw_role_card(uid, role_data, player_info, __plugin_version__, only_cal=False)
    msg = "" if at_user else check_role(role_name, event, img, score)
    img = image_build(img=img, quality=100, mode="RGB")
    await get_card.sendh(  # MessageSegment.reply(event.message_id) +
        msg + img, at_sender=False
    )


@gold_cost(coin=1, percent=1)
async def update(event: MessageEvent, uid, group_save):
    if os.path.exists(f"{player_info_path}/{uid}.json"):
        data = load_json(f"{player_info_path}/{uid}.json")
        if "玩家信息" in data.keys():
            given_time_str = data["玩家信息"]["更新时间"]
            given_time = datetime.strptime(given_time_str, "%Y-%m-%d %H:%M:%S")

            # 获取当前时间的datetime对象
            current_time = datetime.now()

            # 计算时间差并转换为秒数
            time_difference_seconds = (current_time - given_time).total_seconds()
            mod_time = os.path.getmtime(f"{player_info_path}/{uid}.json")
            cd_time = int(time.time() - mod_time)
            if time_difference_seconds < 60:
                await get_card.finish(  # MessageSegment.reply(event.message_id) +
                    f"{60 - cd_time}秒后可再次更新!", at_sender=False
                )
    player_info, update_role_list = await get_enka_info(uid, update_info=True, event=event)
    await check_artifact(event, player_info, update_role_list, uid, group_save)
    await get_card.send(  # MessageSegment.reply(event.message_id) +
        await draw_role_pic(uid, update_role_list, player_info)
    )


def check_role(role_name, event, img, score):
    if isinstance(event, GroupMessageEvent) and str(score)[-1] != "*":
        role_path = f"{group_info_path}/{event.group_id}/{role_name}/{score}-{event.user_id}.png"
        role_path = Path(role_path)
        role_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.listdir(role_path.parent):
            img.save(role_path)
            return f"恭喜成为本群最强{role_name}!\n"
        else:
            data = sorted(os.listdir(role_path.parent), key=lambda x: float(x.split("-")[0]))
            role_info_best = data[-1].split("-")
            if len(os.listdir(role_path.parent)) == 1:
                img.save(role_path)
                if float(role_info_best[0]) <= score:
                    old_best = int(role_info_best[1].rstrip(".png"))
                    if old_best != event.user_id:
                        return Message(f"恭喜你击败{MessageSegment.at(old_best)}成为本群最强{role_name}!\n")
                    else:
                        return f"你仍然是本群最强{role_name}!\n"
                else:
                    return f"恭喜你成为本群最菜{role_name}!\n距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
            else:
                if float(role_info_best[0]) <= score:
                    os.unlink(f"{role_path.parent}/{data[-1]}")
                    img.save(role_path)
                    old_best = int(role_info_best[1].rstrip(".png"))
                    if old_best != event.user_id:
                        return Message(f"恭喜你击败{MessageSegment.at(old_best)}成为本群最强{role_name}!\n")
                    else:
                        return f"你仍然是本群最强{role_name}!\n"
                else:
                    role_info_worst = data[0].split("-")
                    if float(role_info_worst[0]) >= score:
                        os.unlink(f"{role_path.parent}/{data[0]}")
                        img.save(role_path)
                        old_worst = int(role_info_worst[1].rstrip(".png"))
                        if old_worst != event.user_id:
                            return Message(f"恭喜你帮助{MessageSegment.at(old_worst)}摆脱最菜{role_name}的头衔!\n")
                        else:
                            return f"你仍然是本群最菜{role_name}!\n距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
                    else:
                        return f"距本群最强{role_name}还有{round(float(role_info_best[0]) - score, 2)}分差距!\n"
    return ""


def check_group_artifact(event, player_info):
    if not os.path.exists(f"{group_info_path}/{event.group_id}.json"):
        group_artifact_info = []
    else:
        group_artifact_info = load_json(f"{group_info_path}/{event.group_id}.json")
    group_player_info = copy.deepcopy(player_info.data["圣遗物榜单"])
    for item in group_player_info:
        item["QQ"] = event.user_id
        if item not in group_artifact_info:
            group_artifact_info.append(item)
    group_artifact_info_20 = sorted(group_artifact_info, key=lambda x: float(x["评分"]), reverse=True)[:20]
    save_json(group_artifact_info_20, f"{group_info_path}/{event.group_id}.json")


def check_uid(uid):
    return re.search(r"^[123456789]\d{8}$", str(uid)) is not None


async def get_update_info():
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_info/README.md"
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r"\*\*\[v\d.\d.\d]((?:.|\n)*?)\*\*", str(version.text))
    except Exception as e:
        print(f"{__zx_plugin_name__}插件获取更新内容失败，请检查github连接性是否良好!: {e}")
        return ""
    return version.group(1).strip()


@check_update.handle()
async def _check_update():
    await AsyncHttpx.download_file(weapon_loc_url, path=f"{json_path}/weapon_loc.json", follow_redirects=True)
    url = "https://raw.githubusercontent.com/CRAZYShimakaze/zhenxun_extensive_plugin/main/genshin_role_info/__init__.py"
    bot = nonebot.get_bot()
    try:
        version = await AsyncHttpx.get(url, follow_redirects=True)
        version = re.search(r'__plugin_version__ = "(\d+\.\d+\.\d+)"', str(version.text))
    except Exception as e:
        print(f"{__zx_plugin_name__}插件检查更新失败，请检查github连接性是否良好!: {e}")
        return
    if version.group(1) > __plugin_version__:
        update_info = await get_update_info()
        try:
            await check_update.send(f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{update_info}")
        except Exception:
            for admin in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(admin),
                    message=f"检测到{__zx_plugin_name__}插件有更新(当前V{__plugin_version__},最新V{version.group(1)})！请前往github下载！\n本次更新内容如下:\n{update_info}",
                )
            print(f"检测到{__zx_plugin_name__}插件有更新！请前往github下载！")
    else:
        update_info = await get_update_info()
        try:
            await check_update.send(f"{__zx_plugin_name__}插件已经是最新V{__plugin_version__}！最近一次的更新内容如下:\n{update_info}")
        except Exception:
            pass


@driver.on_startup
async def _():
    scheduler.add_job(
        _check_update,
        "cron",
        hour=random.randint(9, 22),
        minute=random.randint(0, 59),
        id="genshin_role_info",
    )
