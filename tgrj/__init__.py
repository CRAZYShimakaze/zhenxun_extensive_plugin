from nonebot import on_regex
from nonebot.params import RegexGroup

from utils.http_utils import AsyncHttpx

__zx_plugin_name__ = "舔狗日记"
__plugin_usage__ = """
usage：
    舔狗的一天
    指令：
       舔狗日记|tgrj
""".strip()
__plugin_des__ = "舔狗的一天"
__plugin_cmd__ = ["舔狗日记|tgrj"]
__plugin_version__ = 0.1
__plugin_type__ = ("群内小游戏",)
__plugin_author__ = 'CRAZYSHIMAKAZE'
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["舔狗日记", "tgrj"],
}

tgrj = on_regex("^(舔狗日记|tgrj)(.*)", priority=5, block=True)

url = "http://ovooa.com/API/tgrj/api.php"


@tgrj.handle()
async def _(args=RegexGroup()):
    name = args[1].strip()
    if name:
        data = await AsyncHttpx.get(url)
        data = data.text.replace('你', name).replace('您', name)
        await tgrj.send(data)
