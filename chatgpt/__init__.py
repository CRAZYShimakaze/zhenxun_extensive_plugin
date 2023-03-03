import asyncio

import openai
from configs.config import Config
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

__zx_plugin_name__ = "ChatGPT"
__plugin_usage__ = """
usage：
    问答：世界树+问题
    设置历史记录长度：上下文长度+数字(建议不超过20)
    清空历史记录：重置世界树
""".strip()
__plugin_des__ = "ChatGPT"
__plugin_cmd__ = ["世界树"]
__plugin_type__ = ("一些工具",)
__plugin_version__ = 0.1
__plugin_author__ = "CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "admin_level": 2,
    "default_status": True,
    "limit_superuser": False,
    "cmd": __plugin_cmd__,
}
__plugin_cd_limit__ = {
    "cd": 10,
    "rst": "请求过快！"
}
Config.add_plugin_config(
    "ChatGPT",
    "API_KEY",
    None,
    name="ChatGPT",
    help_="登陆https://platform.openai.com/account/api-keys获取",
    default_value=None,
)
ai = on_command("世界树", priority=5, block=True)
context_set = on_command("上下文长度", permission=SUPERUSER, priority=5, block=True)
reset = on_command("重置世界树", permission=SUPERUSER, priority=5, block=True)

# 会话记录
conversations = {}
ctx_len = 1


@reset.handle()
async def _(event: MessageEvent):
    global conversations
    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    try:
        conversations.pop(chat_id)
    except:
        pass
    await reset.send("世界树重置完毕")


@context_set.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global conversations, ctx_len
    msg = arg.extract_plain_text().strip()
    if not msg:
        return
    else:
        msg = int(msg)
    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    conversation = conversations.get(chat_id, [])
    try:
        if not conversations:
            init_chatbot()
        if not conversation:
            conversations[chat_id] = [[], msg]
        else:
            conversation[1] = msg
    except Exception as e:
        await context_set.finish(str(e))
    await context_set.finish("上下文长度设置完成！")


@ai.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    global conversations, ctx_len
    msg = arg.extract_plain_text().strip()
    if not msg:
        return

    chat_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else str(event.user_id)
    conversation = conversations.get(chat_id, [])
    try:
        if not conversations:
            init_chatbot()
        if not conversation:
            conversation = [[], ctx_len]
            conversations[chat_id] = conversation
        # 获取GPT回复
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ask, msg, conversation[0])
    except Exception as e:
        return await ai.finish(str(e))
    conversation[0].append({"role": "user", "content": msg})
    conversation[0].append({"role": "assistant", "content": response})

    conversation[0] = conversation[0] if len(conversation[0]) < conversation[1] * 2 else conversation[0][2:]
    conversations[chat_id] = conversation

    await ai.send(response, at_sender=True)


def ask(msg, conversation):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation + [{"role": "user", "content": msg}])
    return response['choices'][0]['message']['content'].strip('\n')


def init_chatbot():
    api_key = Config.get_config("ChatGPT", "API_KEY")
    if not api_key:
        raise Exception("未配置API_KEY,请在config.yaml文件中进行配置")
    openai.api_key = api_key
