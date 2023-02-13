import asyncio
import copy
import json
import os
import platform
import re
import shutil
import subprocess
import traceback
import zipfile

from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from nonebot.exception import FinishedException
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot_plugin_htmlrender import text_to_pic

from configs.config import Config
from services.log import logger
from utils.http_utils import AsyncHttpx

__zx_plugin_name__ = "插件管理 [Superuser]"
__plugin_usage__ = """
usage：
    插件管理
    指令：
        下载插件[插件git仓库地址]
        更新插件[插件git仓库地址]
        删除插件[插件名]
        下载依赖[依赖名]
        下载依赖[依赖名]=[版本]
        更新依赖[依赖名]
""".strip()
__plugin_des__ = "插件管理"
__plugin_cmd__ = ["下载插件 [_superuser]", "更新插件 [_superuser]", "下载依赖 [_superuser]", "更新依赖 [_superuser]",
                  "删除插件 [_superuser]"]
__plugin_type__ = ("常规插件",)
__plugin_version__ = 0.1
__plugin_author__ = "mobius&CRAZYSHIMAKAZE"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["插件管理"],
}
__plugin_configs__ = {
    "PLUGINFOLDER": {
        "name": "plugin_manager",
        "value": "extensive_plugin",
        "help": "插件安装文件夹，默认extensive_plugin，需确保bot.py包含加载命令 nonebot.load_plugins(文件夹名)",
        "default_value": "extensive_plugin"
    },
    "BOTPATH": {
        "name": "plugin_manager",
        "value": None,
        "help": "真寻bot.py所在路径，如/home/zhenxun_bot",
        "default_value": None
    },
    "PIPCMD": {
        "name": "plugin_manager",
        "value": "pip",
        "help": "pip命令，默认pip,如有特殊情况（如pip3等）请修改此配置",
        "default_value": "pip"
    },
    "ISPOETRY": {
        "name": "plugin_manager",
        "value": True,
        "help": "是否使用poetry虚拟环境，默认True使用",
        "default_value": True
    },
    "ISUPDATEPIP": {
        "name": "plugin_manager",
        "value": True,
        "help": "是否更新pip，默认True更新",
        "default_value": True
    },
    "USEGIT": {
        "name": "plugin_manager",
        "value": False,
        "help": "是否使用git -clone下载完整插件仓库，默认False，不使用git时通过下载压缩包解压的方式下载插件",
        "default_value": False
    },
    "TOKEN": {
        "name": "plugin_manager",
        "value": None,
        "help": "登陆github获取https://github.com/settings/tokens/new",
        "default_value": None
    },
}
header = {'Authorization': 'token ' + str(Config.get_config("plugin_manager", "TOKEN")),
          'Accept': 'application/vnd.github.v3+json'}
installPlugin = on_command("下载插件", priority=5, permission=SUPERUSER, block=True)
updatePlugin = on_command("更新插件", priority=5, permission=SUPERUSER, block=True)
deletePlugin = on_command("删除插件", priority=5, permission=SUPERUSER, block=True)
installDependence = on_command("下载依赖", priority=5, permission=SUPERUSER, block=True)
updateDependence = on_command("更新依赖", priority=5, permission=SUPERUSER, block=True)

# 支持的系统
support_sys = ["windows", "linux"]


@deletePlugin.handle()
async def _(arg: Message = CommandArg()):
    plugin_name = arg.extract_plain_text().strip()
    bot_path = Config.get_config("plugin_manager", "BOTPATH")  # 读取配置文件
    if not bot_path:
        logger.warning("未配置BOTPATH，将从当前目录上两级寻找bot.py")
        bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # 插件安装文件夹
    plugin_folder = Config.get_config("plugin_manager", "PLUGINFOLDER")  # 读取配置文件
    # 插件安装文件夹路径
    plugin_folder_path = os.path.join(bot_path, plugin_folder)
    # 检查插件是否已安装A
    if os.path.exists(os.path.join(plugin_folder_path, plugin_name)):
        try:
            shutil.rmtree(os.path.join(plugin_folder_path, plugin_name))
            await deletePlugin.send(f'删除{plugin_name}插件完成!')
        except:
            await deletePlugin.send(f'删除{plugin_name}插件出错,文件可能被占用!')
    else:
        plugin_regex = f'[^\s\']+{plugin_name}'
        plugin_match = re.compile(plugin_regex)

        plugin_full_name = plugin_match.findall(str(os.listdir(plugin_folder_path)))
        if plugin_full_name:
            if len(plugin_full_name) == 1:
                plugin_name = plugin_full_name[0]
                try:
                    shutil.rmtree(os.path.join(plugin_folder_path, plugin_name))
                    await deletePlugin.send(f'删除{plugin_name}插件完成!')
                except:
                    await deletePlugin.send(f'删除{plugin_name}插件出错,文件可能被占用!')
            else:
                await deletePlugin.send(f'找到多个同名插件{",".join(plugin_full_name)},请输入完整名称进行删除!')
        else:
            await deletePlugin.send(f'在{plugin_folder_path}下未找到{plugin_name}插件!')


