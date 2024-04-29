import datetime
import random
import signal
import numpy as np
from parrot_v2 import Session, DEBUG
from parrot_v2.model import Word, Meaning, ReviewPlan, ReviewPlanType, AddCounter, ReviewStatus
from parrot_v2.model.core import ReviewStage, update_meaning_fts, get_related_meaning
from parrot_v2.util import rlinput
from sqlalchemy.orm import raiseload
from typing import List
from collections import defaultdict


def get_word_or_none(text):
    '''根据text获取库里的单词'''
    session = Session()
    word = session.query(Word).filter(
        Word.text == text).one_or_none()
    # session.close()
    return word


def get_report_stats():
    '''
        获得统计数据
        return {'word_count':int, 'meaning_count':int, 'review_plan_count':int}
    '''
    session = Session()
    word_count = session.query(Word).count()
    meaning_count = session.query(Meaning).count()
    review_plan_count = session.query(ReviewPlan).count()
    return {
        'word_count': word_count,
        'meaning_count': meaning_count,
        'review_plan_count': review_plan_count,
    }


def add_new_word_and_meaning(text, phonetic_symbol, meaning, use_case, remark):
    session = Session()
    counter = AddCounter.get_counter(session)
    word = Word.new_word(text, phonetic_symbol, meaning, use_case, remark)
    session.add(word)
    counter.incr()
    meaning: Meaning = word.meanings[0]
    update_meaning_fts(session, None, None, meaning)
    session.commit()
    print("added {} words today".format(counter.counter))
    return True


def add_new_meaning_to_exist_word(word_id, phonetic_symbol, meaning, use_case, remark):
    session = Session()
    word = session.query(Word).filter(Word.id == word_id).one_or_none()
    counter = AddCounter.get_counter(session)
    meaning = Meaning.new_meaning(
        word, phonetic_symbol, meaning, use_case, remark)
    session.add(meaning)
    counter.incr()
    update_meaning_fts(session, None, None, meaning)
    session.commit()
    print("added {} words today".format(counter.counter))
    return True


def modify_exist_meaning(meaning_id, phonetic_symbol, meaning, use_case, remark, unremember=True):
    session = Session()
    meaning_obj_new: Meaning = session.query(Meaning).filter(
        Meaning.id == meaning_id).one_or_none()
    if meaning_obj_new == None:
        exit("Unknow Error(meaning doesn't exist)")
    old_use_case = meaning_obj_new.use_case
    meaning_obj_new.modify_meaning(
        phonetic_symbol, meaning, use_case, remark, unremember=unremember)
    update_meaning_fts(session, meaning_id, old_use_case,
                       meaning_obj_new)
    if unremember == True:
        counter = AddCounter.get_counter(session)
        counter.incr()
        print("added {} words today".format(counter.counter))
    session.commit()
    return True


def modify_exist_word(word_id, word_text):
    session = Session()
    word = session.query(Word).filter(
        Word.id == word_id).one()
    word.text = word_text
    session.commit()


