import math
from services.db_context import db
from typing import List

class Worker(db.Model):
    __tablename__ = "workers"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    question_count = db.Column(db.Integer(), default=0)  # 答对题目数
    work_count = db.Column(db.Integer(), default=0) # 打工次数
    time_count = db.Column(db.Float(), default=0) # 工时（秒）
    salary = db.Column(db.Integer(), default=0) # 工资总数

    _idx1 = db.Index("workers_group_users_idx1", "user_qq", "group_id", unique=True)

    @classmethod
    async def ensure(cls, user_qq:int,group_id:int)->"Worker":
        """
        说明:
            获取用户对象
        参数:
            :param user_qq: qq号
            :param group_id: 群号
        """
        user = (
            await cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
            .with_for_update()
            .gino.first()
        )
        return user or await cls.create(user_qq=user_qq, group_id=group_id)

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
            user = (
                await cls.query.where(
                    (cls.user_qq == user_qq) & (cls.group_id == group_id)
                )
                .with_for_update()
                .gino.first()
            )
            if not user:
                user = await cls.create(user_qq=user_qq, group_id=group_id)
            await user.update( question_count=user.question_count + num ).apply()
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
            user = (
                await cls.query.where(
                    (cls.user_qq == user_qq) & (cls.group_id == group_id)
                )
                .with_for_update()
                .gino.first()
            )
            if not user:
                user = await cls.create(user_qq=user_qq, group_id=group_id)
            await user.update( work_count=user.work_count + 1 ).apply()
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
            user = (
                await cls.query.where(
                    (cls.user_qq == user_qq) & (cls.group_id == group_id)
                )
                .with_for_update()
                .gino.first()
            )
            if not user:
                user = await cls.create(user_qq=user_qq, group_id=group_id)
            await user.update( time_count=user.time_count + times ).apply()
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
            user = (
                await cls.query.where(
                    (cls.user_qq == user_qq) & (cls.group_id == group_id)
                )
                .with_for_update()
                .gino.first()
            )
            if not user:
                user = await cls.create(user_qq=user_qq, group_id=group_id)
            await user.update( salary=user.salary + salary ).apply()
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
        users = await cls.query.where((cls.group_id == group_id)).gino.all()
        return users
