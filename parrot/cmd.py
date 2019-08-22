# coding=utf8
import os
import argparse
import datetime
# 为了兼容 mac os
try:
    import gnureadline as readline
except ImportError:
    import readline

from parrot.interface import get_word, add_word, begin_to_review

def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
       return input(prompt)  # or raw_input in Python 2
    finally:
       readline.set_startup_hook()

def run():
    '''parrot命令行入口'''
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['add', 'review', 'migrate'])
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
        plan_generator = begin_to_review(begin_time, end_time)
        try:
            plan = next(plan_generator)
            while True:
                print('word:', plan.word.text, plan.word.phonetic_symbol)
                input()
                print('use case:', plan.word.use_case)
                input()
                print('meaning:', plan.word.meaning, plan.word.remark)
                result = input('choice[1.知道了/2.记住了/3.没记住]: (default:1)') or '1'
                plan = plan_generator.send(int(result))

        except StopIteration:
            print('finished')
    if args.command == 'migrate':
        alembic_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alembic.ini')
        os.system("mkdir -p ~/.parrot")
        os.system("alembic -c {} upgrade head".format(alembic_config))

if __name__ == '__main__':
    run()