@updatePlugin.handle()
async def _(arg: Message = CommandArg()):
    sys = platform.system().lower()
    # 判断操作系统
    if sys not in support_sys:
        await updatePlugin.finish(f"目前暂未适配{sys}系统")

    # 获取仓库地址
    url = arg.extract_plain_text().strip()
    if not url:  # 不存在仓库地址
        await updatePlugin.finish(
            "未提供插件仓库地址；示例：安装插件https://github.com/CRAZYShimakaze/zhenxun_extensive_plugin")
    elif not url.startswith("https://github.com/"):
        await updatePlugin.finish("目前仅支持github仓库")
    owner, repo, branch, plugin_name, part_flag, upper_path = get_url_info(url)
    '''
    # 移除末尾.git    
    elif url.endswith(".git"):
        url = url[:-4]
    url_list = url.split('/')

    part_flag = len(url_list) > 5
    # 插件名
    plugin_name = url_list[-1]
    # 仓库作者
    owner = url_list[3]
    # 仓库名（完成版下等于插件名）
    repo = url_list[4]
    '''

    # 获取bot.py文件
    bot_path = Config.get_config("plugin_manager", "BOTPATH")  # 读取配置文件
    if not bot_path:
        logger.warning("未配置BOTPATH，将从当前目录上两级寻找bot.py")
        bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    bot_file = os.path.join(bot_path, 'bot.py')
    if not os.path.exists(bot_file):
        await updatePlugin.finish(f"未找到{bot_file}文件，请检查BOTPATH配置")

    # 插件安装文件夹
    plugin_folder = Config.get_config("plugin_manager", "PLUGINFOLDER")  # 读取配置文件
    # 插件安装文件夹路径
    plugin_folder_path = os.path.join(bot_path, plugin_folder)

    # 检查插件是否已安装
    if os.path.exists(os.path.join(plugin_folder_path, plugin_name)):
        await updatePlugin.send('删除旧版插件...')
        shutil.rmtree(os.path.join(plugin_folder_path, plugin_name))
    else:
        await updatePlugin.send('未找到旧版插件,直接进行下载...')
    # 检查插件目录是否被加载
    # TODO 已知如果该行代码被注释，可能导致误判
    try:
        with open(bot_file, "r", encoding="utf8") as rf:
            data = rf.read()
        regex = re.compile(rf'nonebot.load_plugins\([\'\"]{plugin_folder}[\'\"]\)')
        if not regex.search(data):
            msg = f'bot.py中未加载插件目录{plugin_folder}，请修改bot.py或检查PLUGINFOLDER配置'
            logger.warning(msg)
            await updatePlugin.send(msg)
    except Exception as e:
        msg = f"未能检查bot.py中是否加载插件目录{plugin_folder}，请手动检查：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await updatePlugin.send(MessageSegment.image(pic))

    # 创建插件目录
    if not os.path.exists(plugin_folder_path):
        os.makedirs(plugin_folder_path)
        # 设置权限755
        os.chmod(plugin_folder_path, 0o0755)
        logger.info(f"创建插件目录{plugin_folder_path}")

    git_flag = Config.get_config("plugin_manager", "USEGIT")  # 读取配置文件
    '''检查网址是完整git还是git下某一层目录
       完整git:  https://github.com/KarisAya/nonebot_plugin_groupmate_waifu
       目录git:  https://github.com/CRAZYShimakaze/zhenxun_extensive_plugin/tree/main/24_point
    '''

    # 下载git下某一层目录
    if part_flag:
        # 获取待下载的仓库路径 #TODO 已知如果len(url_list)大于7，会导致截取的path成为 xxxx/[插件名]，
        # 下载下来的文件结构会变成[插件目录]/xxxx/[插件名]，导致插件加载失败，但目前未发现相关案例，暂不兼容
        '''
        path = ""
        for i in range(7, len(url_list)):
            path += url_list[i] + "/"
        path = path[:-1]
        '''
        # upper_path = '/'.join(url_list[7:-1])
        # branch = re.search(r'tree/(.*?)/', url).group(1)
        index_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{upper_path + plugin_name}?ref={branch}"
        try:
            if not await getfiles(index_url, plugin_folder_path, upper_path):
                raise
            # 检查插件目录下是否有load_plugins命令
            plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
            if os.path.exists(plugin_init):
                try:
                    # 替换加载命令
                    change_load_commond(plugin_folder, plugin_name, plugin_init)
                except Exception as e:
                    msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                    logger.error(msg)
                    pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                    await updatePlugin.finish(MessageSegment.image(pic))
            await updatePlugin.finish(f"{url}安装成功，请检查依赖并重启真寻。")
        except FinishedException:
            return
        except Exception as e:
            pic = await text_to_pic(
                text=f"{url}安装失败：\n{e}\n{traceback.format_exc()}")  # 日志转图片，依赖nonebot_plugin_htmlrender
            await updatePlugin.finish(MessageSegment.image(pic))
    # 不使用git下载完整仓库
    elif not git_flag:
        # 下载仓库
        result = await get_repo(owner, repo, plugin_folder_path, plugin_name)
        # 下载失败
        if result["retcode"] != 0:
            pic = await text_to_pic(text=result["msg"])  # 日志转图片，依赖nonebot_plugin_htmlrender
            await updatePlugin.finish(MessageSegment.image(pic))
        # 检查插件目录下是否有load_plugins命令
        plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
        if os.path.exists(plugin_init):
            try:
                # 替换加载命令
                change_load_commond(plugin_folder, plugin_name, plugin_init)
            except Exception as e:
                msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                logger.error(msg)
                pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                await updatePlugin.finish(MessageSegment.image(pic))
        await updatePlugin.finish(f"{url}安装成功，请检查依赖并重启真寻。")
        # git -clone下载完整git
    else:
        # 校验git
        try:
            stdout, stderr, result = run_cmd("git --version", sys)
            if result != 0:
                if 'windows' == sys:
                    msg = "系统未安装git，请人工安装：https://git-scm.com/download/win"
                elif 'linux' == sys:
                    msg = "系统未安装git，请人工安装：https://git-scm.com/download/linux"
                else:
                    msg = "系统未安装git，请人工安装"
                await updatePlugin.finish(msg)
        except FinishedException:
            return
        except Exception as e:
            msg = f"校验git出错,请人工确认git已经安装：{e}"
            logger.error(msg)
            await updatePlugin.finish(msg)

        # git克隆命令
        cmd = f'''cd {plugin_folder_path} && git clone {url}'''
        try:
            stdout, stderr, result = run_cmd(cmd, sys)
            if result == 0:
                # 检查插件目录下是否有load_plugins命令
                plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
                if os.path.exists(plugin_init):
                    try:  # 替换加载命令
                        change_load_commond(plugin_folder, plugin_name, plugin_init)
                    except Exception as e:
                        msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                        logger.error(msg)
                        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                        await updatePlugin.finish(MessageSegment.image(pic))
                await updatePlugin.finish(f"{url}安装成功，请检查依赖并重启真寻。")
            else:
                pic = await text_to_pic(text=f"{url}安装失败：\n{stderr}")  # 日志转图片，依赖nonebot_plugin_htmlrender
                await updatePlugin.finish(MessageSegment.image(pic))
        except FinishedException:
            return
        except Exception as e:
            pic = await text_to_pic(
                text=f"{url}安装失败：\n{e}\n{traceback.format_exc()}")  # 日志转图片，依赖nonebot_plugin_htmlrender
            await updatePlugin.finish(MessageSegment.image(pic))


