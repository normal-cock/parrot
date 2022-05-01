import datetime
import random
from parrot_v2 import Session, DEBUG
from parrot_v2.model import Word, Meaning, ReviewPlan, ReviewPlanType, AddCounter, ReviewStatus
from parrot_v2.util import rlinput
from sqlalchemy.orm import raiseload


def get_word_or_none(text):
    '''根据text获取库里的单词'''
    session = Session()
    word = session.query(Word).filter(
        Word.text == text).one_or_none()
    # session.close()
    return word


def add_new_word_and_meaning(text, phonetic_symbol, meaning, use_case, remark):
    session = Session()
    counter = AddCounter.get_counter(session)
    word = Word.new_word(text, phonetic_symbol, meaning, use_case, remark)
    session.add(word)
    counter.incr()
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
    session.commit()
    print("added {} words today".format(counter.counter))
    return True


def modify_exist_meaning(meaning_id, phonetic_symbol, meaning, use_case, remark):
    session = Session()
    counter = AddCounter.get_counter(session)
    meaning_obj_new = session.query(Meaning).filter(
        Meaning.id == meaning_id).one_or_none()
    if meaning_obj_new == None:
        exit("Unknow Error(meaning doesn't exist)")
    meaning_obj_new.modify_meaning(phonetic_symbol, meaning, use_case, remark)
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
    meaning_reviewed = set()
    for index, plan_id in enumerate(plan_ids):
        print("")
        print("Progress: {}/{}".format(index+1, total_len))
        review_plan = session.query(ReviewPlan).get(plan_id)
        result = _display_review_card(review_plan)
        new_status_value = int(result)+1
        is_gen_new_plans = False
        if review_plan.meaning_id not in meaning_reviewed:
            is_gen_new_plans = True
            meaning_reviewed.add(review_plan.meaning_id)

        new_plans = review_plan.complete(
            new_status_value, is_gen_new_plans)
        session.add_all(new_plans)
        other_meaning_dict = {}
        other_meanings = review_plan.meaning.word.get_all_meaning_without_review_plan()
        if len(other_meanings) > 0:
            print("This word has multiple meanings:")
            for i, meaning in enumerate(other_meanings):
                print("{}. {}".format(i+1, meaning.meaning))
                other_meaning_dict[str(i+1)] = meaning
            review_choice = rlinput(
                "Want to review anyone?Input the index(-1 means don't want to):", "-1")
            if review_choice != '-1':
                other_meaning_to_review = other_meaning_dict[review_choice]
                other_meaning_to_review.unremember()
        session.commit()


def _display_review_card(plan: ReviewPlan) -> int:
    '''
    展示复习卡片
    返回值为选择的结果: 1.知道了/2.记住了/3.没记住
    '''
    meaning = plan.meaning
    if plan.review_plan_type in [None, "", ReviewPlanType.HINT_WORD]:
        print('word:', meaning.word.text, meaning.phonetic_symbol)
        input()
        print('use case:', meaning.use_case)
        input()
        print('meaning:', meaning.meaning, meaning.remark)
        result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
        return result
    elif plan.review_plan_type == ReviewPlanType.HINT_MEANING:
        print('meaning:', meaning.meaning)
        input()
        print('word:', meaning.word.text, meaning.phonetic_symbol)
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
    begin_time = datetime.date.today() - datetime.timedelta(days=10)
    end_time = datetime.date.today() + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)

    # 明天的复习量
    begin_time = datetime.date.today() + datetime.timedelta(days=1)
    end_time = begin_time + datetime.timedelta(days=1)
    _show_predict(begin_time, end_time)