def begin_to_review_v2(begin_time, end_time):
    '''
    开始复习单词，生成器
    begin_time 和 end_time 分别为要复习的复习计划的 time_to_review 范围
    '''
    start_time = datetime.datetime.now()
    session = Session()
    review_plans: List[ReviewPlan] = session.query(ReviewPlan).filter(
        ReviewPlan.time_to_review >= begin_time,
        ReviewPlan.time_to_review <= end_time,
        ReviewPlan.status == ReviewStatus.UNREVIEWED
    )
    review_plans = [review_plan for review_plan in review_plans]

    random.shuffle(review_plans)
    total_len = len(review_plans)

    # 每个元素为dict，格式为
    # {"meaning", "review_status", "review_stage"}
    review_results = []
    for index, review_plan in enumerate(review_plans):
        print("")
        print("Progress: {}/{}".format(index+1, total_len))
        result = _display_review_card(review_plan)
        new_status_value = int(result)+1
        review_plan.complete(new_status_value, is_gen_new_plan=False)
        review_results.append({
            "meaning": review_plan.meaning,
            "review_status": review_plan.status,
            "review_stage": review_plan.stage,
        })

        other_meanings: List[Meaning] = review_plan.meaning.word.get_other_meaning_without_review_plan(
        )
        other_meanings = [
            m for m in other_meanings if m.id != review_plan.meaning.id]
        if len(other_meanings) > 0:
            print("This word has multiple meanings:")
            for i, meaning in enumerate(other_meanings):
                print("{}. {}".format(i+1, meaning.meaning))
            review_choice = rlinput(
                "Want to review anyone?Input the index(-1 means don't want to):", "-1")
            if review_choice != '-1':
                other_meaning_to_review = other_meanings[int(review_choice)-1]
                review_results.append({
                    "meaning": other_meaning_to_review,
                    "review_status": ReviewStatus.UNREMEMBERED,
                    "review_stage": ReviewStage.STAGE5
                })
                # other_meaning_to_review.unremember()

    # generate next review_plan
    review_results_per_meaning = defaultdict(list)
    new_review_plan_count = 0
    for review_result in review_results:
        meaning: Meaning = review_result["meaning"]
        review_results_per_meaning[meaning.id].append(review_result)
    for _, review_result_list in review_results_per_meaning.items():
        meaning = review_result_list[0]["meaning"]
        # check whether there is unremembered review_plan
        unremember_plans = [review_result
                            for review_result in review_result_list
                            if review_result["review_status"] == ReviewStatus.UNREMEMBERED]
        if len(unremember_plans) > 0:
            new_review_plan_count += meaning.unremember()
            continue
        else:
            # find reviewed result with maximum stage
            key_reviewed_result = None
            for review_result in review_result_list:
                review_status = review_result["review_status"]
                review_stage = review_result["review_stage"]
                if review_status == ReviewStatus.REVIEWED:
                    if key_reviewed_result == None:
                        key_reviewed_result = review_result
                    elif key_reviewed_result["review_stage"].value < review_stage.value:
                        key_reviewed_result = review_result
                    else:
                        pass
            if key_reviewed_result != None:
                new_review_plan_count += ReviewPlan.gen_next_plan(
                    meaning,
                    key_reviewed_result["review_stage"],
                    ReviewStatus.REVIEWED,
                )
                continue

            # find remember result with maximum stage
            key_remember_result = None
            for review_result in review_result_list:
                review_status = review_result["review_status"]
                review_stage = review_result["review_stage"]
                if review_status == ReviewStatus.REMEMBERED:
                    if key_remember_result == None:
                        key_remember_result = review_result
                    elif key_remember_result["review_stage"].value < review_stage.value:
                        key_remember_result = review_result
                    else:
                        pass
            if key_remember_result != None:
                new_review_plan_count += ReviewPlan.gen_next_plan(
                    meaning,
                    key_remember_result["review_stage"],
                    ReviewStatus.REMEMBERED,
                )
                continue

    session.commit()

    print("\nFinished and generated {} new plans, costing {}".format(
        new_review_plan_count,
        datetime.datetime.now() - start_time,
    ))


def begin_to_review_v3(begin_time, end_time):
    '''
    开始复习单词，生成器
    begin_time 和 end_time 分别为要复习的复习计划的 time_to_review 范围
    '''
    start_time = datetime.datetime.now()
    reviewed_plan_count = 0
    new_review_plan_count = 0

    def ctrlc_handler(signum, frame):
        print("\n\nReview Finished and generated {} new plans, costing {}".format(
            new_review_plan_count,
            datetime.datetime.now() - start_time,
        ))
        exit()
    signal.signal(signal.SIGINT, ctrlc_handler)
    session = Session()
    review_plans: List[ReviewPlan] = session.query(ReviewPlan).filter(
        ReviewPlan.time_to_review >= begin_time,
        ReviewPlan.time_to_review <= end_time,
        ReviewPlan.status == ReviewStatus.UNREVIEWED
    )
    review_plans = [review_plan for review_plan in review_plans]
    review_plans_per_meaning = defaultdict(list)
    for review_plan in review_plans:
        meaning: Meaning = review_plan.meaning
        review_plans_per_meaning[meaning.id].append(review_plan)
    minimum_meaning_count_in_batch = 10
    if DEBUG:
        minimum_meaning_count_in_batch = 2
    # list of plans of each meaning, 2-d array
    plans_list = list(review_plans_per_meaning.values())
    random.shuffle(plans_list)
    split_count = len(plans_list) // minimum_meaning_count_in_batch
    if split_count == 0:
        split_count = 1
    review_plans_in_batch = np.array_split(plans_list, split_count)

    total_review_plan_count = len(review_plans)

    for sub_review_plans_list in review_plans_in_batch:
        tmp_review_plans = []
        for tmp_review_plans2 in sub_review_plans_list:
            tmp_review_plans.extend(tmp_review_plans2)
        tmp_new_review_plan_count = _review_in_batch(
            session, tmp_review_plans, reviewed_plan_count, total_review_plan_count)
        reviewed_plan_count += len(tmp_review_plans)
        new_review_plan_count += tmp_new_review_plan_count

    print("\nFinished and generated {} new plans, costing {}".format(
        new_review_plan_count,
        datetime.datetime.now() - start_time,
    ))


