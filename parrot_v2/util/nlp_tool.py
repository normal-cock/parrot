'''
premise
    import nltk
    nltk.download('wordnet')
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('cmudict')
pos values: https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
'''
from typing import Callable, List
from collections import OrderedDict, defaultdict
import spacy
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize.treebank import TreebankWordDetokenizer
from bs4 import BeautifulSoup
from parrot_v2.model.core import CWordPos
from parrot_v2.dal.dict.cambridge_dict import query_word_with_pos
from parrot_v2.util import logger


detokenizer = TreebankWordDetokenizer()
lemmatizer = WordNetLemmatizer()

nlp = spacy.load("en_core_web_sm")


def clear_fmt(input):
    input = BeautifulSoup(input, 'html.parser').get_text()
    tokens = nltk.word_tokenize(input)
    return detokenizer.detokenize(tokens)


def get_cpos_from_pos(pos: str) -> CWordPos:
    pos = pos.lower()
    if pos.startswith('nn') or 'noun' in pos:
        return CWordPos.NOUN
    elif pos.startswith('vb') or 'verb' in pos:
        return CWordPos.VERB
    elif pos.startswith('jj') or 'adj' in pos:
        return CWordPos.ADJ
    elif pos.startswith('rb') or pos.endswith('wrb') or 'adv' in pos:
        return CWordPos.ADV
    elif pos.startswith('in') or 'adp' in pos:
        return CWordPos.PREP
    else:
        return CWordPos.OTHER


def morphy_by_cpos(token: str, cpos_list: List[CWordPos]) -> str:
    token = token.lower().strip()
    if len(token.strip()) == 0:
        raise Exception('empty token')
    origin_token = token
    origin_token1 = token
    origin_token2 = token
    if CWordPos.NOUN in cpos_list:
        origin_token1 = wordnet.morphy(token, wordnet.NOUN)
        origin_token2 = lemmatizer.lemmatize(token, 'n')
    if CWordPos.VERB in cpos_list:
        origin_token1 = wordnet.morphy(token, wordnet.VERB)
        origin_token2 = lemmatizer.lemmatize(token, 'v')
    origin_token = origin_token2
    if origin_token1 != origin_token2:
        logger.warn(
            f'origin_token1={origin_token1}||origin_token2={origin_token2}||diff origin_token1 and origin_token2')
    return origin_token


def get_origin_morphy_4_phrase(phrase: str):
    '''
        20240703 暂时废弃该方法，sel的还原也使用整句解析出来的pos
    '''
    # word_text = wordnet.morphy(word_text)
    lower_phrase = phrase.lower()
    origin_tokens = []
    tokens = nltk.word_tokenize(lower_phrase)
    # https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
    tags = nltk.pos_tag(tokens)
    is_start_with_be = False

    for i, (token, pos) in enumerate(tags):
        origin_token = ''
        cpos = get_cpos_from_pos(pos)
        if is_start_with_be == False:
            origin_token = morphy_by_cpos(token, [cpos])
            if i == 0 and origin_token == 'be':
                is_start_with_be = True
            if origin_token == None:
                origin_token = token
        else:
            origin_token = token
        origin_tokens.append(origin_token)

    origin_phrase = detokenizer.detokenize(origin_tokens)
    logger.debug(
        f'raw_sel={phrase}||origin_sel={origin_phrase}||get_origin_morphy_4_phrase')
    return origin_phrase


def parse_sentence(selected, sentence: str, unknown_checker: Callable[[str, str, List[CWordPos]], bool]):
    '''
    support noun verb adj adv frist
    return cleaned_selected, selected_query_result, unknown_query_result
    '''
    selected_tokens = nltk.word_tokenize(selected)
    sentence_tokens = nltk.word_tokenize(sentence)
    selected_origin_tokens = []
    word_pron = ''
    word_cn_def = ''
    selected_word_pos = []
    selected_word_cpos = []
    # key: token, value: query_result
    unknown_words = OrderedDict()

    token_pos_dict = defaultdict(set)

    tags = nltk.pos_tag(sentence_tokens)
    for token, pos in tags:
        cpos = get_cpos_from_pos(pos)
        token_pos_dict[token].add(cpos)

    alternative_pos = nlp(sentence)
    for token in alternative_pos:
        cpos = get_cpos_from_pos(token.pos_)
        token_pos_dict[token.text].add(cpos)

    # for token, pos in tags:
    for token_item in alternative_pos:
        token = token_item.text
        pos = token_item.pos_
        cpos_list = list(token_pos_dict[token])

        # import ipdb
        # ipdb.set_trace()
        lower_token = token.lower()
        origin_token = token_item.lemma_
        origin_token = origin_token.lower()
        if origin_token == lower_token:
            origin_token = morphy_by_cpos(lower_token, cpos_list)
        if token in selected_tokens:
            selected_word_pos.append(pos)
            selected_word_cpos += cpos_list
                
            if origin_token not in selected_origin_tokens:
                selected_origin_tokens.append(origin_token)
        else:
            if origin_token == None:
                logger.info(f'token={token}||origin_token is None')
                continue
            logger.debug(
                f'pos={pos}||cpos={cpos_list}||raw_word={lower_token}||word={origin_token}||found token')
            if unknown_checker(origin_token, pos, cpos_list) == True:
                logger.debug(
                    f'pos={pos}||cpos={cpos_list}||word={origin_token}||found unknwon word')
                query_result_list = query_word_with_pos(origin_token, cpos_list)
                if len(query_result_list) != 0:
                    unknown_words[token] = query_result_list
                else:
                    logger.debug(
                        f"pos={pos}||cpos={cpos_list}||word={origin_token}||can't identify unknwon word")

    selected_word_text = detokenizer.detokenize(selected_origin_tokens)
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
