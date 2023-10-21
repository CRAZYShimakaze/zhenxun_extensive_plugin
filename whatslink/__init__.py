from PIL import Image, ImageFilter
from configs.path_config import TEMP_PATH
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment, GroupMessageEvent
from nonebot.params import CommandArg

from utils.http_utils import AsyncHttpx

# from ..plugin_utils.auth_utils import check_gold

__zx_plugin_name__ = "验车"
__plugin_usage__ = """
usage：
    速览链接内容
    指令：
       验车[DDL/Torrent/Ed2k链接]
""".strip()
__plugin_des__ = "速览链接内容"
__plugin_cmd__ = ["验车"]
__plugin_version__ = 0.1
__plugin_type__ = ("一些工具",)
__plugin_author__ = 'CRAZYSHIMAKAZE'
__plugin_settings__ = {"level": 5, "default_status": True, "limit_superuser": False, "cmd": ["验车"], }
__plugin_cd_limit__ = {"cd": 10, "limit_type": "group", "rst": "发车太快啦,歇一歇吧..."}
check = on_command("验车", priority=5, block=True)


@check.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    url = "https://whatslink.info/api/v1/link"
    # await check_gold(event, coin=50, percent=1)
    link = arg.extract_plain_text().strip()
    url += '?url=' + link
    data = await AsyncHttpx.get(url)
    data = data.json()
    if (size := data['size'] / 1024 / 1024) >= 1024:
        size = f"{round(size / 1024, 2)}G"
    else:
        size = f"{round(size, 2)}M"
    screenshots_list = '无'
    if screenshots := data['screenshots']:
        screenshots_list = [f"该文件为{data['name']},大小{size}.预览图:\n"]
        cnt = 1
        for item in screenshots:
            save_path = TEMP_PATH / f"{data['name']}_{cnt}.jpg"
            cnt += 1
            if not save_path.exists():
                await AsyncHttpx.download_file(item['screenshot'], save_path, follow_redirects=True)
            ori_image = Image.open(save_path)
            blur_image = ori_image.filter(ImageFilter.GaussianBlur(5))
            blur_image.save(save_path)
            screenshots_list.append(MessageSegment.image(save_path))
            if len(screenshots_list) >= 6:
                break
        if isinstance(event, GroupMessageEvent):
            mes_list = []
            for txt in screenshots_list:
                data = {"type": "node", "data": {"name": f"{event.sender.card or event.sender.nickname}", "uin": f"{event.user_id}", "content": txt, }, }
                mes_list.append(data)
            await bot.send_group_forward_msg(group_id=event.group_id, messages=mes_list)
        else:
            if len(screenshots_list) == 2:
                await check.send(screenshots_list[0] + screenshots_list[1])
            elif len(screenshots_list) == 3:
                await check.send(screenshots_list[0] + screenshots_list[1] + screenshots_list[2])
            elif len(screenshots_list) == 4:
                await check.send(screenshots_list[0] + screenshots_list[1] + screenshots_list[2])
            elif len(screenshots_list) == 5:
                await check.send(screenshots_list[0] + screenshots_list[1] + screenshots_list[2] + screenshots_list[3] + screenshots_list[4])
            elif len(screenshots_list) == 6:
                await check.send(screenshots_list[0] + screenshots_list[1] + screenshots_list[2] + screenshots_list[3] + screenshots_list[4] + screenshots_list[5])
    else:
        await check.send(f"该文件为{data['name']},大小{size}.预览图:无")