def _review_in_batch(session, review_plans, reviewed_plan_count, total_review_plan_count) -> int:
    '''
        return new_review_plan_count
    '''
    random.shuffle(review_plans)
    batch_count = len(review_plans)

    # 每个元素为dict，格式为
    # {"meaning", "review_status", "review_stage"}
    review_results = []
    for index, review_plan in enumerate(review_plans):
        print("")
        print("Progress: {}/{} ({}/{} in batch)".format(
            reviewed_plan_count+index+1,
            total_review_plan_count,
            index+1,
            batch_count,
        ))
        result = _display_review_card(review_plan)
        new_status_value = int(result)+1
        review_plan.complete(new_status_value, is_gen_new_plan=False)
        review_results.append({
            "meaning": review_plan.meaning,
            "review_status": review_plan.status,
            "review_stage": review_plan.stage,
        })

        other_meanings: List[Meaning] = review_plan.meaning.word.get_other_meaning_without_review_plan(
        )
        other_meanings = [
            m for m in other_meanings if m.id != review_plan.meaning.id]
        if len(other_meanings) > 0:
            print("This word has multiple meanings:")
            for i, meaning in enumerate(other_meanings):
                print("{}. {}".format(i+1, meaning.meaning))
            review_choice = rlinput(
                "Want to review anyone?Input the index(-1 means don't want to):", "-1")
            if review_choice != '-1':
                other_meaning_to_review = other_meanings[int(review_choice)-1]
                review_results.append({
                    "meaning": other_meaning_to_review,
                    "review_status": ReviewStatus.UNREMEMBERED,
                    "review_stage": ReviewStage.STAGE5
                })
                # other_meaning_to_review.unremember()

    # generate next review_plan
    review_results_per_meaning = defaultdict(list)
    new_review_plan_count = 0
    for review_result in review_results:
        meaning: Meaning = review_result["meaning"]
        review_results_per_meaning[meaning.id].append(review_result)
    for _, review_result_list in review_results_per_meaning.items():
        meaning = review_result_list[0]["meaning"]
        # check whether there is unremembered review_plan
        unremember_plans = [review_result
                            for review_result in review_result_list
                            if review_result["review_status"] == ReviewStatus.UNREMEMBERED]
        if len(unremember_plans) > 0:
            new_review_plan_count += meaning.unremember()
            continue
        else:
            # find reviewed result with maximum stage
            key_reviewed_result = None
            for review_result in review_result_list:
                review_status = review_result["review_status"]
                review_stage = review_result["review_stage"]
                if review_status == ReviewStatus.REVIEWED:
                    if key_reviewed_result == None:
                        key_reviewed_result = review_result
                    elif key_reviewed_result["review_stage"].value < review_stage.value:
                        key_reviewed_result = review_result
                    else:
                        pass
            if key_reviewed_result != None:
                new_review_plan_count += ReviewPlan.gen_next_plan(
                    meaning,
                    key_reviewed_result["review_stage"],
                    ReviewStatus.REVIEWED,
                )
                continue

            # find remember result with maximum stage
            key_remember_result = None
            for review_result in review_result_list:
                review_status = review_result["review_status"]
                review_stage = review_result["review_stage"]
                if review_status == ReviewStatus.REMEMBERED:
                    if key_remember_result == None:
                        key_remember_result = review_result
                    elif key_remember_result["review_stage"].value < review_stage.value:
                        key_remember_result = review_result
                    else:
                        pass
            if key_remember_result != None:
                new_review_plan_count += ReviewPlan.gen_next_plan(
                    meaning,
                    key_remember_result["review_stage"],
                    ReviewStatus.REMEMBERED,
                )
                continue

    session.commit()
    return new_review_plan_count


