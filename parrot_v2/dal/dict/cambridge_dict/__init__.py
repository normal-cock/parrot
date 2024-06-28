import requests
from bs4 import BeautifulSoup
from parrot_v2.model.core import CWordPos
''' 
class==entry-body__el
    词性(part of speech): class==pos dpos
        verb
            T or I(所有text拼接在一起): class==gram dgram
        noun
    发音(pron): 
        class==uk dpron-i
            type==audio/mpeg
            class==ipa dipa lpr-2 lpl-1
        class==us dpron-i 
            type==audio/mpeg
            class==ipa dipa lpr-2 lpl-1
    含义(def): pr dsense 
        英语解释(所有text拼接在一起): class==def ddef_d db
        汉语解释(所有text拼接在一起): class==trans dtrans dtrans-se break-cj ; lang="zh-Hans"

'''

NON_POS = 'Non-Pos'
NON_PRON = 'Non-Pron'


def entry_filter(soup):
    return soup.select('div.entry-body__el')


def meaning_filter(soup):
    meanings = soup.select('.def-block')
    meaning_list = []
    for meaning in meanings:
        if meaning.find_parent(class_='phrase-block'):
            continue
        meaning_list.append(meaning)
    return meaning_list


def get_pos(soup):
    posgram = soup.select_one('*.posgram')
    if posgram:
        return posgram.get_text()

    dpos = soup.select_one('*.pos.dpos')
    if dpos:
        return dpos.get_text()
    return NON_POS


def get_pron(soup):
    us_pron = soup.select_one(
        '*.us.dpron-i')
    if us_pron != None:
        us_pron = us_pron.select_one('*.ipa.dipa.lpr-2.lpl-1')
        if us_pron != None:
            return us_pron.get_text()
    uk_pron = soup.select_one(
        '*.uk.dpron-i')
    if uk_pron != None:
        uk_pron = uk_pron.select_one('*.ipa.dipa.lpr-2.lpl-1')
        if uk_pron != None:
            return uk_pron.get_text()
    return NON_PRON


def get_en_def(soup):
    en_def = soup.select_one('*.def.ddef_d.db')
    if en_def != None:
        return en_def.get_text()
    return ''


def get_cn_def(soup):
    cn_def = soup.select_one(
        '*.trans.dtrans.dtrans-se.break-cj[lang="zh-Hans"]')
    if cn_def != None:
        return cn_def.get_text()
    return ''


def raw_query(word):
    '''
        return [meaning1, ], ''
            meaning {
                'word': '',
                'pos':'',
                'pron':'',
                'en_def':'',
                'cn_def':'',
            }
    '''
    query_result = []

    url = f"https://dictionary.cambridge.org/us/dictionary/english-chinese-simplified/{word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return query_result, f'status_code={resp.status_code}'

    soup = BeautifulSoup(resp.text, 'html.parser')
    entries = entry_filter(soup)

    for entry in entries:
        # import ipdb
        # ipdb.set_trace()
        pos = get_pos(entry)
        pron = get_pron(entry)
        meanings = meaning_filter(entry)
        for meaning in meanings:
            en_def = get_en_def(meaning)
            cn_def = get_cn_def(meaning)
            query_result.append({
                'word': word,
                'pos': pos,
                'pron': pron,
                'en_def': en_def,
                'cn_def': cn_def,
            })

    return query_result, ''


def _is_pos_match(pos: str, cpos: CWordPos) -> bool:
    pos = pos.lower()
    if ((cpos == CWordPos.NOUN and 'noun' in pos)
        or (cpos == CWordPos.VERB and 'verb' in pos)
            or (cpos == CWordPos.ADJ and 'adj' in pos)):
        return True
    return False


def query_pron_with_pos(word, cpos: CWordPos):
    result_list, err_str = raw_query(word)
    if len(err_str) != 0:
        raise Exception(err_str)
    if len(result_list) == 0:
        return ''
    if cpos.may_have_different_pron_by_pos():
        for result in result_list:
            if _is_pos_match(result['pos'], cpos):
                return result['pron']
    else:
        return result_list[0]['pron']

    return ''


def query_word_with_pos(word, cpos: CWordPos):
    result_list, err_str = raw_query(word)
    if len(err_str) != 0:
        raise Exception(err_str)
    filtered_result_list = []
    for result in result_list:
        if _is_pos_match(result['pos'], cpos) or result['pos'] == NON_POS:
            filtered_result_list.append(result)

    return filtered_result_list


if __name__ == '__main__':
    # meanings, err_str = raw_query('record')
    # meanings, err_str = raw_query('be born')
    meanings, err_str = raw_query('rang')
    if len(err_str) != 0:
        print(err_str)
        exit(0)
    for meaning in meanings:
        print(meaning['pos'], meaning['pron'], meaning['cn_def'])
