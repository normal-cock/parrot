# coding=utf8
import datetime

from sqlalchemy.orm import joinedload

from parrot import Session
from parrot.models import Word, ReviewPlan, ReviewStatus, ReviewStage, STAGE_DELTA_MAP

def add_word(text, phonetic_symbol, meaning, remark):
    '''添加单词'''
    session = Session()
    word = Word(
        text=text, 
        phonetic_symbol=phonetic_symbol, 
        meaning=meaning, 
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
                ReviewPlan.reviewed == False
            ).order_by(ReviewPlan.time_to_review).all():
        yield review_plan
        new_plan = _generate_next_plan(review_plan)
        if new_plan:
            session.add(new_plan)
        session.commit()

def _generate_next_plan(review_plan):
    new_plan = None
    if (review_plan.stage < ReviewStage.STAGE5 
            and review_plan.status != ReviewStatus.UNREVIEWED):
        if (review_plan.status == ReviewStatus.REMEMBERED 
                and review_plan.stage < ReviewStage.STAGE4):
            # 记住了，且 stage 小于 4
            # 大于等于4时，就走正常的流程
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=review_plan.stage+2,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[review_plan.stage+2])
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
                stage=review_plan.stage+1,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[review_plan.stage+1])
            )
        return new_plan
    else:
        return None