# 安装插件
@installPlugin.handle()
async def _(arg: Message = CommandArg()):
    sys = platform.system().lower()
    # 判断操作系统
    if sys not in support_sys:
        await installPlugin.finish(f"目前暂未适配{sys}系统")

    # 获取仓库地址
    url = arg.extract_plain_text().strip()
    if not url:  # 不存在仓库地址
        await installPlugin.finish(
            "未提供插件仓库地址；示例：安装插件https://github.com/CRAZYShimakaze/zhenxun_extensive_plugin")
    elif not url.startswith("https://github.com/"):
        await installPlugin.finish("目前仅支持github仓库")
    owner, repo, branch, plugin_name, part_flag, upper_path = get_url_info(url)
    '''
    # 移除末尾.git    
    elif url.endswith(".git"):
        url = url[:-4]
    url_list = url.split('/')

    part_flag = len(url_list) > 5
    # 插件名
    plugin_name = url_list[-1]
    # 仓库作者
    owner = url_list[3]
    # 仓库名（完成版下等于插件名）
    repo = url_list[4]
    '''

    # 获取bot.py文件
    bot_path = Config.get_config("plugin_manager", "BOTPATH")  # 读取配置文件
    if not bot_path:
        logger.warning("未配置BOTPATH，将从当前目录上两级寻找bot.py")
        bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    bot_file = os.path.join(bot_path, 'bot.py')
    if not os.path.exists(bot_file):
        await installPlugin.finish(f"未找到{bot_file}文件，请检查BOTPATH配置")

    # 插件安装文件夹
    plugin_folder = Config.get_config("plugin_manager", "PLUGINFOLDER")  # 读取配置文件
    # 插件安装文件夹路径
    plugin_folder_path = os.path.join(bot_path, plugin_folder)

    # 检查插件是否已安装
    if os.path.exists(os.path.join(plugin_folder_path, plugin_name)):
        await installPlugin.finish(f"已安装插件{plugin_name}")

    # 检查插件目录是否被加载
    # TODO 已知如果该行代码被注释，可能导致误判
    try:
        with open(bot_file, "r", encoding="utf8") as rf:
            data = rf.read()
        regex = re.compile(rf'nonebot.load_plugins\([\'\"]{plugin_folder}[\'\"]\)')
        if not regex.search(data):
            msg = f'bot.py中未加载插件目录{plugin_folder}，请修改bot.py或检查PLUGINFOLDER配置'
            logger.warning(msg)
            await installPlugin.send(msg)
    except Exception as e:
        msg = f"未能检查bot.py中是否加载插件目录{plugin_folder}，请手动检查：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await installPlugin.send(MessageSegment.image(pic))

    # 创建插件目录
    if not os.path.exists(plugin_folder_path):
        os.makedirs(plugin_folder_path)
        # 设置权限755
        os.chmod(plugin_folder_path, 0o0755)
        logger.info(f"创建插件目录{plugin_folder_path}")

    git_flag = Config.get_config("plugin_manager", "USEGIT")  # 读取配置文件
    '''检查网址是完整git还是git下某一层目录
       完整git:  https://github.com/KarisAya/nonebot_plugin_groupmate_waifu
       目录git:  https://github.com/CRAZYShimakaze/zhenxun_extensive_plugin/tree/main/24_point
    '''

    # 下载git下某一层目录
    if part_flag:
        # 获取待下载的仓库路径 #TODO 已知如果len(url_list)大于7，会导致截取的path成为 xxxx/[插件名]，
        # 下载下来的文件结构会变成[插件目录]/xxxx/[插件名]，导致插件加载失败，但目前未发现相关案例，暂不兼容
        '''
        path = ""
        for i in range(7, len(url_list)):
            path += url_list[i] + "/"
        path = path[:-1]
        '''
        # upper_path = '/'.join(url_list[7:-1])
        # branch = re.search(r'tree/(.*?)/', url).group(1)
        index_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{upper_path}/{plugin_name}?ref={branch}"
        try:
            if not await getfiles(index_url, plugin_folder_path, upper_path):
                raise
            # 检查插件目录下是否有load_plugins命令
            plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
            if os.path.exists(plugin_init):
                try:
                    # 替换加载命令
                    change_load_commond(plugin_folder, plugin_name, plugin_init)
                except Exception as e:
                    msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                    logger.error(msg)
                    pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                    return await installPlugin.send(MessageSegment.image(pic))
            return await installPlugin.send(f"{url}安装成功，请检查依赖并重启真寻。")
        except Exception as e:
            pic = await text_to_pic(
                text=f"{url}安装失败：\n{e}\n{traceback.format_exc()}")  # 日志转图片，依赖nonebot_plugin_htmlrender
            await installPlugin.finish(MessageSegment.image(pic))
    # 不使用git下载完整仓库
    elif not git_flag:
        # 下载仓库
        result = await get_repo(owner, repo, plugin_folder_path, plugin_name)
        # 下载失败
        if result["retcode"] != 0:
            pic = await text_to_pic(text=result["msg"])  # 日志转图片，依赖nonebot_plugin_htmlrender
            await installPlugin.finish(MessageSegment.image(pic))
        # 检查插件目录下是否有load_plugins命令
        plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
        if os.path.exists(plugin_init):
            try:
                # 替换加载命令
                change_load_commond(plugin_folder, plugin_name, plugin_init)
            except Exception as e:
                msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                logger.error(msg)
                pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                await installPlugin.finish(MessageSegment.image(pic))
        await installPlugin.finish(f"{url}安装成功，请检查依赖并重启真寻。")
        # git -clone下载完整git
    else:
        # 校验git
        try:
            stdout, stderr, result = run_cmd("git --version", sys)
            if result != 0:
                if 'windows' == sys:
                    msg = "系统未安装git，请人工安装：https://git-scm.com/download/win"
                elif 'linux' == sys:
                    msg = "系统未安装git，请人工安装：https://git-scm.com/download/linux"
                else:
                    msg = "系统未安装git，请人工安装"
                await installPlugin.finish(msg)
        except FinishedException:
            return
        except Exception as e:
            msg = f"校验git出错,请人工确认git已经安装：{e}"
            logger.error(msg)
            await installPlugin.finish(msg)

        # git克隆命令
        cmd = f'''cd {plugin_folder_path} && git clone {url}'''
        try:
            stdout, stderr, result = run_cmd(cmd, sys)
            if result == 0:
                # 检查插件目录下是否有load_plugins命令
                plugin_init = os.path.join(plugin_folder_path, plugin_name, "__init__.py")
                if os.path.exists(plugin_init):
                    try:  # 替换加载命令
                        change_load_commond(plugin_folder, plugin_name, plugin_init)
                    except Exception as e:
                        msg = f"替换加载命令出错：{e}\n{traceback.format_exc()}"
                        logger.error(msg)
                        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
                        await installPlugin.finish(MessageSegment.image(pic))
                await installPlugin.finish(f"{url}安装成功，请检查依赖并重启真寻。")
            else:
                pic = await text_to_pic(text=f"{url}安装失败：\n{stderr}")  # 日志转图片，依赖nonebot_plugin_htmlrender
                await installPlugin.finish(MessageSegment.image(pic))
        except FinishedException:
            return
        except Exception as e:
            pic = await text_to_pic(
                text=f"{url}安装失败：\n{e}\n{traceback.format_exc()}")  # 日志转图片，依赖nonebot_plugin_htmlrender
            await installPlugin.finish(MessageSegment.image(pic))


