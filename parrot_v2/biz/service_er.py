import datetime
import signal
import random
from typing import List
from parrot_v2 import Session, DEBUG, cache
from parrot_v2.model import Word, Meaning, ERLookupRecord, ER_REVIEW_RANGE_DAY
from parrot_v2.model.core import update_meaning_fts
from parrot_v2.util import rlinput, logger


def add_er_lookup_record():
    text = rlinput('word_text:', '').strip()
    session = Session()
    word = session.query(Word).filter(
        Word.text == text).one_or_none()
    meaning_obj: Meaning = None
    old_meaning_usecase = ''
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
            old_meaning_usecase = meaning_obj.use_case

    phonetic_symbol = rlinput(
        'phonetic_symbol:', meaning_obj.phonetic_symbol if meaning_obj else '')
    meaning = rlinput(
        'meaning:', meaning_obj.meaning if meaning_obj else '')
    use_case = rlinput(
        'use case:', meaning_obj.use_case if meaning_obj else '')
    remark = rlinput('remark:', meaning_obj.remark if meaning_obj else '')
    use_case_voice = rlinput(
        'use case voice:', meaning_obj.use_case_voice if meaning_obj else '')

    if word == None:
        word = Word.new_word_during_er(
            text, phonetic_symbol, meaning, use_case, remark, use_case_voice)
        session.add(word)
        update_meaning_fts(session, None, None, word.meanings[0])
    elif meaning_obj == None:
        meaning_obj = Meaning.new_meaning_during_er(
            word, phonetic_symbol, meaning, use_case, remark, use_case_voice)
        update_meaning_fts(session, None, None, meaning_obj)
    else:
        meaning_obj.phonetic_symbol = phonetic_symbol
        meaning_obj.meaning = meaning
        meaning_obj.use_case = use_case
        meaning_obj.remark = remark
        meaning_obj.use_case_voice = use_case_voice
        meaning_obj.add_er_lookup_record()
        update_meaning_fts(session, meaning_obj.id,
                           old_meaning_usecase, meaning_obj)

    added_count = session.query(ERLookupRecord).filter(
        ERLookupRecord.created_time >= datetime.date.today()).count()
    session.commit()
    print("looked up {} times today".format(added_count))
    return True


def _gen_er_lookup_records(session, begin_time, end_time) -> List[ERLookupRecord]:
    lookup_record_id_list = cache.get_erplan_today()
    if len(lookup_record_id_list) == 0:
        lookup_records: List[ERLookupRecord] = session.query(ERLookupRecord).filter(
            ERLookupRecord.created_time >= begin_time,
            ERLookupRecord.created_time < end_time,
        ).order_by(-ERLookupRecord.created_time)
        lookup_record_id_list = [record.id for record in lookup_records]
        if len(lookup_record_id_list) == 0:
            return []
        random.shuffle(lookup_record_id_list)
        cache.set_erplan_today(lookup_record_id_list)
        logger.debug('lookup_record_id_list' + str(lookup_record_id_list))

    er_lookup_records = session.query(ERLookupRecord).filter(
        ERLookupRecord.id.in_(lookup_record_id_list)).all()
    er_lookup_records: List[ERLookupRecord] = sorted(
        er_lookup_records, key=lambda o: lookup_record_id_list.index(o.id))
    return er_lookup_records


def fetch_next_er_lookup_record():
    begin_time = datetime.date.today() - datetime.timedelta(days=ER_REVIEW_RANGE_DAY)
    end_time = datetime.date.today()
    if DEBUG == True:
        end_time = datetime.date.today() + datetime.timedelta(days=1)
    session = Session()

    er_lookup_records = _gen_er_lookup_records(
        session, begin_time, end_time)
    total_len = len(er_lookup_records)
    logger.info(
        f"lookup records since {begin_time} to {end_time}. Total {total_len}")

    er_review_index = cache.get_erplan_last_index_today()

    lookup_meaning_id_set = set()
    for record in er_lookup_records:
        lookup_meaning_id_set.add(record.meaning_id)

    next_review_record = None
    next_review_index = -1
    for index, lookup_record in enumerate(er_lookup_records):
        if index <= er_review_index:
            continue
        next_review_record = lookup_record
        next_review_index = index
        break

    if next_review_record == None:
        return None
    meaning = next_review_record.meaning
    result = {
        'review_index': next_review_index,
        'total_len': total_len,
        'meaning': {
            'id': meaning.id,
            'word': meaning.word.text,
            'meaning': meaning.meaning,
            'phonetic_symbol': meaning.phonetic_symbol,
            'use_case': meaning.use_case,
            'remark': meaning.remark,
            'created_time': meaning.created_time,
        }
    }

    if meaning.has_use_case_voice():
        result['meaning']['use_case_media'] = {
            # 'play_url': 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
            'play_url': f'/Rkf7br9rmUMB/meaning-m3u8/{meaning.id}',
            'offset': meaning.ucv_offset(),
            'duration': meaning.ucv_duration(),
        }
    return result


def complete_er_lookup_record_review(index: int):
    return cache.set_erplan_last_index_today(index)


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

    begin_time = datetime.date.today() - datetime.timedelta(days=ER_REVIEW_RANGE_DAY)
    end_time = datetime.date.today()
    if DEBUG == True:
        end_time = datetime.date.today() + datetime.timedelta(days=1)
    session = Session()

    er_lookup_records = _gen_er_lookup_records(
        session, begin_time, end_time)
    total_len = len(er_lookup_records)
    logger.info(
        f"lookup records since {begin_time} to {end_time}. Total {total_len}")

    er_review_index = cache.get_erplan_last_index_today()

    lookup_meaning_id_set = set()
    for record in er_lookup_records:
        lookup_meaning_id_set.add(record.meaning_id)

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
        input()

        other_meanings: List[Meaning] = meaning.word.get_other_meaning_without_review_plan(
            lookup_meaning_id_set
        )
        other_meanings = [
            m for m in other_meanings if m.id != meaning.id]
        if len(other_meanings) > 0:
            print("This word has multiple meanings:")
            for i, meaning in enumerate(other_meanings):
                print("{}. {}".format(i+1, meaning.meaning))
            review_choice = rlinput(
                "Want to review anyone?Input the index(-1 means don't want to):", "-1")
            if review_choice != '-1':
                other_meaning_to_review = other_meanings[int(
                    review_choice)-1]
                other_meaning_to_review.add_er_lookup_record()
                session.commit()

        if cache.set_erplan_last_index_today(index) == False:
            print('set_erplan_last_index_today error, try again')
            exit()
        this_time_reviewed_plan_count += 1

    print("\n\nReview Finished and reviewed {} words, costing {}".format(
        this_time_reviewed_plan_count,
        datetime.datetime.now() - start_time,
    ))


def predict_er():
    begin_time = datetime.date.today() - datetime.timedelta(days=ER_REVIEW_RANGE_DAY)
    end_time = datetime.date.today()
    if DEBUG == True:
        end_time = datetime.date.today() + datetime.timedelta(days=1)
    session = Session()
    for i in range(10):
        cur_begin_time = begin_time + datetime.timedelta(days=i)
        cur_end_time = end_time + datetime.timedelta(days=i)
        review_date = datetime.date.today() + + datetime.timedelta(days=i)
        total_count = session.query(ERLookupRecord).filter(
            ERLookupRecord.created_time >= cur_begin_time,
            ERLookupRecord.created_time < cur_end_time,
        ).count()
        print(f"{review_date} : {total_count}")
