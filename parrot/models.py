# coding=utf8
import datetime
import enum

from sqlalchemy import Column, Boolean, Enum, Integer, String, DateTime, ForeignKey
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from parrot import engine

Base = declarative_base()


class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    text = Column(String(64), unique=True)
    # 音标
    phonetic_symbol = Column(String(64))
    # 示例
    use_case = Column(String)
    # 意思
    meaning = Column(String)
    # 备注
    remark = Column(String)

    created_time = Column(DateTime, default=datetime.datetime.now)
    changed_time = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)


class ReviewStage(enum.Enum):
    STAGE1 = 1
    STAGE2 = 2
    STAGE3 = 3
    STAGE4 = 4
    STAGE5 = 5


STAGE_DELTA_MAP = {
    ReviewStage.STAGE1: datetime.timedelta(days=1),
    ReviewStage.STAGE2: datetime.timedelta(days=1),
    ReviewStage.STAGE3: datetime.timedelta(days=4),
    ReviewStage.STAGE4: datetime.timedelta(days=9),
    ReviewStage.STAGE5: datetime.timedelta(days=15),
}


class ReviewStatus(enum.Enum):
    # 还未复习
    UNREVIEWED = 1
    # 已经复习过了，且结果是“知道了”
    REVIEWED = 2
    # 已经复习过了，且结果是“记住了”
    REMEMBERED = 3
    # 已经复习过了，且结果是“没记住”
    UNREMEMBERED = 4


class ReviewPlanType(enum.Enum):
    '''该条复习的类型'''
    # 提示单词来复习
    HINT_WORD = 0
    # 提示中文来复习
    HINT_MEANING = 1


class ReviewPlan(Base):
    __tablename__ = 'review_plans'
    id = Column(Integer, primary_key=True)
    # 复习计划所处的阶段，1~5
    stage = Column(Enum(ReviewStage), default=ReviewStage.STAGE1)
    # 该计划所处的状态
    status = Column(Enum(ReviewStatus), default=ReviewStatus.UNREVIEWED)
    review_plan_type = Column(
        Enum(ReviewPlanType),
        default=ReviewPlanType.HINT_WORD)
    # 要复习的时间
    time_to_review = Column(DateTime)
    # 实际被复习的时间, 复习后才有该字段
    reviewed_time = Column(DateTime)

    created_time = Column(DateTime, default=datetime.datetime.now)
    changed_time = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # foreign key
    word_id = Column(Integer, ForeignKey('words.id'))
    word = relationship("Word", back_populates="review_plans")

    def __repr__(self):
        return "< ReviewPlan(id='{}',word_id='{}')".format(self.id, self.word_id)

    @classmethod
    def generate_full_review_plan(
            cls,
            word_id,
            time_to_review,
            stage_value=ReviewStage.STAGE1.value
    ):
        hint_meaning_plan = cls(
            time_to_review=time_to_review,
            word_id=word_id,
            review_plan_type=ReviewPlanType.HINT_MEANING,
            stage=ReviewStage(stage_value),
        )
        hint_word_plan = cls(
            time_to_review=time_to_review,
            word_id=word_id,
            review_plan_type=ReviewPlanType.HINT_WORD,
            stage=ReviewStage(stage_value),
        )
        return [hint_meaning_plan, hint_word_plan]


class AddCounter(Base):
    __tablename__ = 'add_counter'
    id = Column(Integer, primary_key=True)
    # 第几次
    counter = Column(Integer, default=0)
    changed_time = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    @classmethod
    def get_counter(cls, session):
        first = session.query(AddCounter).first()
        if first is not None:
            return first
        new_one = cls(
            counter=0,
            changed_time=datetime.datetime.now())
        session.add(new_one)
        return new_one

    def incr(self):
        if self.changed_time.date() == datetime.date.today():
            self.counter += 1
        else:
            # 这里主动更新changed_time，是因为如果counter没变的
            # 话，sqlalchemy会认为不是一次更新而不执行update语句，
            # 那么配置的onupdate也不会触发。
            # 假设上一次changed_time不是今天，且counter也是1，那么
            # 就会遇到这种情况，导致counter永远是1，因为这种情况并不会
            # 真正的执行update语句。
            self.changed_time = datetime.datetime.now()
            self.counter = 1


# foreign key
Word.review_plans = relationship("ReviewPlan",
                                 order_by=ReviewPlan.id,
                                 back_populates="word")

# Base.metadata.create_all(engine)