# 下载依赖
@installDependence.handle()
async def _(arg: Message = CommandArg()):
    sys = platform.system().lower()
    # 判断操作系统
    if sys not in support_sys:
        await installPlugin.finish(f"目前暂未适配{sys}系统")

    # 获取依赖
    dependence = arg.extract_plain_text().strip()
    if not dependence:  # 未输入依赖
        await installDependence.finish("未提供需安装的依赖；示例：下载依赖pillow")
    dependence = dependence.replace(" ", "")
    # 覆盖安装
    override_flag = False
    if dependence.startswith("覆盖"):
        override_flag = True
        dependence = dependence.replace("覆盖", "")
    # 依赖名称 不带版本信息
    dependence_name = dependence.split("=")[0].strip()
    # 是否指定版本
    version = dependence.split("=")[1].strip() if len(dependence.split("=")) == 2 else None

    # 校验pip
    pip = Config.get_config("plugin_manager", "PIPCMD")  # 读取配置文件
    try:
        stdout, stderr, result = run_cmd(f"{pip} list", sys)
        if result != 0:
            msg = f"系统未找到命令{pip}，请检查PIPCMD配置{stderr}"
            await installDependence.finish(msg)
        # 检查是否需要更新pip
        if stderr and ("To update" in stderr):
            update_pip_flag = Config.get_config("plugin_manager", "ISUPDATEPIP")  # 读取配置文件
            if update_pip_flag:
                await installDependence.send("检测到新版本pip，正在升级pip")
                # 更新pip
                upd_cmd = re.search(r"To update, run: \w+", stderr).group().replace("To update, run: ", "")
                try:
                    stdout2, stderr2, result2 = run_cmd(upd_cmd, sys)
                    if result2 != 0:
                        msg = f"pip更新失败，请人工处理：{stderr2}"
                        logger.error(msg)
                        await installDependence.finish(msg)
                except FinishedException:
                    return
                except Exception as e:
                    msg = f"pip更新失败，请人工处理：\n{e}\n{traceback.format_exc()}"
                    logger.error(msg)
                    await installDependence.finish(msg)
            else:
                await installDependence.send("检测到新版本pip，如需更新pip，请手动执行更新命令，或修改ISUPDATEPIP配置")
                # 检查插件是否已经安装
        for piplist in stdout.split('\n'):
            if len(piplist.split()) < 2:
                continue

            if dependence_name == piplist.split()[0].lower() and (not version):
                # 已经安装依赖且未指定依赖版本
                msg = f"已安装{piplist.split()[0]},当前版本{piplist.split()[1]}"
                logger.warning(msg)
                await installDependence.finish(msg)
            elif dependence_name.lower() == piplist.split()[0].lower() and version and (version == piplist.split()[1]):
                # 已经安装依赖且指定的依赖版本与已安装的版本一致
                msg = f"已安装{piplist.split()[0]},当前版本{piplist.split()[1]}"
                logger.warning(msg)
                await installDependence.finish(msg)
            elif dependence_name.lower() == piplist.split()[0].lower() and (not override_flag):
                # 已经安装依赖且指定的依赖版本与已安装的版本不一致,且未要求覆盖安装
                msg = f"已安装{piplist.split()[0]},当前版本{piplist.split()[1]}，如需覆盖版本，请回复  下载依赖覆盖{dependence}"
                logger.warning(msg)
                await installDependence.finish(msg)
            elif dependence_name.lower() == piplist.split()[0].lower() and override_flag:
                # 已经安装依赖且指定的依赖版本与已安装的版本不一致，但要求覆盖安装
                msg = f"已安装{piplist.split()[0]},当前版本{piplist.split()[1]}，将覆盖安装{version}版本"
                logger.warning(msg)
                await installDependence.send(msg)
    except FinishedException:
        return
    except Exception as e:
        msg = f"系统未找到命令{pip}，请检查PIPCMD配置：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        await installDependence.finish(msg)

    # 安装依赖命令
    install_cmd = f'{pip} install {dependence.replace("=", "==") if version else dependence}'

    # 校验poetry
    poetry_flag = Config.get_config("plugin_manager", "ISPOETRY")  # 读取配置文件
    if poetry_flag:
        try:
            stdout, stderr, result = run_cmd(f"poetry --version", sys)
            if result != 0:
                msg = "系统未找到命令poetry，请确认是否使用poetry虚拟环境并检查ISPOETRY配置"
                logger.error(msg)
                await installDependence.finish(msg)
        except FinishedException:
            return
        except Exception as e:
            msg = f"系统未找到命令poetry，请确认是否使用poetry虚拟环境并检查ISPOETRY配置：\n{e}\n{traceback.format_exc()}"
            logger.error(msg)
            await installDependence.finish(msg)
        # 获取poetry环境所在目录
        bot_path = Config.get_config("plugin_manager", "BOTPATH")  # 读取配置文件
        if not bot_path:
            logger.warning("未配置BOTPATH，将从当前目录上两级寻找bot.py")
            bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        # 更新安装命令进入虚拟环境步骤
        install_cmd = f'cd {bot_path} && poetry run {install_cmd}'
    try:
        # 安装依赖
        stdout, stderr, result = run_cmd(install_cmd, sys)
        if result == 0:
            env = "在poetry环境" if poetry_flag else ""
            msg = f"{dependence_name}{env}安装成功：\n{stdout}"
            pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
            await installDependence.finish(MessageSegment.image(pic))
        msg = f"{dependence_name}安装失败：\n{stderr}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await installDependence.finish(MessageSegment.image(pic))
    except FinishedException:
        return
    except Exception as e:
        msg = f"{dependence_name}安装异常：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await installDependence.finish(MessageSegment.image(pic))


