from configs.config import Config, NICKNAME
from nonebot import on_request
from nonebot.adapters.onebot.v11 import (Bot)

__zx_plugin_name__ = "入群检测 [Hidden]"
__plugin_version__ = 0.1
__plugin_author__ = 'unknownsno'
__plugin_type__ = ("其他",)
__plugin_usage__ = """
usage：
    有新的入群请求时会在群内播报
""".strip()
__plugin_task__ = {"join_group": "入群检测"}

Config.add_plugin_config("_task", "DEFAULT_JOIN_GROUP", True, help_="被动 入群检测 进群默认开关状态", default_value=True, )

join_group_handle = on_request(priority=1, block=False)


@join_group_handle.handle()
async def _(bot: Bot, event):
    if event.post_type == 'request':
        if event.user_id != int(bot.self_id):
            if event.request_type == 'group':
                stranger_info = await bot.get_stranger_info(user_id=event.user_id, no_cache=False)
                await join_group_handle.finish(
                    "[[_task|join_group]]" + f'{NICKNAME}检测到加群请求哟~管理员们快去看看叭！\nID：{event.user_id}\n昵称：{stranger_info["nickname"]}\n性别：{"女" if "f" in stranger_info["sex"] else "男" if stranger_info["sex"] != "unknown" else "保密"}\n年龄：{stranger_info["age"]}\nQQ等级：{stranger_info["level"]}\n描述：{event.comment}')
