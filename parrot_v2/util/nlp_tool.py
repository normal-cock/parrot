'''
premise
    import nltk
    nltk.download('wordnet')
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('cmudict')
pos values: https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
'''
from typing import Callable
from collections import OrderedDict
import nltk
from nltk.corpus import wordnet
from nltk.tokenize.treebank import TreebankWordDetokenizer
from bs4 import BeautifulSoup
from parrot_v2.model.core import CWordPos
from parrot_v2.dal.dict.cambridge_dict import query_word_with_pos
from parrot_v2.util import logger

detokenizer = TreebankWordDetokenizer()


def clear_fmt(input):
    input = BeautifulSoup(input, 'html.parser').get_text()
    tokens = nltk.word_tokenize(input)
    return detokenizer.detokenize(tokens)


def get_cwordpost_from_pos(pos: str) -> CWordPos:
    pos = pos.lower()
    if pos.startswith('nn'):
        return CWordPos.NOUN
    elif pos.startswith('vb'):
        return CWordPos.VERB
    elif pos.startswith('jj'):
        return CWordPos.ADJ
    elif pos.startswith('rb') or pos.endswith('wrb'):
        return CWordPos.ADV
    elif pos.startswith('in'):
        return CWordPos.PREP
    else:
        return CWordPos.OTHER


def morphy_by_cpos(token: str, cpos: CWordPos) -> str:
    token = token.lower().strip()
    if len(token.strip()) == 0:
        raise Exception('empty token')
    origin_token = token
    if cpos == CWordPos.NOUN:
        origin_token = wordnet.morphy(token, wordnet.NOUN)
    elif cpos == CWordPos.VERB:
        origin_token = wordnet.morphy(token, wordnet.VERB)
    if origin_token == None or len(origin_token) == 0:
        origin_token = wordnet.morphy(token)
        if origin_token == None:
            origin_token = token
    return origin_token


def get_origin_morphy_4_phrase(phrase: str):
    # word_text = wordnet.morphy(word_text)
    lower_phrase = phrase.lower()
    origin_tokens = []
    tokens = nltk.word_tokenize(lower_phrase)
    # https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
    tags = nltk.pos_tag(tokens)
    is_start_with_be = False

    for i, (token, pos) in enumerate(tags):
        origin_token = ''
        cpos = get_cwordpost_from_pos(pos)
        if is_start_with_be == False:
            origin_token = morphy_by_cpos(token, cpos)
            if i == 0 and origin_token == 'be':
                is_start_with_be = True
            if origin_token == None:
                origin_token = token
        else:
            origin_token = token
        origin_tokens.append(origin_token)

    return detokenizer.detokenize(origin_tokens)


def parse_sentence(selected, sentence: str, unknown_checker: Callable[[str, str, str], bool]):
    '''
    support noun verb adj adv frist
    return cleaned_selected, selected_query_result, unknown_query_result
    '''
    selected_tokens = nltk.word_tokenize(selected)
    sentence_tokens = nltk.word_tokenize(sentence)
    selected_word_text = get_origin_morphy_4_phrase(selected)
    word_pron = ''
    word_cn_def = ''
    selected_word_pos = None
    selected_word_cpos = None
    # key: token, value: query_result
    unknown_words = OrderedDict()

    tags = nltk.pos_tag(sentence_tokens)

    for token, pos in tags:
        origin_token = ''
        lower_token = token.lower()
        # import ipdb
        # ipdb.set_trace()
        cpos = get_cwordpost_from_pos(pos)
        if token in selected_tokens:
            if selected_word_pos == None or selected_word_cpos == None:
                selected_word_pos = pos
                selected_word_cpos = cpos
        else:
            origin_token = morphy_by_cpos(lower_token, cpos)
            if origin_token == None:
                logger.info(f'token={token}||origin_token is None')
                continue
            if unknown_checker(origin_token, pos, cpos) == True:
                logger.debug(
                    f'pos={pos}||cpos={cpos}||word={origin_token}||found unknwon word')
                query_result_list = query_word_with_pos(origin_token, cpos)
                if len(query_result_list) != 0:
                    unknown_words[token] = query_result_list
                else:
                    logger.debug(
                        f"pos={pos}||cpos={cpos}||word={origin_token}||can't identify unknwon word")

    logger.debug(
        f"pos={selected_word_pos}||cpos={selected_word_cpos}||word={selected_word_text}||selected word")
    word_query_result = query_word_with_pos(
        selected_word_text, selected_word_cpos)
    return selected_word_text, word_query_result, unknown_words


if __name__ == '__main__':
    # assert (get_origin_morphy_4_phrase('pulled off') == 'pull off')
    # assert (get_origin_morphy_4_phrase(
    #     'Was annoyed with') == 'be annoyed with')
    # assert (get_origin_morphy_4_phrase('APPLES') == 'apple')

    def unknown_checker(i): return i.lower() not in ['she', 'an']
    selected = 'ultimatum'
    sentence = 'She sent Serbia an ultimatum.'

    print(parse_sentence(selected, sentence, unknown_checker))
