# coding=utf8
import os
import datetime
import random

from sqlalchemy.orm import joinedload

from parrot import Session, DEBUG
from parrot.models import (Word, ReviewPlan, 
                           ReviewStatus, ReviewStage, 
                           ReviewPlanType,STAGE_DELTA_MAP)

def get_word(text):
    '''根据text获取库里的单词'''
    session = Session()
    word = session.query(Word).filter(Word.text==text).one_or_none()
    return word

def add_word(text, phonetic_symbol, meaning, use_case, remark):
    '''添加单词'''
    session = Session()
    word = session.query(Word).filter(Word.text==text).one_or_none()
    time_to_review = (
        datetime.datetime.now() + 
        STAGE_DELTA_MAP[ReviewStage.STAGE1]
    )
    if DEBUG:
        time_to_review = datetime.datetime.now()

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
            time_to_review=time_to_review,
            word_id = word.id,
            review_plan_type=ReviewPlanType.HINT_WORD,
        )
        
        session.add(new_review_plan)
        new_review_plan = ReviewPlan(
            time_to_review=time_to_review,
            word_id=word.id,
            review_plan_type=ReviewPlanType.HINT_MEANING
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
            ReviewPlan(time_to_review=time_to_review,
                       review_plan_type=ReviewPlanType.HINT_WORD),
            ReviewPlan(time_to_review=time_to_review,
                       review_plan_type=ReviewPlanType.HINT_MEANING),
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
    plan_ids = [plan[0] for plan in session.query(ReviewPlan.id).filter(
        ReviewPlan.time_to_review >= begin_time,
        ReviewPlan.time_to_review <= end_time,
        ReviewPlan.status == ReviewStatus.UNREVIEWED
    )]

    print("Total plans: ", len(plan_ids))
    random.shuffle(plan_ids)

    for plan_id in plan_ids:
        review_plan = session.query(ReviewPlan).get(plan_id)
        result = _display_review_card(review_plan)
        review_plan.status = ReviewStatus(int(result)+1)
        review_plan.reviewed_time = datetime.datetime.now()
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
                review_plan_type=review_plan.review_plan_type,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+2)])
            )
        elif review_plan.status == ReviewStatus.UNREMEMBERED:
            # 没记住，重新从 STAGE1 开始
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=ReviewStage.STAGE1,
                review_plan_type=review_plan.review_plan_type,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage.STAGE1])
            )
        else:
            # 正常流程，增加stage ，增加 time_to_review 
            new_plan = ReviewPlan(
                word=review_plan.word,
                stage=ReviewStage(review_plan.stage.value+1),
                review_plan_type=review_plan.review_plan_type,
                time_to_review=(datetime.datetime.now()+
                    STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+1)])
            )
        return new_plan
    else:
        return None

def _display_review_card(plan:ReviewPlan) -> int :
    '''
    展示复习卡片
    返回值为选择的结果：1.知道了/2.记住了/3.没记住
    '''
    if plan.review_plan_type in [None, "", ReviewPlanType.HINT_WORD]:
        print("")
        print('word:', plan.word.text, plan.word.phonetic_symbol)
        input()
        print('use case:', plan.word.use_case)
        input()
        print('meaning:', plan.word.meaning, plan.word.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    elif plan.review_plan_type == ReviewPlanType.HINT_MEANING:
        print("")
        print('meaning:', plan.word.meaning)
        input()
        print('word:', plan.word.text, plan.word.phonetic_symbol)
        print('use case:', plan.word.use_case)
        print('remark:', plan.word.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    else:
        raise Exception("Unknown ReviewPlayType")
