from bs4 import BeautifulSoup

from utils.http_utils import AsyncHttpx

url = "http://www.eclzz.fyi"


async def get_bt_info(keyword: str, page=1):
    """
    获取资源信息
    :param keyword: 关键词
    :param page: 页数
    """
    result = []
    for i in range(3):
        try:
            text = (await AsyncHttpx.get(f"{url}/s/{keyword}_rel_{page}.html", timeout=5, follow_redirects=True)).text
            if "没有找到记录！" in text:
                return result
            soup = BeautifulSoup(text, "lxml")
            break
        except:
            pass  # await asyncio.sleep(1)
    else:
        return '搜索出错,请重试!'
    item_lst = soup.find_all("div", {"class": "search-item"})
    bt_max_num = 3
    bt_max_num = bt_max_num if bt_max_num < len(item_lst) else len(item_lst)
    for item in item_lst[:bt_max_num]:
        divs = item.find_all("div")
        title = (str(divs[0].find("a").text).replace("<em>", "").replace("</em>", "").strip())
        spans = divs[2].find_all("span")
        type_ = spans[0].text
        create_time = spans[1].find("b").text
        file_size = spans[2].find("b").text
        link = ''
        for i in range(3):
            try:
                link = await get_download_link(divs[0].find("a")["href"])
                break
            except:
                pass  # await asyncio.sleep(1)
        result.append([title, type_, create_time, file_size, link])
    return result


async def get_download_link(_url: str) -> str:
    """
    获取资源下载地址
    :param _url: 链接
    """
    text = (await AsyncHttpx.get(f"{url}{_url}", follow_redirects=True)).text
    soup = BeautifulSoup(text, "lxml")
    return soup.find("a", {"id": "down-url"})["href"]
