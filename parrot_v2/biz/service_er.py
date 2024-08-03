import datetime
import signal
import random
from typing import List
from parrot_v2 import Session, DEBUG, cache
from parrot_v2.model import Word, Meaning, ERLookupRecord
from parrot_v2.util import rlinput

_REVIEW_RANGE_DAY = 7
_REVIEW_RANGE_DAY = 5


def add_er_lookup_record():
    text = rlinput('word_text:', '').strip()
    session = Session()
    word = session.query(Word).filter(
        Word.text == text).one_or_none()
    meaning_obj: Meaning = None
    if word != None:
        tmp_meaning_dict = {}
        print("found the following existing meanings:")
        for i, meaning in enumerate(word.meanings):
            print("{}. {}".format(i+1, meaning.meaning))
            tmp_meaning_dict[str(i+1)] = meaning
        meaning_choice = rlinput(
            "input existing meaning index(-1 to add a new meaning):", "-1")
        if meaning_choice != "-1" and meaning_choice not in tmp_meaning_dict:
            exit('Error: invalid index')

        if meaning_choice != "-1":
            meaning_obj = tmp_meaning_dict[meaning_choice]

    phonetic_symbol = rlinput(
        'phonetic_symbol:', meaning_obj.phonetic_symbol if meaning_obj else '')
    meaning = rlinput(
        'meaning:', meaning_obj.meaning if meaning_obj else '')
    use_case = rlinput(
        'use case:', meaning_obj.use_case if meaning_obj else '')
    remark = rlinput('remark:', meaning_obj.remark if meaning_obj else '')

    if word == None:
        word = Word.new_word_during_er(
            text, phonetic_symbol, meaning, use_case, remark)
        session.add(word)
    elif meaning_obj == None:
        meaning_obj = Meaning.new_meaning_during_er(
            word, phonetic_symbol, meaning, use_case, remark)
    else:
        meaning_obj.add_er_lookup_record()
    added_count = session.query(ERLookupRecord).filter(
        ERLookupRecord.created_time >= datetime.date.today()).count()
    session.commit()
    print("looked up {} times today".format(added_count))
    return True


def begin_er_lookup_review():
    start_time = datetime.datetime.now()
    this_time_reviewed_plan_count = 0

    def ctrlc_handler(signum, frame):
        print("\n\nReview Finished and reviewed {} words, costing {}".format(
            this_time_reviewed_plan_count,
            datetime.datetime.now() - start_time,
        ))
        exit()
    signal.signal(signal.SIGINT, ctrlc_handler)

    begin_time = datetime.date.today() - datetime.timedelta(days=_REVIEW_RANGE_DAY)
    end_time = datetime.date.today()
    if DEBUG == True:
        end_time = datetime.date.today() + datetime.timedelta(days=1)
    session = Session()

    print("lookup records since {}".format(begin_time))
    lookup_record_id_list = cache.get_erplan_today()
    if len(lookup_record_id_list) == 0:
        lookup_records: List[ERLookupRecord] = session.query(ERLookupRecord).filter(
            ERLookupRecord.created_time >= begin_time,
            ERLookupRecord.created_time < end_time,
        ).order_by(-ERLookupRecord.created_time)
        lookup_record_id_list = [record.id for record in lookup_records]
        random.shuffle(lookup_record_id_list)
        cache.set_erplan_today(lookup_record_id_list)

    total_len = len(lookup_record_id_list)
    er_review_index = cache.get_erplan_last_index_today()

    er_lookup_records = session.query(ERLookupRecord).filter(
        ERLookupRecord.id.in_(lookup_record_id_list)).all()
    er_lookup_records: List[ERLookupRecord] = sorted(
        er_lookup_records, key=lambda o: lookup_record_id_list.index(o.id))

    for index, lookup_record in enumerate(er_lookup_records):
        if index <= er_review_index:
            continue
        meaning = lookup_record.meaning
        print("")
        print("Progress: {}/{}".format(index+1, total_len))
        print('word:', meaning.word.text, meaning.phonetic_symbol)
        input()
        print('use case:', meaning.use_case)
        input()
        print('meaning:', meaning.meaning, meaning.remark)
        print('added at {}'.format(lookup_record.created_time.date()))
        cache.set_erplan_last_index_today(index)
        this_time_reviewed_plan_count += 1

    print("\n\nReview Finished and reviewed {} words, costing {}".format(
            this_time_reviewed_plan_count,
            datetime.datetime.now() - start_time,
        ))


def predict_er():
    begin_time = datetime.date.today() - datetime.timedelta(days=_REVIEW_RANGE_DAY)
    end_time = datetime.date.today()
    if DEBUG == True:
        end_time = datetime.date.today() + datetime.timedelta(days=1)
    session = Session()
    for i in range(10):
        cur_begin_time = begin_time + datetime.timedelta(days=i)
        cur_end_time = end_time + datetime.timedelta(days=i)
        review_date = datetime.date.today() +  + datetime.timedelta(days=i)
        total_count = session.query(ERLookupRecord).filter(
            ERLookupRecord.created_time >= cur_begin_time,
            ERLookupRecord.created_time < cur_end_time,
        ).count()
        print(f"{review_date} : {total_count}")

