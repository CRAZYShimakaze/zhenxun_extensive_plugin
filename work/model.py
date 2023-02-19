from tortoise import fields
from services.db_context import Model
from typing import List

class Worker(Model):

    class Meta:
        table = "workers"
        table_description = "打工数据表"
        unique_together = ("user_qq", "group_id")

    id = fields.IntField(pk=True, generated=True, auto_increment=True) # 自增id
    user_qq = fields.BigIntField() # 用户id
    group_id = fields.BigIntField() # 群聊id
    question_count = fields.IntField(default=0) # 答对题目数
    work_count = fields.IntField(default=0) # 打工次数
    time_count = fields.FloatField(default=0) # 工时（秒）
    salary = fields.FloatField(default=0) # 工资总数



    @classmethod
    async def ensure(cls, user_qq:int,group_id:int)->"Worker":
        """
        说明:
            获取用户对象
        参数:
            :param user_qq: qq号
            :param group_id: 群号
        """
        user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
        return user

    @classmethod
    async def add_question_count(cls, user_qq: int, group_id: int, num:int) -> bool:
        """
        说明:
            添加用户答对题目数
        说明:
            :param user_qq: qq号
            :param group_id: 群号
            :num: 答对题目数
        """
        try:
            user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
            user.question_count = user.question_count + num
            await user.save(update_fields=["question_count", ])
            return True
        except Exception:
            return False

    @classmethod
    async def add_work_count(cls, user_qq: int, group_id: int) -> bool:
        """
        说明:
            添加用户打工次数（调用一次就+1）
        说明:
            :param user_qq: qq号
            :param group_id: 群号
        """
        try:
            user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
            user.work_count = user.work_count + 1
            await user.save(update_fields=["work_count", ])
            return True
        except Exception:
            return False

    @classmethod
    async def add_time_count(cls, user_qq: int, group_id: int, times: int) -> bool:
        """
        说明:
            添加用户工时
        说明:
            :param user_qq: qq号
            :param group_id: 群号
            :times: 此次工作耗时（秒）
        """
        try:
            user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
            user.time_count = user.time_count + times
            await user.save(update_fields=["time_count", ])
            return True
        except Exception:
            return False

    @classmethod
    async def add_salary(cls, user_qq: int, group_id: int, salary: int) -> bool:
        """
        说明:
            添加用户工资
        说明:
            :param user_qq: qq号
            :param group_id: 群号
            :salary: 此次工作所得工资
        """
        try:
            user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
            user.salary = user.salary + salary
            await user.save(update_fields=["salary", ])
            return True
        except Exception:
            return False

    @classmethod
    async def get_all_user(cls, group_id: int) -> List["Worker"]:
        """
        说明:
            获取该群所有用户对象
        参数:
        :param group_id: 群号
        """
        users = await cls.all(group_id = group_id)
        return users