# 更新依赖
@updateDependence.handle()
async def _(arg: Message = CommandArg()):
    sys = platform.system().lower()
    # 判断操作系统
    if sys not in support_sys:
        await installPlugin.finish(f"目前暂未适配{sys}系统")

    # 获取依赖
    dependence = arg.extract_plain_text().strip()
    if not dependence:  # 未输入依赖
        await installDependence.finish("未提供需更新的依赖；示例：更新依赖pillow")
    dependence = dependence.replace(" ", "")

    # 校验pip
    pip = Config.get_config("plugin_manager", "PIPCMD")  # 读取配置文件
    try:
        stdout, stderr, result = run_cmd(f"{pip} list", sys)
        if result != 0:
            msg = f"系统未找到命令{pip}，请检查PIPCMD配置{stderr}"
            await installDependence.finish(msg)
        # 检查是否需要更新pip
        if stderr and ("To update" in stderr):
            update_pip_flag = Config.get_config("plugin_manager", "ISUPDATEPIP")  # 读取配置文件
            if update_pip_flag:
                await installDependence.send("检测到新版本pip，正在升级pip")
                # 更新pip
                upd_cmd = re.search(r"To update, run: \w+", stderr).group().replace("To update, run: ", "")
                try:
                    stdout2, stderr2, result2 = run_cmd(upd_cmd, sys)
                    if result2 != 0:
                        msg = f"pip更新失败，请人工处理：{stderr2}"
                        logger.error(msg)
                        await installDependence.finish(msg)
                except FinishedException:
                    return
                except Exception as e:
                    msg = f"pip更新失败，请人工处理：\n{e}\n{traceback.format_exc()}"
                    logger.error(msg)
                    await installDependence.finish(msg)
            else:
                await installDependence.send("检测到新版本pip，如需更新pip，请手动执行更新命令，或修改ISUPDATEPIP配置")
    except FinishedException:
        return
    except Exception as e:
        msg = f"系统未找到命令{pip}，请检查PIPCMD配置：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        await installDependence.finish(msg)

    # 更新依赖命令
    install_cmd = f'{pip} install --upgrade {dependence}'

    # 校验poetry
    poetry_flag = Config.get_config("plugin_manager", "ISPOETRY")  # 读取配置文件
    if poetry_flag:
        try:
            stdout, stderr, result = run_cmd(f"poetry --version", sys)
            if result != 0:
                msg = "系统未找到命令poetry，请确认是否使用poetry虚拟环境并检查ISPOETRY配置"
                logger.error(msg)
                await installDependence.finish(msg)
        except FinishedException:
            return
        except Exception as e:
            msg = f"系统未找到命令poetry，请确认是否使用poetry虚拟环境并检查ISPOETRY配置：\n{e}\n{traceback.format_exc()}"
            logger.error(msg)
            await installDependence.finish(msg)
        # 获取poetry环境所在目录
        bot_path = Config.get_config("plugin_manager", "BOTPATH")  # 读取配置文件
        if not bot_path:
            logger.warning("未配置BOTPATH，将从当前目录上两级寻找bot.py")
            bot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        # 更新命令进入虚拟环境步骤
        install_cmd = f'cd {bot_path} && poetry run {install_cmd}'
    try:
        # 更新依赖
        stdout, stderr, result = run_cmd(install_cmd, sys)
        if result == 0:
            env = "在poetry环境" if poetry_flag else ""
            msg = f"{dependence}{env}更新成功：\n{stdout}"
            pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
            await installDependence.finish(MessageSegment.image(pic))
        msg = f"{dependence}更新失败：\n{stderr}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await installDependence.finish(MessageSegment.image(pic))
    except FinishedException:
        return
    except Exception as e:
        msg = f"{dependence}更新异常：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        pic = await text_to_pic(text=msg)  # 日志转图片，依赖nonebot_plugin_htmlrender
        await installDependence.finish(MessageSegment.image(pic))


