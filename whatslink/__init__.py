import asyncio
import io
import os

from PIL import Image, ImageFilter
from configs.path_config import DATA_PATH
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (Bot, Message, MessageEvent, MessageSegment, GroupMessageEvent, )
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from utils.http_utils import AsyncHttpx
from .data_source import get_bt_info
# from ..plugin_utils.auth_utils import check_gold

__zx_plugin_name__ = "搜车"
__plugin_usage__ = """
usage：
    搜索关键字并获取预览图
    指令：
       搜车+关键字
       验车+磁链
       反和谐开启/关闭[超级用户命令]
""".strip()
__plugin_des__ = "搜索关键字并获取预览图"
__plugin_cmd__ = ["搜车", "验车"]
__plugin_version__ = 0.3
__plugin_type__ = ("一些工具",)
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {"level": 5, "default_status": True, "limit_superuser": False, "cmd": ["搜车", "验车"], }
__plugin_cd_limit__ = {"cd": 10, "limit_type": "group", "rst": "太快啦,歇一歇吧..."}
search = on_command("搜车", priority=5, block=True)
check = on_command("验车", priority=5, block=True)
transparent = on_command("反和谐", permission=SUPERUSER, priority=5, block=True)

blur = True
proxy = ""


@transparent.handle()
async def get_bt(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    global blur
    keyword = arg.extract_plain_text().strip()
    blur = True if keyword in ["关闭", "关"] else False
    await transparent.send(f"已{'关闭' if blur else '开启'}反和谐！")


@search.handle()
async def get_bt(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    global cnt
    keyword = arg.extract_plain_text().strip()
    result = await get_bt_info(keyword)
    if not result:
        await check.finish("没有找到结果！")
    # await check_gold(event, coin=10, percent=1)
    mes_list = []
    cnt = 1
    for item in result:
        title, type_, create_time, file_size, link = item
        info = (f"标题：{title}\n"
                f"类型：{type_}\n"
                f"创建时间：{create_time}\n"
                f"文件大小：{file_size}\n"
                f"种子：{link}\n")
        preview = await get_preview(event, link, False)
        data_info = {"type": "node",
                     "data": {"name": f"{event.sender.card or event.sender.nickname}",
                              "uin": f"{event.user_id}",
                              "content": info + preview, }, }
        mes_list.append(
            data_info)  # preview = await get_preview(event, link, False)  # mes_list = (mes_list + preview)  # + {"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}", "uin": f"{event.user_id}", "content": '※预览图来源于https://whatslink.info/※', }, }
    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=mes_list)
    else:
        await bot.send_private_forward_msg(user_id=event.user_id, messages=mes_list)


@check.handle()
async def check_bt(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    link = arg.extract_plain_text().strip()
    preview = await get_preview(event, link, True)
    # await check_gold(event, coin=10, percent=1)
    return await check.send(preview)
    for item in preview:
        await check.send(item["data"]["content"])
    return
    if isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=preview)
    else:
        await bot.send_private_forward_msg(user_id=event.user_id, messages=preview)


async def get_preview(event, link, title=False):
    global blur
    w, h = 640, 360
    url = proxy + "https://whatslink.info/api/v1/link"
    # await check_gold(event, coin=50, percent=1)
    url += "?url=" + link
    data = await AsyncHttpx.get(url)
    data = data.json()
    if (size := data["size"] / 1024 / 1024) >= 1024:
        size = f"{round(size / 1024, 2)}G"
    else:
        size = f"{round(size, 2)}M"
    screenshots_list = []
    if screenshots := data["screenshots"]:
        if title:
            screenshots_list = [f"该文件为{data['name']},大小{size}.预览图:\n"]
        else:
            screenshots_list = []
        data["name"] = data["name"][:80] if len(data["name"]) > 80 else data["name"]

        total_width = w
        total_height = sum(h for i in range(5))

        # 创建一个新的图片，用于拼接
        new_image = Image.new("RGB", (total_width, total_height))

        # 用于记录当前图片拼接的高度位置
        y_offset = 0

        save_path_sum = DATA_PATH / "bt_search" / f"{data['name']}.jpg"
        if not save_path_sum.exists():
            save_path = DATA_PATH / "bt_search" / f"{data['name']}_tmp.jpg"
            for item in screenshots:
                await asyncio.sleep(1)
                out_img = ""
                await AsyncHttpx.download_file(proxy + item["screenshot"], save_path, follow_redirects=True, )
                try:
                    ori_image = Image.open(save_path)
                    ori_image = ori_image.resize((w, h))
                    new_image.paste(ori_image, (0, y_offset))
                    y_offset += h
                    break
                except:
                    continue
                if len(screenshots_list) >= 6:
                    break
            os.unlink(save_path)
            new_image = new_image.crop((0, 0, w, y_offset))
            new_image.save(save_path_sum)
            blur_image = new_image.filter(ImageFilter.GaussianBlur(5)) if blur else new_image
            out_img = io.BytesIO()
            blur_image.save(out_img, format="JPEG")
        else:
            blur_image = Image.open(save_path_sum)
            blur_image = blur_image.filter(ImageFilter.GaussianBlur(5)) if blur else blur_image
            out_img = io.BytesIO()
            blur_image.save(out_img, format="JPEG")
        screenshots_list.append(MessageSegment.image(out_img))
        if title:
            return screenshots_list[0] + MessageSegment.image(out_img)
        else:
            return screenshots_list[0]
        mes_list = []
        for item in screenshots_list:
            mes_list.append({"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}",
                                                      "uin": f"{event.user_id}", "content": item, }, })
        return mes_list
    else:
        # return [{"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}", "uin": f"{event.user_id}", "content": f"该文件为{data['name']},大小{size}.预览图:无", }, }]
        return f"该文件为{data['name']},大小{size}.预览图:无"
