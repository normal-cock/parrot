# coding=utf8
import os
import argparse
import datetime
# 为了兼容 mac os
try:
    import gnureadline as readline
except ImportError:
    import readline

from parrot.interface import get_word, add_word, begin_to_review, show_predict
from parrot import DATA_DIR

def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
       return input(prompt)  # or raw_input in Python 2
    finally:
       readline.set_startup_hook()

def run():
    '''parrot命令行入口'''
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=[
                        'add', 'review', 'migrate', 'predict'])
    args = parser.parse_args()
    if args.command == 'add':
        word_text = rlinput('word_text:', '').strip()
        if not word_text:
            exit('Error: empty word')
        word = get_word(word_text)
        phonetic_symbol = rlinput('phonetic_symbol:', word.phonetic_symbol if word else '')
        meaning = rlinput('meaning:', word.meaning if word else '')
        use_case = rlinput('use case:', word.use_case if word else '')
        remark = rlinput('remark:', word.remark if word else '')
        add_word(word_text, phonetic_symbol, meaning, use_case, remark)
    if args.command == 'review':
        begin_time = datetime.date.today() - datetime.timedelta(days=7)
        end_time = datetime.date.today() + datetime.timedelta(days=1)
        begin_to_review(begin_time, end_time)
        print('finished')
    if args.command == 'migrate':
        alembic_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alembic.ini')
        os.system("mkdir -p {}".format(DATA_DIR))
        os.system("alembic -c {} upgrade head".format(alembic_config))
    if args.command == 'predict':
        show_predict()

if __name__ == '__main__':
    run()