# 执行shell命令  returncode=0成功，非零失败，报错失败
def run_cmd(command: str, sys):
    if "windows" == sys:
        command = command.split()
    ret = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = ret.communicate()
    return stdout, stderr, ret.returncode


# 递归下载文件
async def getfiles(url, plugin_folder_path, upper_path):
    # 获取资源下载信息
    max_retry = 3
    while max_retry:
        try:
            res = await AsyncHttpx.get(url, timeout=10, headers=header)
        except:
            max_retry -= 1
            await asyncio.sleep(0.5)
            logger.info(f'重试获取{url}第{3 - max_retry}次')
        else:
            break
    else:
        return False
    res.encoding = "utf8"
    data = json.loads(res.text)
    for i in data:
        # 检查文件类型，文件夹需要递归下载子文件
        if i["type"] == "dir":
            if not await getfiles(i["url"], plugin_folder_path, upper_path):
                return False
        elif i["type"] == "file":
            max_retry = 3
            relative_path = copy.deepcopy(i["path"])
            while (max_retry and not await AsyncHttpx.download_file("https://ghproxy.com/" + i["download_url"],
                                                                    plugin_folder_path + relative_path.replace(
                                                                        upper_path, '',
                                                                        1),
                                                                    headers=header,
                                                                    timeout=10)):
                await asyncio.sleep(0.5)
                max_retry -= 1
                logger.info(f'重试下载{i["download_url"]}第{3 - max_retry}次')

            if not max_retry:
                return False
        else:
            # 非预期的文件类型跳过处理
            logger.error(f'未知的文件类型{i}')
            return False
    return True


