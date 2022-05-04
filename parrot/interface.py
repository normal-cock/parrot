# coding=utf8
import os
import datetime
import random

# from sqlalchemy.orm import joinedload

from parrot import Session, DEBUG
from parrot.models import (Word, ReviewPlan,
                           ReviewStatus, ReviewStage,
                           ReviewPlanType, STAGE_DELTA_MAP,
                           AddCounter,)


def _show_predict(begin_time: datetime.date, end_time: datetime.date):
    session = Session()
    review_count = session.query(ReviewPlan.id).filter(
        ReviewPlan.time_to_review >= begin_time,
        ReviewPlan.time_to_review < end_time,
        ReviewPlan.status == ReviewStatus.UNREVIEWED
    ).count()
    print("{} : {}".format(end_time-datetime.timedelta(days=1), review_count))


def show_predict():
    '''预测未来的复习任务量'''
    # 今天的复习量
    begin_time = datetime.date.today() - datetime.timedelta(days=10)
    end_time = datetime.date.today() + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)

    # 明天的复习量
    begin_time = datetime.date.today() + datetime.timedelta(days=1)
    end_time = begin_time + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)


def get_word(text):
    '''根据text获取库里的单词'''
    session = Session()
    word = session.query(Word).filter(Word.text == text).one_or_none()
    return word


def add_word(text, phonetic_symbol, meaning, use_case, remark):
    '''添加单词'''
    session = Session()
    word = session.query(Word).filter(Word.text == text).one_or_none()
    time_to_review = (
        datetime.datetime.now() +
        STAGE_DELTA_MAP[ReviewStage.STAGE1]
    )
    counter = AddCounter.get_counter(session)
    if DEBUG:
        time_to_review = datetime.datetime.now()

    if word:
        word.phonetic_symbol = phonetic_symbol
        word.meaning = meaning
        word.use_case = use_case
        word.remark = remark

        # 先将所有未复习的计划改为UNREMEMBERED
        session.query(ReviewPlan).filter(
            ReviewPlan.word_id == word.id,
            ReviewPlan.status == ReviewStatus.UNREVIEWED,
        ).update(
            {ReviewPlan.status: ReviewStatus.UNREMEMBERED},
            synchronize_session='fetch',
        )

        # 将所有计划中最近的一个计划改为UNREMEMBERED
        # 这里其实不需要了
        last_review_plan = session.query(
            ReviewPlan
        ).filter(
            ReviewPlan.word_id == word.id
        ).order_by(ReviewPlan.time_to_review.desc()).first()
        last_review_plan.status = ReviewStatus.UNREMEMBERED

        plans = ReviewPlan.generate_full_review_plan(word.id, time_to_review)
        session.add_all(plans)
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
    counter.incr()
    session.commit()
    print("added {} words today".format(counter.counter))
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

    total_len = len(plan_ids)
    print("Total plans: ", total_len)
    random.shuffle(plan_ids)

    # 某个单词只要有一种形式Plan没记住，就重新构造该单词的所有形式Plan
    # 本次已经生成过所有Plan的单词，不再重复生成
    words_has_reviewed = set()
    for index, plan_id in enumerate(plan_ids):
        print("")
        print("Progress: {}/{}".format(index+1, total_len))
        review_plan = session.query(ReviewPlan).get(plan_id)
        result = _display_review_card(review_plan)
        review_plan.status = ReviewStatus(int(result)+1)
        review_plan.reviewed_time = datetime.datetime.now()
        if review_plan.word_id not in words_has_reviewed:
            new_plans = _generate_next_plan(review_plan)
            session.add_all(new_plans)
            words_has_reviewed.add(review_plan.word_id)
        session.commit()


def _generate_next_plan(review_plan):
    new_plans = []
    if (review_plan.stage.value != ReviewStage.STAGE5.value
            and review_plan.status != ReviewStatus.UNREVIEWED):
        if (review_plan.status == ReviewStatus.REMEMBERED
                and review_plan.stage.value < ReviewStage.STAGE4.value):
            # 记住了，且 stage 小于 4
            # 大于等于4时，就走正常的流程
            new_plans.extend(ReviewPlan.generate_full_review_plan(
                review_plan.word_id,
                time_to_review=(datetime.datetime.now() +
                                STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+2)]),
                stage_value=review_plan.stage.value+2,
            ))
        elif review_plan.status == ReviewStatus.UNREMEMBERED:
            # 没记住，重新从 STAGE1 开始
            new_plans.extend(ReviewPlan.generate_full_review_plan(
                review_plan.word_id,
                time_to_review=(datetime.datetime.now() +
                                STAGE_DELTA_MAP[ReviewStage.STAGE1]),
                stage_value=ReviewStage.STAGE1.value,
            ))
        else:
            # 正常流程，增加stage ，增加 time_to_review
            new_plans.extend(ReviewPlan.generate_full_review_plan(
                review_plan.word_id,
                time_to_review=(datetime.datetime.now() +
                                STAGE_DELTA_MAP[ReviewStage(review_plan.stage.value+1)]),
                stage_value=review_plan.stage.value+1,
            ))
    return new_plans


def _display_review_card(plan: ReviewPlan) -> int:
    '''
    展示复习卡片
    返回值为选择的结果: 1.知道了/2.记住了/3.没记住
    '''
    if plan.review_plan_type in [None, "", ReviewPlanType.HINT_WORD]:
        print('word:', plan.word.text, plan.word.phonetic_symbol)
        input()
        print('use case:', plan.word.use_case)
        input()
        print('meaning:', plan.word.meaning, plan.word.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    elif plan.review_plan_type == ReviewPlanType.HINT_MEANING:
        print('meaning:', plan.word.meaning)
        input()
        print('word:', plan.word.text, plan.word.phonetic_symbol)
        print('use case:', plan.word.use_case)
        print('remark:', plan.word.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    else:
        raise Exception("Unknown ReviewPlayType")
