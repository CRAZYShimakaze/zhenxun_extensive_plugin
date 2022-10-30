import itertools
import random
from io import BytesIO

from PIL import ImageFont
from PIL.Image import Image as IMG
from PIL.ImageFont import FreeTypeFont

from configs.path_config import FONT_PATH
from utils.http_utils import AsyncHttpx


async def load_font(name: str, fontsize: int) -> FreeTypeFont:
    tff_path = FONT_PATH / name
    if not tff_path.exists():
        try:
            url = "https://raw.githubusercontent.com/noneplugin/nonebot-plugin-handle/main/nonebot_plugin_handle/resources/fonts/{}".format(
                name)
            await AsyncHttpx.download_file(url, tff_path)
        except:
            url = "https://ghproxy.com/https://raw.githubusercontent.com/noneplugin/nonebot-plugin-handle/main/nonebot_plugin_handle/resources/fonts/{}".format(
                name)
            await AsyncHttpx.download_file(url, tff_path)
    return ImageFont.truetype(str(tff_path), fontsize, encoding="utf-8")


def twentyfour(cards):
    bds_list = []
    for nums in itertools.permutations(cards):  # 四个数
        for ops in itertools.product('+-*/', repeat=3):  # 三个运算符(可重复！)
            # 构造三种中缀表达式 (bsd)
            bds1 = '({0}{4}{1}){5}({2}{6}{3})'.format(*nums,
                                                      *ops)  # (a+b)*(c-d)
            bds2 = '(({0}{4}{1}){5}{2}){6}{3}'.format(*nums, *ops)  # (a+b)*c-d
            bds3 = '{0}{4}({1}{5}({2}{6}{3}))'.format(*nums,
                                                      *ops)  # a/(b-(c/d))
            for bds in [bds1, bds2, bds3]:  # 遍历
                try:
                    if abs(eval(bds) - 24.0) < 1e-10 and abs(
                            eval(bds.replace('/', '//')) -
                            24.0) < 1e-10:  # eval函数
                        bds_list.append(bds)
                except ZeroDivisionError:  # 零除错误！
                    continue
    if (len(bds_list) < 30) and (len(bds_list) > 0):
        return bds_list[random.randint(0, len(bds_list) - 1)]
    else:
        return False


def random_question():
    while 1:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        c = random.randint(1, 9)
        d = random.randint(1, 9)
        able = twentyfour([a, b, c, d])
        if able:
            break
    return [str(a), str(b), str(c), str(d)], able


# 检查正确性
def check_result(submit: str, question) -> bool:
    try:
        if eval(submit) == 24:
            num = submit.replace("+", ",").replace("-", ",").replace(
                "*", ",").replace("/", ",").replace("(", ",").replace(")", ",")
            num = num.split(",")
            if str(question[0]) in num:
                num.remove(str(question[0]))
                if str(question[1]) in num:
                    num.remove(str(question[1]))
                    if str(question[2]) in num:
                        num.remove(str(question[2]))
                        if str(question[3]) in num:
                            num.remove(str(question[3]))
                            while '' in num:
                                num.remove('')
                            if not num:
                                return True
        return False
    except:
        return False


def save_jpg(frame: IMG) -> BytesIO:
    output = BytesIO()
    frame = frame.convert("RGB")
    frame.save(output, format="jpeg")
    return output