# 下载完整仓库
async def get_repo(owner, repo, plugin_folder_path, plugin_name, branch=None, retry=False):
    msg = ""
    try:
        # 获取默认分支
        if not branch:
            branch = await get_branch(owner, repo)
        # 下载链接
        url = f'https://codeload.github.com/{owner}/{repo}/zip/{branch}'
        # 下载目录
        filename = os.path.join(plugin_folder_path, plugin_name)
        zipfile_name = filename + '.zip'
        data = await AsyncHttpx.get(url)
        if str(data) == '<Response [404 Not Found]>':
            msg = f"未找到压缩包文件，分支{branch}可能不存在"
            logger.warning(msg)
            raise FinishedException(msg)
        # 写压缩包
        with open(zipfile_name, 'wb') as f:
            f.write(data.read())
        # 解压插件包
        try:
            with zipfile.ZipFile(zipfile_name, 'r') as f:
                f.extractall(plugin_folder_path)
        except Exception as e:
            msg = f"解压{zipfile_name}失败，请手动处理：\n{e}\n{traceback.format_exc()}"
            logger.warning(msg)
            return {"retcode": 1, "msg": msg}
            # 检查解压文件夹
        unzip_folder = f'{filename}-{branch}'
        if not os.path.exists(unzip_folder):
            msg = f"{plugin_name}安装失败：解压{zipfile_name}文件后未能发现文件夹{unzip_folder}"
            logger.error(msg)
            return {"retcode": 4, "msg": msg}
            # 删除压缩包
        try:
            os.unlink(zipfile_name)
        except Exception as e:
            msg = f"删除压缩包{zipfile_name}失败，请手动处理：\n{e}\n{traceback.format_exc()}"
            logger.warning(msg)
        # 重命名文件夹
        try:
            os.rename(unzip_folder, filename)
        except Exception as e:
            msg += f"重命名{unzip_folder}失败，请手动处理：\n{e}\n{traceback.format_exc()}"
            logger.warning(msg)
            return {"retcode": 5, "msg": msg}
        msg += f"插件{plugin_name}下载成功"
        logger.info(msg)
        return {"retcode": 0, "msg": msg}
    except FinishedException as e:
        # 获取分支重试后依然下载失败
        if retry:
            msg += f"{plugin_name}安装失败：\n{e}\n{traceback.format_exc()}"
            logger.error(msg)
            return {"retcode": 2, "msg": msg}
        try:
            # 尝试获取默认分支后重试            
            default_branch = await get_branch(owner, repo)
            # 重试
            await get_repo(owner, repo, plugin_folder_path, plugin_name, branch=default_branch, retry=True)
        except Exception as e:
            msg += f"{plugin_name}安装失败：\n{e}\n{traceback.format_exc()}"
            logger.error(msg)
            return {"retcode": 3, "msg": msg}
    except Exception as e:
        msg += f"{plugin_name}安装失败：\n{e}\n{traceback.format_exc()}"
        logger.error(msg)
        return {"retcode": 9, "msg": msg}

    # 获取仓库的默认分支


