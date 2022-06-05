# coding=utf8
import os
import argparse
import datetime

from parrot_v2.biz.service import (
    get_word_or_none,
    add_new_word_and_meaning,
    add_new_meaning_to_exist_word,
    modify_exist_meaning,
    begin_to_review_v2,
    show_predict,
    search,
    rebuild_fts,
)

from parrot_v2.biz.service_er import add_er_lookup_record, begin_er_lookup_review, predict_er

from parrot_v2.biz.migrate_script import import_data_from_v1
from parrot_v2 import DATA_DIR
from parrot_v2.util import rlinput


def run():
    '''parrot_v2命令行入口'''
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=[
                        'add', 'review', 'search', 'migrate',
                        'add_er', 'review_er', 'predict_er',
                        'predict', 'import_v1_data',
                        'initialize'])
    args = parser.parse_args()

    if args.command == 'initialize':
        os.system("rm -r {}".format(DATA_DIR))
    if args.command == 'add':
        word_text = rlinput('word_text:', '').strip()
        if not word_text:
            exit('Error: empty word')

        word = get_word_or_none(word_text)

        meaning_obj = None
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
            add_new_word_and_meaning(
                word_text, phonetic_symbol, meaning, use_case, remark)
        elif meaning_obj == None:
            add_new_meaning_to_exist_word(
                word.id, phonetic_symbol, meaning, use_case, remark)
        else:
            modify_exist_meaning(
                meaning_obj.id, phonetic_symbol, meaning, use_case, remark)
    if args.command == 'review':
        begin_time = datetime.date.today() - datetime.timedelta(days=7)
        end_time = datetime.date.today() + datetime.timedelta(days=1)
        # begin_to_review(begin_time, end_time)
        begin_to_review_v2(begin_time, end_time)
    if args.command == 'search':
        query = rlinput('word_text:', '').strip()
        # print("search:", query)
        search(query)
    if args.command in ['initialize', 'migrate']:
        alembic_config = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'alembic.ini')
        os.system("mkdir -p {}".format(DATA_DIR))
        os.system("alembic -c {} upgrade head".format(alembic_config))
        rebuild_fts()
    if args.command == 'predict':
        show_predict()
    if args.command == 'import_v1_data':
        import_data_from_v1()
    if args.command == 'add_er':
        add_er_lookup_record()
    if args.command == 'review_er':
        begin_er_lookup_review()
    if args.command == 'predict_er':
        predict_er()


if __name__ == '__main__':
    run()
