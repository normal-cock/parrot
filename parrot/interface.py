# coding=utf8
import datetime

from sqlalchemy.orm import joinedload

from parrot import Session
from parrot.models import Word, ReviewPlan, ReviewStatus, ReviewStage, STAGE_DELTA_MAP

def get_word(text):
    '''根据text获取库里的单词'''
    session = Session()
    word = session.query(Word).filter(Word.text==text).one_or_none()
    return word

def add_word(text, phonetic_symbol, meaning, use_case, remark):
    '''添加单词'''
    session = Session()
    word = session.query(Word).filter(Word.text==text).one_or_none()
    if word:
        word.phonetic_symbol = phonetic_symbol
        word.meaning = meaning
        word.use_case = use_case
        word.remark = remark
        last_review_plan = session.query(
            ReviewPlan
        ).filter(
            ReviewPlan.word_id==word.id
        ).order_by(ReviewPlan.time_to_review.desc()).first()
        last_review_plan.status = ReviewStatus.UNREMEMBERED
        new_review_plan = ReviewPlan(
            time_to_review=datetime.datetime.now() +
                   STAGE_DELTA_MAP[ReviewStage.STAGE1],
            word_id = word.id
        )
        session.add(new_review_plan)
    else:
        word = Word(
            text=text, 
            phonetic_symbol=phonetic_symbol, 
            meaning=meaning, 
            use_case=use_case,
            remark=remark)
        word.review_plans = [
            ReviewPlan(time_to_review=
                datetime.datetime.now()+STAGE_DELTA_MAP[ReviewStage.STAGE1])
        ]
        session.add(word)
    session.commit()
    return True

def begin_to_review(begin_time, end_time):
    '''
    开始复习单词，生成器
    begin_time 和 end_time 分别为要复习的复习计划的 time_to_review 范围
    '''
    session = Session()
    for review_plan in session.query(ReviewPlan).options(
                joinedload(ReviewPlan.word)
            ).filter(
                ReviewPlan.time_to_review>=begin_time, 
                ReviewPlan.time_to_review<=end_time,
                ReviewPlan.status == ReviewStatus.UNREVIEWED
            ).order_by(ReviewPlan.time_to_review).all():
        result = yield review_plan
        review_plan.status = ReviewStatus(result+1)
        new_plan = _generate_next_plan(review_plan)
        if new_plan:
            session.add(new_plan)
        session.commit()

def _generate_next_plan(review_plan):
    new_plan = None
    if (review_plan.stage.value != ReviewStage.STAGE5.value 
            and review_plan.status != ReviewStatus.UNREVIEWED):
        if (review_plan.status == ReviewStatus.REMEMBERED 
                and review_plan.stage.value < ReviewStage.STAGE4.value):
            # 记住了，且 stage 小于 4
            # 大于等于4时，就走正常的流程
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=ReviewStage(review_plan.stage.value+2),
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+2)])
            )
        elif review_plan.status == ReviewStatus.UNREMEMBERED:
            # 没记住，重新从 STAGE1 开始
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=ReviewStage.STAGE1,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage.STAGE1])
            )
        else:
            # 正常流程，增加stage ，增加 time_to_review 
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=ReviewStage(review_plan.stage.value+1),
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+1)])
            )
        return new_plan
    else:
        return None