async def get_branch(owner, repo):
    # 尝试api方式获取
    try:
        res = await AsyncHttpx.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=30)
        res.encoding = "utf8"
        data = json.loads(res.text)
        return data["default_branch"]
    except Exception:
        # 尝试网页获取
        from fake_useragent import UserAgent
        headers = {'User-Agent': UserAgent().random, 'Host': 'github.com'}
        response = await AsyncHttpx.get(f'https://github.com/{owner}/{repo}', headers=headers)
        pattern = '<span class="css-truncate-target" data-menu-button>(.*?)</span>'
        return re.findall(pattern, str(response.read()))[-1]


def change_load_commond(plugin_folder, plugin_name, plugin_init):
    new_load_str = f'''nonebot.load_plugins("{plugin_folder}/{plugin_name}")'''
    regex = re.compile(rf'nonebot.load_plugins\([\'\"]\w+/{plugin_name}[\'\"]\)')
    # 替换加载命令
    with open(plugin_init, "r", encoding="utf-8") as f1, open(f"{plugin_init}.bak", "w", encoding="utf-8") as f2:
        for line in f1:
            f2.write(regex.sub(new_load_str, line))
    os.remove(plugin_init)
    os.rename(f"{plugin_init}.bak", plugin_init)


def get_url_info(url):
    para = {}
    u = url.strip("/").replace(".git", "") + '/'
    reg = "https://github.com/(.*?)/(.*?)/(tree)?(.*)"
    rs = re.match(reg, u)
    para["owner"] = rs.group(1)
    para["repo"] = rs.group(2)
    if rs.group(3):
        path_info = rs.group(4).strip('/')
        path_info = path_info.split('/')
        para["branch"] = path_info[0]
        if len(path_info) == 1:
            para["plugin_name"] = para["repo"]
            para["part_flag"] = False
        else:
            para["plugin_name"] = path_info[-1]
            para["path"] = "/".join(path_info[1:-1])
            para["part_flag"] = True
    else:
        para["branch"] = ''
        para["plugin_name"] = para["repo"]
        para["part_flag"] = False
    return para["owner"], para["repo"], para["branch"], para["plugin_name"], para["part_flag"], para["path"]
