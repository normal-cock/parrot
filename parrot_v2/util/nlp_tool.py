"""
premise
    import nltk
    nltk.download('wordnet')
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('cmudict')
    nltk.download('averaged_perceptron_tagger_eng')
pos values: https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
"""

from typing import Callable, List
from collections import OrderedDict, defaultdict
import spacy
import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize.treebank import TreebankWordDetokenizer
from bs4 import BeautifulSoup
from parrot_v2.model.core import CWordPos
from parrot_v2.dal.dict.cambridge_dict import query_word_with_cpos
from parrot_v2.util import logger


detokenizer = TreebankWordDetokenizer()
lemmatizer = WordNetLemmatizer()

nlp = spacy.load("en_core_web_sm")


def tokenize(input: str) -> List[str]:
    return nltk.word_tokenize(input)


def detokenize(tokens: List[str]) -> str:
    return detokenizer.detokenize(tokens)


def clear_fmt(input):
    input = BeautifulSoup(input, "html.parser").get_text()
    tokens = nltk.word_tokenize(input)
    return detokenizer.detokenize(tokens)


def get_cpos_from_pos(pos: str) -> CWordPos:
    pos = pos.lower()
    if pos.startswith("nn") or "noun" in pos:
        return CWordPos.NOUN
    elif pos.startswith("vb") or "verb" in pos:
        return CWordPos.VERB
    elif pos.startswith("jj") or "adj" in pos:
        return CWordPos.ADJ
    elif pos.startswith("rb") or pos.endswith("wrb") or "adv" in pos:
        return CWordPos.ADV
    elif pos.startswith("in") or "adp" in pos:
        return CWordPos.PREP
    else:
        return CWordPos.OTHER


def morphy_by_cpos(token: str, cpos_list: List[CWordPos]) -> str:
    """词语形态处理"""
    token = token.lower().strip()
    if len(token.strip()) == 0:
        raise Exception("empty token")
    origin_token = token
    origin_token1 = token
    origin_token2 = token
    if CWordPos.NOUN in cpos_list:
        origin_token1 = wordnet.morphy(token, wordnet.NOUN)
        origin_token2 = lemmatizer.lemmatize(token, "n")
    if CWordPos.VERB in cpos_list:
        origin_token1 = wordnet.morphy(token, wordnet.VERB)
        origin_token2 = lemmatizer.lemmatize(token, "v")
    origin_token = origin_token2
    if origin_token1 != origin_token2:
        logger.warn(
            f"origin_token1={origin_token1}||origin_token2={origin_token2}||diff origin_token1 and origin_token2"
        )
    return origin_token


def get_cpos_dict_4_sentence(sentence: str) -> defaultdict[str, set[CWordPos]]:
    """获取选中词语的cpos列表"""
    token_pos_dict = defaultdict(set)

    # 使用不同的方法充分解析cpos
    sentence_tokens = nltk.word_tokenize(sentence)
    tags = nltk.pos_tag(sentence_tokens)
    for token, pos in tags:
        cpos = get_cpos_from_pos(pos)
        token_pos_dict[token].add(cpos)

    # 使用不同的方法充分解析cpos
    alternative_pos = nlp(sentence)
    for token in alternative_pos:
        cpos = get_cpos_from_pos(token.pos_)
        token_pos_dict[token.text].add(cpos)

    return token_pos_dict


def get_morphy_4_sel(sel: str, sentence: str) -> str:
    """获取选中词语的morphy
    sel和sentence需要原生数据，没经过大小写转换的
    """
    sel_tokens = nltk.word_tokenize(sel)
    sentence_tokens = nltk.word_tokenize(sentence)
    # 这里不能直接用`if sel not in sentence`是因为某些场景，tokenize和detokenize会有差异。
    # 也不能用`if sel_token not in sentence`，因为""会被tokenize称``
    #   例如"smelter[ˈsmel.tɚ]" 会变成"smelter [ˈsmel.tɚ]", 多一个空格
    # 也不能用`sel_token in sel_tokens`，因为有时候查询的只是半个token
    # 所以暂时不校验
    # for sel_token in sel_tokens:
    #     if sel_token not in sentence_tokens:
    #         raise Exception(
    #             f"sel_token={sel_token} not in sentence_tokens={sentence_tokens}"
    #         )

    token_pos_dict = get_cpos_dict_4_sentence(sentence)
    sel_morphy_tokens = []
    for token in sel_tokens:
        origin_token = morphy_by_cpos(token, list(token_pos_dict[token]))
        sel_morphy_tokens.append(origin_token)
    return detokenizer.detokenize(sel_morphy_tokens)


def parse_sentence(
    selected, sentence: str, unknown_checker: Callable[[str, str, List[CWordPos]], bool]
):
    """
    support noun verb adj adv frist
    return cleaned_selected, selected_query_result, unknown_query_result
    """
    selected_tokens = nltk.word_tokenize(selected)
    sentence_tokens = nltk.word_tokenize(sentence)
    selected_origin_tokens = []
    word_pron = ""
    word_cn_def = ""
    selected_word_pos = []
    selected_word_cpos = []
    # key: token, value: query_result
    unknown_words = OrderedDict()

    token_pos_dict = get_cpos_dict_4_sentence(sentence)

    alternative_pos = nlp(sentence)

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
                logger.info(f"token={token}||origin_token is None")
                continue
            logger.debug(
                f"pos={pos}||cpos={cpos_list}||raw_word={lower_token}||word={origin_token}||found token"
            )
            if unknown_checker(origin_token, pos, cpos_list) == True:
                logger.debug(
                    f"pos={pos}||cpos={cpos_list}||word={origin_token}||found unknwon word"
                )
                query_result_list = query_word_with_cpos(origin_token, cpos_list)
                if len(query_result_list) != 0:
                    unknown_words[token] = query_result_list
                else:
                    logger.debug(
                        f"pos={pos}||cpos={cpos_list}||word={origin_token}||can't identify unknwon word"
                    )

    selected_word_text = detokenizer.detokenize(selected_origin_tokens)
    logger.debug(
        f"pos={selected_word_pos}||cpos={selected_word_cpos}||word={selected_word_text}||selected word"
    )
    word_query_result = query_word_with_cpos(selected_word_text, selected_word_cpos)
    return selected_word_text, word_query_result, unknown_words


if __name__ == "__main__":
    # assert (get_origin_morphy_4_phrase('pulled off') == 'pull off')
    # assert (get_origin_morphy_4_phrase(
    #     'Was annoyed with') == 'be annoyed with')
    # assert (get_origin_morphy_4_phrase('APPLES') == 'apple')

    def unknown_checker(i):
        return i.lower() not in ["she", "an"]

    selected = "ultimatum"
    sentence = "She sent Serbia an ultimatum."

    print(parse_sentence(selected, sentence, unknown_checker))
