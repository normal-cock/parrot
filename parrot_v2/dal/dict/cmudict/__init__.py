from nltk.corpus import cmudict
from arpabetandipaconvertor.arpabet2phoneticalphabet import ARPAbet2PhoneticAlphabetConvertor

# XXX


def query_pron(word):

    # 如果只有一个读音，可以cmudict，但假如有多个读音，还是用剑桥字典
    # 如果查record，查到3个读音，跟剑桥字典对不上
    arpabet = cmudict.dict()
    arpabet['record']

    # convert from Arpabet to IPA
    converter = ARPAbet2PhoneticAlphabetConvertor()
    converter.convert_to_international_phonetic_alphabet("W IY1 L K IY0 N S N")
