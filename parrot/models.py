# coding=utf8
import datetime
import enum

from sqlalchemy import Column, Boolean, Enum, Integer, String, DateTime, ForeignKey
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
    changed_time = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)


class ReviewStage(enum.Enum):
    STAGE1 = 1
    STAGE2 = 2
    STAGE3 = 3
    STAGE4 = 4
    STAGE5 = 5

STAGE_DELTA_MAP = {
    ReviewStage.STAGE1:datetime.timedelta(days=1),
    ReviewStage.STAGE2:datetime.timedelta(days=1),
    ReviewStage.STAGE3:datetime.timedelta(days=4),
    ReviewStage.STAGE4:datetime.timedelta(days=9),
    ReviewStage.STAGE5:datetime.timedelta(days=15),
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

class ReviewPlan(Base):
    __tablename__ = 'review_plans'
    id = Column(Integer, primary_key=True)
    # 复习计划所处的阶段，1~5
    stage = Column(Enum(ReviewStage), default=ReviewStage.STAGE1)
    # 该计划所处的状态
    status = Column(Enum(ReviewStatus), default=ReviewStatus.UNREVIEWED)
    # 要复习的时间
    time_to_review = Column(DateTime)
    # 实际被复习的时间, 复习后才有该字段
    reviewed_time = Column(DateTime)

    created_time = Column(DateTime, default=datetime.datetime.now)
    changed_time = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # foreign key
    word_id = Column(Integer, ForeignKey('words.id'))
    word = relationship("Word", back_populates="review_plans")

    def __repr__(self):
        return "< ReviewPlan(id='{}',word_id='{}')".format(self.id, self.word_id)

# foreign key
Word.review_plans = relationship("ReviewPlan", 
    order_by=ReviewPlan.id, 
    back_populates="word")

# Base.metadata.create_all(engine)
