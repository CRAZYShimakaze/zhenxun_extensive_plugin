from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg

from utils.http_utils import AsyncHttpx
from utils.utils import get_message_at, get_bot

__zx_plugin_name__ = "舔狗日记"
__plugin_usage__ = """
usage：
    舔狗的一天
    指令：
       舔狗日记|tgrj [被舔对象昵称] [at]
""".strip()
__plugin_des__ = "舔狗的一天"
__plugin_cmd__ = ["舔狗日记|tgrj"]
__plugin_version__ = 0.2
__plugin_type__ = ("群内小游戏",)
__plugin_author__ = 'CRAZYSHIMAKAZE'
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["舔狗日记", "tgrj"],
}

tgrj = on_command("舔狗日记", aliases={"tgrj"}, priority=5, block=True)

url = "https://cloud.qqshabi.cn/api/tiangou/api.php"


@tgrj.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    name = arg.extract_plain_text().strip()
    if not name and isinstance(event, GroupMessageEvent) and (ats := get_message_at(event.json())):
        bot = get_bot()
        qq_name = await bot.get_stranger_info(user_id=ats[0])
        name = qq_name["nickname"]
    if name:
        data = await AsyncHttpx.get(url)
        data = data.text.replace('你', name).replace('您', name)
        await tgrj.send(data)
