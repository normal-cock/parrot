
import time
import datetime
import uuid
import nltk
from typing import List
from sqlalchemy import desc
from parrot_v2 import Session, DEBUG, PW

from parrot_v2.model import Item, Word, Meaning, ERLookupRecord, ER_REVIEW_RANGE_DAY

# from parrot_v2.dal.aliyun_oss import oss_sington
from parrot_v2.model.core import ReviewStage, update_meaning_fts, get_related_meaning, CWordPos
from parrot_v2.util import logger


def get_media_url(item_id):
    '''
        return {
            'item_id':
            'subtitle_url':, 
            'audio_url':, 
            'video_url':, 
            'expiration_time':timestamp
        }, err_string
    '''
    from parrot_v2.dal.aliyun_oss import oss_sington

    session = Session()
    item = session.query(Item).filter(
        Item.item_id == item_id).one_or_none()
    if item == None:
        return {}, f'{item_id} not found'
    adjustment = item.subtitle_adjustment
    subtitle_url = oss_sington.get_object_url(f'{item_id}-e.vtt')
    subtitle_url_2 = ''
    if oss_sington.check_existence(f'{item_id}.vtt'):
        subtitle_url = oss_sington.get_object_url(f'{item_id}.vtt')
    if oss_sington.check_existence(f'{item_id}-c.vtt'):
        subtitle_url_2 = oss_sington.get_object_url(f'{item_id}-c.vtt')
    audio_url = oss_sington.get_object_url(f'{item_id}.mp3')
    video_url = oss_sington.get_object_url(f'{item_id}.mp4')

    session.close()
    return {
        'item_id': item_id,
        'subtitle_url': subtitle_url,
        'subtitle_url_2': subtitle_url_2,
        'audio_url': audio_url,
        'video_url': video_url,
        'adjustment': adjustment,
        'expiration_time': time.time() + oss_sington.get_expire_sec(),
    }, ''


def get_item_total() -> int:
    session = Session()
    total_count = session.query(Item).count()
    session.close()
    return total_count


def get_item_list(offset, per_page):
    '''
        return item_list
    '''
    session = Session()
    item_list = session.query(Item).order_by(desc(Item.created_time)).offset(
        offset).limit(per_page).all()
    result_list = []
    for item in item_list:
        result_list.append({
            'create_time': item.created_time.strftime('%Y-%m-%d'),
            'item_name': item.item_name,
            'url': f'{PW}/{item.item_id}',
        })
    session.close()
    return result_list


def add_item(item_name, item_id, adjustment: float, item_type: int):
    session = Session()
    item = Item.new_item(
        item_name=item_name,
        item_id=item_id,
        item_type=item_type,
        adjustment=adjustment,
    )
    session.add(item)
    session.commit()
    session.close()
    return True


def blur_search(query: str):
    '''返回结果[(word_text, meaning_id, meaning_meaning, 
        meaning_use_case, meaning_phonetic_symbol, meaning_remark)]'''
    session = Session()
    meaning_list = get_related_meaning(session, query, output='html')
    session.close()
    return meaning_list


def query_word(word_text: str):
    '''返回结果[(word_text, meaning_id, meaning_meaning, 
        meaning_use_case, meaning_phonetic_symbol, meaning_remark)]'''
    from parrot_v2.util import nlp_tool

    origin_word_text = nlp_tool.get_origin_morphy_4_phrase(word_text)
    result_list = []
    session = Session()
    word = session.query(Word).filter(
        Word.text == origin_word_text).one_or_none()
    if word == None:
        logger.info('query_word||word not found')
        return result_list

    logger.info('query_word||word is found')
    for i, meaning in enumerate(word.meanings):
        result_list.append([
            meaning.word.text,
            meaning.id,
            meaning.meaning,
            meaning.use_case,
            meaning.phonetic_symbol,
            meaning.remark,
            meaning.created_time,
        ])
    session.close()
    return result_list


def unknown_checker_gen(session):
    def _checker(origin_word: str, pos: str, cpos_list: List[CWordPos]) -> bool:
        '''
            origin_word: lower
        '''
        if pos.upper().startswith('PRP') or pos.upper().startswith('PRON'):
            return False
        if CWordPos.PREP in cpos_list:
            return False
        if origin_word in ['be', 'the', 'most', 'so', "'s", 'about', 'think', 'ever', 'go', 'year']:
            return False
        word = session.query(Word).filter(
            Word.text == origin_word).one_or_none()
        return word == None
    return _checker


def parse_sentence(selected, sentence):
    '''
        return {
            'selected':{
                'cleaned_word':'',
                'qr':[{'pron':'', 'cn_def':'',}],
            },
            'unknown_words':{
                'raw_word':[{'pron':'', 'cn_def':'',}],
            }
        }
    '''
    from parrot_v2.util import nlp_tool

    session = Session()
    cleaned_selected, selected_qr, unknown_qr = nlp_tool.parse_sentence(
        selected, sentence, unknown_checker_gen(session))
    session.close()
    logger.info('unkown words:' + ', '.join(unknown_qr.keys()))

    return {
        'selected': {
            'cleaned_word': cleaned_selected,
            'qr': selected_qr,
        },
        'unknown_words': unknown_qr,
    }


def readd_er(meaning_id: int) -> str:
    begin_time = datetime.date.today() - datetime.timedelta(days=ER_REVIEW_RANGE_DAY)
    session = Session()
    if session.query(ERLookupRecord).filter(
            ERLookupRecord.meaning_id == meaning_id,
            ERLookupRecord.created_time >= begin_time).count() > 0:
        return 'already in ER review plan'
    m: Meaning | None = session.query(Meaning).filter(
        Meaning.id == meaning_id).one_or_none()
    if m == None:
        return 'non-exist'
    m.add_er_lookup_record()
    session.commit()
    session.close()
    return ''


if __name__ == '__main__':
    # selected = 'poor'
    # sentence = 'sentence=more fearsome and dangerous than the old'
    # selected = 'notes'
    # sentence = 'The deep notes of Big Ben rang out into the night'
    # selected = 'Whenever'
    # sentence = 'Whenever Princip missed the target people standing around would laugh at him'
    # selected = 'extreme'
    # sentence = 'It was filled with demands so extreme and insulting that Serbia could never accept them.'
    selected = 'commemorates'
    sentence = '''At the Serbian town of Prnjavor, this memorial commemorates those who died.'''
    print(selected)
    print(sentence)
    result_dict = parse_sentence(selected, sentence)
    print(result_dict['selected']['cleaned_word'])
    for qr in result_dict['selected']['qr']:
        print(qr['pron'])
        print(qr['pos'] + ' ' + qr['cn_def'])

    for w, qr_list in result_dict['unknown_words'].items():
        sentence = sentence.replace(w, f"{w}[{qr_list[0]['pron']}]")
    print(sentence)

    for w, qr_list in result_dict['unknown_words'].items():
        print(w)
        for qr in qr_list:
            print(' '.join([qr['word'], qr['pos'], qr['cn_def']]))
        print('\n')
