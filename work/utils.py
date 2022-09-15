from .model import Worker
from typing import Optional
from utils.data_utils import init_rank
from utils.image_utils import BuildMat

async def rank(group_id: int, itype: str, num: int) -> Optional[BuildMat]:
    all_users = await Worker.get_all_user(group_id)
    all_user_id = [user.user_qq for user in all_users]
    if itype == 'work_count':
        rank_name = '打工次数排行榜'
        all_user_data = [user.work_count for user in all_users]
    elif itype == 'time_count':
        rank_name = '打工工时（秒）排行榜'
        all_user_data = [user.time_count for user in all_users]
    elif itype == 'salary':
        rank_name = '赚取金币排行榜'
        all_user_data = [user.salary for user in all_users]
    elif itype == 'question_count':
        rank_name = '算数能手排行榜'
        all_user_data = [user.question_count for user in all_users]
    rst = None
    if all_users:
        rst = await init_rank(rank_name, all_user_id, all_user_data, group_id, num)
    return rst
