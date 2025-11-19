from collections import OrderedDict

from nonebot import on_message, on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupRecallNoticeEvent, MessageEvent
from nonebot.plugin import PluginMetadata

from zhenxun.configs.config import BotConfig
from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import PluginType

__plugin_meta__ = PluginMetadata(
    name="消息防撤回",
    description="消息防撤回",
    usage="""
    消息防撤回：
    当消息被撤回或收到闪照时自动触发；
    将撤回的消息/闪照发送给超级用户；
    ————麻麻再也不怕我错过群里的女装照片了！
    """.strip(),
    extra=PluginExtraData(
        author="CRAZYSHIMAKAZE",
        version="0.1",
        plugin_type=PluginType.HIDDEN,
    ).to_dict(),
)
if_withdraw = on_notice(priority=1, block=False)
get_mes = on_message(priority=1, block=False)
message_dict = OrderedDict()  # 用于存储消息id和消息内容的字典


@get_mes.handle()
async def _(bot: Bot, event: MessageEvent):
    # entity = get_entity_ids(session)
    # 获取发送消息时间

    if event.message_id not in message_dict:
        message_dict[event.message_id] = await bot.get_msg(message_id=event.message_id)
    # 删除最早添加的消息
    if len(message_dict) > 300:
        message_dict.popitem(last=False)


# 检测撤回消息
@if_withdraw.handle()
async def if_withdraw_handle(
    bot: Bot, event: GroupRecallNoticeEvent
):  # 此处event不知道应该调用哪个，所以暂时不用
    if (
        event.notice_type == "group_recall" and event.user_id not in []
    ):  # 不发送自己的和群其他机器人的撤回消息
        # 获取撤回消息的消息id
        new = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id
        )
        group_info = await bot.get_group_info(
            group_id=event.group_id
        )
        # print(group_info)
        new = new["nickname"]
        group_name = group_info["group_name"]
        recall_message_id = event.message_id
        if recall_message_id in message_dict:
            for superuser in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(superuser),
                    # await bot.send_group_msg(
                    # group_id=event.group_id,
                    message=f"啊嘞?{BotConfig.self_nickname}检测到※{new}※在群聊※{group_name}※撤回消息：\n{message_dict[recall_message_id]['message']}",
                )
        # 获取撤回消息的消息内容
        # 将撤回消息发送给所有超级用户
        # isok = 0
        # if isok:  # 如果1，则在群里发，如果0，则私聊管理员
        #     name1 = await GroupInfoUser.get_member_info(event.user_id, event.group_id)
        #     name = name1.user_name
        #     # if isinstance(event, GroupMessageEvent):
        #     # print("\n\n\n\n" + name + "\n\n")
        #     await bot.send_group_msg(
        #         group_id=event.group_id,
        #         message=f"{name} 撤回的内容：\n{recall_message_content['message']}",
        #     )
        # else:
        #     for superuser in bot.config.superusers:
        #         await bot.send_private_msg(
        #             user_id=superuser,
        #             message=f"{event.user_id} 在群聊 {event.group_id} 撤回了一条消息\n"
        #             f"撤回消息内容：\n{recall_message_content['message']}",
        #         )
