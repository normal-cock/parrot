# coding=utf8
import datetime
import enum

from sqlalchemy import Column, Boolean, Enum, Integer, String, DateTime, ForeignKey
from sqlalchemy import text
from sqlalchemy.orm import relationship

from parrot_v2 import DEBUG
from parrot_v2.model import Base


class Word(Base):
    __tablename__ = 'word'
    id = Column(Integer, primary_key=True)
    text = Column(String(64), unique=True)
    created_time = Column(DateTime, default=datetime.datetime.now)
    changed_time = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    def get_other_meaning_without_review_plan(self):
        other_meanings = []
        for meaning in self.meanings:
            if meaning.review_plans.filter(
                    ReviewPlan.time_to_review >= datetime.datetime.today().date()
            ).count() == 0:
                other_meanings.append(meaning)
        return other_meanings

    @classmethod
    def new_word(cls, text, phonetic_symbol, meaning, use_case, remark):
        word = Word(
            text=text,
        )
        word.meanings = []
        Meaning.new_meaning(
            word, phonetic_symbol, meaning, use_case, remark)

        return word


class Meaning(Base):
    __tablename__ = 'meaning'
    id = Column(Integer, primary_key=True)
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

    # foreign key
    word_id = Column(Integer, ForeignKey('word.id'))
    word = relationship("Word", back_populates="meanings")

    def modify_meaning(self, phonetic_symbol, meaning, use_case, remark):
        self.phonetic_symbol = phonetic_symbol
        self.meaning = meaning
        self.use_case = use_case
        self.remark = remark
        self.unremember()

    def unremember(self):
        self.review_plans.filter(ReviewPlan.status == ReviewStatus.UNREVIEWED).update(
            {ReviewPlan.status: ReviewStatus.UNREMEMBERED},
            synchronize_session='fetch',
        )
        ReviewPlan.generate_a_plan(self)

    @classmethod
    def new_meaning(cls, word, phonetic_symbol, meaning, use_case, remark):
        meaning = Meaning(
            word_id=word.id,
            phonetic_symbol=phonetic_symbol,
            meaning=meaning,
            use_case=use_case,
            remark=remark,
        )
        meaning.review_plans = []
        ReviewPlan.generate_a_plan(meaning)

        word.meanings.append(meaning)
        return meaning


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
    '''1是未完结状态, 2~4都是完结状态'''
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
    __tablename__ = 'review_plan'
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
    meaning_id = Column(Integer, ForeignKey('meaning.id'))
    meaning = relationship("Meaning", back_populates="review_plans")

    def __repr__(self):
        return "< ReviewPlan(id='{}',meaning_id='{}')".format(self.id, self.meaning_id)

    def complete(self, final_status_value, is_gen_new_plan):
        if final_status_value not in [2, 3, 4]:
            exit("invaid final status({}) for review_plan".format(final_status_value))
        self.status = ReviewStatus(final_status_value)
        self.reviewed_time = datetime.datetime.now()
        if is_gen_new_plan:
            return self.gen_next_plan()
        return []

    def gen_next_plan(self):
        new_plans = []
        if (self.stage.value != ReviewStage.STAGE5.value
                and self.status != ReviewStatus.UNREVIEWED):
            if (self.status == ReviewStatus.REMEMBERED
                    and self.stage.value < ReviewStage.STAGE4.value):
                # 记住了，且 stage 小于 4，stage+2
                # 大于等于4时，就走正常的流程
                new_stage = ReviewStage(self.stage.value + 2)
            elif self.status == ReviewStatus.UNREMEMBERED:
                # 没记住，重新从 STAGE1 开始
                new_stage = ReviewStage.STAGE1
                new_plans = ReviewPlan.generate_a_plan(self.meaning, new_stage)
            else:
                # 正常流程，stage+1
                new_stage = ReviewStage(self.stage.value + 1)
            new_plans = ReviewPlan.generate_a_plan(self.meaning, new_stage)
        return new_plans

    @classmethod
    def generate_a_plan(
            cls,
            meaning,
            stage=ReviewStage.STAGE1
    ):
        time_to_review = (
            datetime.datetime.now() +
            STAGE_DELTA_MAP[stage]
        )
        if DEBUG:
            time_to_review = datetime.datetime.now()

        hint_meaning_plan = cls(
            meaning_id=meaning.id,
            time_to_review=time_to_review,
            review_plan_type=ReviewPlanType.HINT_MEANING,
            stage=stage,
        )
        hint_word_plan = cls(
            meaning_id=meaning.id,
            time_to_review=time_to_review,
            review_plan_type=ReviewPlanType.HINT_WORD,
            stage=stage,
        )
        meaning.review_plans.append(hint_meaning_plan)
        meaning.review_plans.append(hint_word_plan)
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
Word.meanings = relationship("Meaning",
                             back_populates="word",
                             lazy='dynamic')

Meaning.review_plans = relationship("ReviewPlan",
                                    back_populates="meaning",
                                    lazy='dynamic')

# Base.metadata.create_all(engine)