def _display_review_card(plan: ReviewPlan) -> int:
    '''
    展示复习卡片
    返回值为选择的结果: 1.知道了/2.记住了/3.没记住
    '''
    meaning = plan.meaning
    if plan.review_plan_type in [None, "", ReviewPlanType.HINT_WORD]:
        input(f'word: {meaning.word.text} {meaning.phonetic_symbol}')
        input(f'use case: {meaning.use_case}')
        print('meaning:', meaning.meaning, meaning.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    elif plan.review_plan_type == ReviewPlanType.HINT_MEANING:
        input(f'meaning: {meaning.meaning}')
        print(f'word: {meaning.word.text} {meaning.phonetic_symbol}')
        print('use case:', meaning.use_case)
        print('remark:', meaning.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    else:
        raise Exception("Unknown ReviewPlayType")


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
    begin_time = datetime.date.today() - datetime.timedelta(days=15)
    end_time = datetime.date.today() + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)

    # 明天的复习量
    begin_time = datetime.date.today() + datetime.timedelta(days=1)
    end_time = begin_time + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)


def show_predict_v2():
    '''预测未来的复习任务量'''
    session = Session()
    predict_days = 15
    # 今天的复习量
    begin_time = datetime.date.today() - datetime.timedelta(days=15)
    end_time = datetime.date.today() + datetime.timedelta(days=1)
    final_end_time = datetime.date.today() + datetime.timedelta(days=predict_days)

    while end_time <= final_end_time:
        review_time = datetime.datetime.now().replace(
            year=end_time.year,
            month=end_time.month,
            day=end_time.day,
        ) - datetime.timedelta(days=1)
        review_plans_today = []
        review_plans_in_db = session.query(ReviewPlan).filter(
            ReviewPlan.time_to_review >= begin_time,
            ReviewPlan.time_to_review < end_time,
            ReviewPlan.status == ReviewStatus.UNREVIEWED
        ).all()
        review_plans_today = list(review_plans_in_db)
        review_count = len(review_plans_today)
        print("{} : {}".format(end_time-datetime.timedelta(days=1), review_count))

        # generate tmp plans by today's review_plans
        reviewed_meaning_id = set()
        for review_plan in review_plans_today:
            if (review_plan.meaning.id not in reviewed_meaning_id and
                    review_plan.stage.value != ReviewStage.STAGE5.value):
                ReviewPlan.gen_plan(
                    review_plan.meaning,
                    ReviewStage(review_plan.stage.value + 1),
                    review_time=review_time,
                )
                reviewed_meaning_id.add(review_plan.meaning.id)

        begin_time = end_time
        end_time = end_time + datetime.timedelta(days=1)

    session.rollback()
    session.close()
    print('predict finished')


def search(query: str):
    session = Session()
    meaning_list = get_related_meaning(session, query)
    if len(meaning_list) != 0:
        print("found the following existing meanings:")
        for i, meaning_dto_tmp in enumerate(meaning_list):
            print("{}. {}||{}||{}".format(
                i, meaning_dto_tmp.word_text,
                meaning_dto_tmp.meaning, meaning_dto_tmp.use_case))

        meaning_choice = int(rlinput(
            "input existing meaning index:", "0"))
        if meaning_choice < 0 or meaning_choice >= len(meaning_list):
            exit('Error: invalid index')

        print("")
        meaning_dto = meaning_list[meaning_choice]

        phonetic_symbol = print(
            'phonetic_symbol:', meaning_dto.phonetic_symbol)
        meaning = print(
            'meaning:', meaning_dto.meaning)
        use_case = print(
            'use case:', meaning_dto.use_case)
        remark = print('remark:', meaning_dto.remark)
    else:
        print("not found")


def rebuild_fts():
    print('begin to rebuild fts...')
    create_sql = '''
    CREATE VIRTUAL TABLE IF NOT EXISTS meaning_fts USING 
        fts5(use_case, content='meaning', content_rowid='id', tokenize = 'porter');
    '''
    delete_all_sql = '''INSERT INTO meaning_fts(meaning_fts) VALUES('delete-all');'''
    rebuild_sql = '''
    INSERT INTO meaning_fts(rowid, use_case) 
        select meaning.id,meaning.use_case from meaning;
    '''
    session = Session()
    result = session.execute(create_sql)
    result = session.execute(delete_all_sql)
    result = session.execute(rebuild_sql)
    print('rebuild {} records'.format(result.rowcount))
    session.commit()
    return
