import asyncio
import re

# from configs.path_config import TEMP_PATH
from matplotlib.pylab import f
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
from nonebot.params import CommandArg
from zhenxun.utils.withdraw_manage import WithdrawManager
from ..plugin_utils.auth_utils import check_gold
from ..plugin_utils.http_utils import AsyncHttpx
from nonebot.plugin import PluginMetadata
from zhenxun.utils.enum import PluginType
from zhenxun.configs.utils import PluginExtraData, RegisterConfig, PluginCdBlock
__plugin_meta__ = PluginMetadata(
    name="色图",
    description="色图",
    usage="""
    指令：
        色图XX
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.2",
        plugin_type=PluginType.NORMAL,
        limits=[PluginCdBlock(cd=5, result="冲太快了哦~")],
    ).to_dict(),
)

setu = on_command("色图", block=True, priority=5)
url = "https://api.lolicon.app/setu/v2"
host_pattern = re.compile(r"https?://([^/]+)")

ws_url = "i.pixiv.cat"# "i.pixiv.re" #pixiv反向代理地址,可自定义
forward = 0
download = 0
size_f = "regular"

async def download_and_send(bot, event, mes_list, i):
    file_name = str(i["pid"])
    title = i["title"]
    res = f'{i["width"]}x{i["height"]}'
    tags = i["tags"]
    url_ = i["urls"][size_f]

    # 替换域名
    host_match = re.match(host_pattern, url_)
    url_ = url_.replace(host_match.group(1), ws_url)
    # if download:
    #     await AsyncHttpx.download_file(url_, TEMP_PATH / file_name)
    #     url_ = TEMP_PATH / file_name

    if forward:
        try:
            data_info = {"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}", "uin": f"{event.user_id}",
                                                  "content": f'标题:{title}\npid:{file_name}\n分辨率:{res}\n标签:{",".join(tags)}\n' + MessageSegment.image(url_), }, }
        except Exception as e:
            data_info = {"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}", "uin": f"{event.user_id}", "content": f'获取图片出错QAQ', }, }
        mes_list.append(data_info)
    else:
        msg_id = await setu.send(MessageSegment.reply(event.message_id) + f'标题:{title}\npid:{file_name}\n分辨率:{res}\n标签:{",".join(tags)}\n' + MessageSegment.image(url_))
        await WithdrawManager.withdraw_message(
            bot,
            msg_id["message_id"],
            30,
        )

@setu.handle()
async def se(bot, event, arg: Message = CommandArg()):
    global forward
    tags = arg.extract_plain_text().strip()
    if not tags:
        return
    r18, tags = 1 if tags[0] == "r" else 0, tags[1:] if tags[0] == "r" else tags
    if event.user_id != 674015283:
        r18 = 0
    num, tags = tags[-1] if tags[-1].isdigit() else 1, tags[:-1] if tags[-1].isdigit() else tags
    if int(num) > 2:
        forward = 1
    else:
        forward = 0
    params = {"r18": r18,  # 添加r18参数 0为否，1为是，2为混合
              "tag": tags.split(','),  # 若指定tag
              "num": int(num),  # 一次返回的结果数量
              "size": [size_f], }
    response = await AsyncHttpx.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if not data["error"]:
            data = data["data"]
            if not data:
                await setu.finish("没有符合条件的色图...")
            mes_list = []
            if r18:
                await check_gold(event, coin=len(data) * 100, percent=1)
            else:
                await check_gold(event, coin=len(data) * 100, percent=1)
            # 创建并执行所有任务
            tasks = [download_and_send(bot, event, mes_list, i) for i in data]
            await asyncio.gather(*tasks)
            if forward:
                if isinstance(event, GroupMessageEvent):
                    msg_id = await bot.send_group_forward_msg(group_id=event.group_id, messages=mes_list)
                    await WithdrawManager.withdraw_message(
                    bot,
                    msg_id["message_id"],
                    10*len(mes_list),
                    )
                else:
                    await bot.send_private_forward_msg(user_id=event.user_id, messages=mes_list)
        else:
            await setu.finish("出错了...")
    else:
        await setu.finish("出错了...")
