# coding=utf8
from parrot_v2.util import rlinput, logger
from parrot_v2 import DATA_DIR, MEANING_SPEECH_DIR
from parrot_v2.biz.migrate_script import import_data_from_v1
from parrot_v2.biz.service_er import (
    add_er_lookup_record,
    begin_er_lookup_review,
    predict_er,
)
from parrot_v2 import DEBUG
from parrot_v2.biz.service_v2 import (
    add_item,
    get_meaning,
    gen_speech_4_meaning,
)
from parrot_v2.biz.service import (
    get_word_or_none,
    add_new_word_and_meaning,
    add_new_meaning_to_exist_word,
    modify_exist_meaning,
    modify_exist_word,
    begin_to_review_v4,
    show_predict_v2,
    search,
    rebuild_fts,
    get_report_stats,
)
from parrot_v2 import Session
import signal
import datetime
import argparse
from parrot_v2.model import Word, Meaning, ERLookupRecord
import time
import os
import sys

# print(f'{__file__}:{sys._getframe().f_lineno}', time.time())
# 定义信号处理函数


def handler(signum, frame):
    print("\n\nExit")
    exit()


def init_signal():
    signal.signal(signal.SIGINT, handler)


def run():
    """parrot_v2命令行入口"""
    init_signal()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "add",
            "review",
            "search",
            "migrate",
            "query_word",
            "report",
            "rebuild_fts",
            "modify_word",
            "modify_meaning",
            "add_er",
            "review_er",
            "predict_er",
            "predict",
            "import_v1_data",
            "add_item",
            "gen_tts",
            "gen_tts_all",
            "initialize",
        ],
    )
    args = parser.parse_args()

    if args.command == "initialize":
        os.system("rm -r {}".format(DATA_DIR))
    if args.command == "add":
        word_text = rlinput("word_text:", "").strip()
        if not word_text:
            exit("Error: empty word")

        word = get_word_or_none(word_text)

        meaning_obj = None
        if word != None:
            tmp_meaning_dict = {}
            print("found the following existing meanings:")
            for i, meaning in enumerate(word.meanings):
                print("{}. {}".format(i + 1, meaning.meaning))
                tmp_meaning_dict[str(i + 1)] = meaning
            meaning_choice = rlinput(
                "input existing meaning index(-1 to add a new meaning):", "-1"
            ).strip()
            if meaning_choice != "-1" and meaning_choice not in tmp_meaning_dict:
                exit("Error: invalid index")

            if meaning_choice != "-1":
                meaning_obj = tmp_meaning_dict[meaning_choice]

        phonetic_symbol = rlinput(
            "phonetic_symbol:", meaning_obj.phonetic_symbol if meaning_obj else ""
        ).strip()
        meaning = rlinput(
            "meaning:", meaning_obj.meaning if meaning_obj else ""
        ).strip()
        use_case = rlinput(
            "use case:", meaning_obj.use_case if meaning_obj else ""
        ).strip()
        remark = rlinput("remark:", meaning_obj.remark if meaning_obj else "").strip()
        use_case_voice = rlinput(
            "use case voice:", meaning_obj.use_case_voice if meaning_obj else ""
        ).strip()

        if word == None:
            add_new_word_and_meaning(
                word_text, phonetic_symbol, meaning, use_case, remark, use_case_voice
            )
        elif meaning_obj == None:
            add_new_meaning_to_exist_word(
                word.id, phonetic_symbol, meaning, use_case, remark, use_case_voice
            )
        else:
            modify_exist_meaning(
                meaning_obj.id,
                phonetic_symbol,
                meaning,
                use_case,
                remark,
                use_case_voice,
            )
    if args.command == "review":
        begin_time = datetime.date.today() - datetime.timedelta(days=60)
        end_time = datetime.date.today() + datetime.timedelta(days=1)
        # if DEBUG:
        #     begin_to_review_v4(begin_time, end_time)
        # else:
        #     begin_to_review_v3(begin_time, end_time)
        begin_to_review_v4(begin_time, end_time)

    if args.command == "search":
        query = rlinput("word_text:", "").strip().lower()
        # print("search:", query)
        search(query)
    if args.command in ["initialize", "migrate"]:
        alembic_config = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "alembic.ini"
        )
        os.system("mkdir -p {}".format(DATA_DIR))
        os.system("mkdir -p {}".format(MEANING_SPEECH_DIR))
        os.system("alembic -c {} upgrade head".format(alembic_config))
        rebuild_fts()
    if args.command == "rebuild_fts":
        rebuild_fts()
    if args.command == "predict":
        show_predict_v2()
    if args.command == "import_v1_data":
        import_data_from_v1()
    if args.command == "add_er":
        add_er_lookup_record()
    if args.command == "review_er":
        begin_er_lookup_review()
    if args.command == "predict_er":
        predict_er()
    if args.command == "modify_word":
        target_word_text = rlinput("word_text:", "").strip()
        word = get_word_or_none(target_word_text)
        if word == None:
            exit(f'word "{target_word_text}" not found')

        new_word_text = rlinput("new_word_text:", word.text).strip()

        modify_exist_word(word.id, new_word_text)
    if args.command == "modify_meaning":
        word_text = rlinput("word_text:", "").strip()
        if not word_text:
            exit("Error: empty word")

        session = Session()
        word = session.query(Word).filter(Word.text == word_text).one_or_none()
        # word = get_word_or_none(word_text)
        if word == None:
            exit(f"word not found")

        tmp_meaning_dict = {}
        print("found the following existing meanings:")
        for i, meaning in enumerate(word.meanings):
            print("{}. {}".format(i + 1, meaning.meaning))
            tmp_meaning_dict[str(i + 1)] = meaning
        meaning_choice = rlinput("input existing meaning index:", "1").strip()
        if meaning_choice not in tmp_meaning_dict:
            exit("Error: invalid index")

        meaning_obj = tmp_meaning_dict[meaning_choice]

        phonetic_symbol = rlinput(
            "phonetic_symbol:", meaning_obj.phonetic_symbol if meaning_obj else ""
        ).strip()
        meaning = rlinput(
            "meaning:", meaning_obj.meaning if meaning_obj else ""
        ).strip()
        use_case = rlinput(
            "use case:", meaning_obj.use_case if meaning_obj else ""
        ).strip()
        remark = rlinput("remark:", meaning_obj.remark if meaning_obj else "").strip()
        use_case_voice = rlinput(
            "use case voice:", meaning_obj.use_case_voice if meaning_obj else ""
        ).strip()

        modify_exist_meaning(
            meaning_obj.id,
            phonetic_symbol,
            meaning,
            use_case,
            remark,
            use_case_voice,
            unremember=False,
        )
    if args.command == "query_word":
        word_text = rlinput("word_text:", "").strip().lower()
        if not word_text:
            exit("Error: empty word")

        word = get_word_or_none(word_text)
        if word == None:
            exit(f"word not found")

        print("found the following existing meanings:")
        for i, meaning in enumerate(word.meanings):
            print(
                "\n{}. {} {}".format(i + 1, meaning.word.text, meaning.phonetic_symbol)
            )
            print("meaning_id:", meaning.id)
            print("meaning:", meaning.meaning)
            print(f"use case: {meaning.use_case}")
            print(f"remark: {meaning.remark}")
            print(f"use_case_voice: {meaning.use_case_voice}")

            print(f'create time: {meaning.created_time.strftime("%Y-%m-%d %H:%M")}')

    if args.command == "report":
        report_stats = get_report_stats()
        print(
            f"""Study Report:\n You have learnt {report_stats['word_count']} words"""
            f""", {report_stats['meaning_count']} meanings, {report_stats['review_plan_count']} times of review"""
        )
    if args.command == "add_item":
        item_name = rlinput("Item Name:", "").strip()
        if not item_name:
            exit("Error: empty item name")
        item_id = rlinput(
            "Item ID(leave empty for auto generation):", item_name
        ).strip()
        item_type = int(
            rlinput("Item Type(1:MP3 only 2:MP4+MP3 3:M3U8+MP4+MP3):", "3").strip()
        )
        adjustment = float(
            rlinput("Subtitle Adjustment(negative is allowed):", "0").strip()
        )
        add_item(
            item_name=item_name,
            item_id=item_id,
            adjustment=adjustment,
            item_type=item_type,
        )
        print("Item added")

    if args.command == "gen_tts":
        meaning_id = rlinput("meaning id:", "").strip()
        if not meaning_id.isdigit():
            exit("Error: invalid meaning id")
        meaning = get_meaning(meaning_id)
        if meaning == None:
            exit("Error: meaning not found")
        print(gen_speech_4_meaning(meaning_id))

    if args.command == "gen_tts_all":
        os.environ["LRU_CACHE_CAPACITY"] = "1"
        session = Session()
        er_records = (
            session.query(ERLookupRecord)
            .order_by(ERLookupRecord.created_time.desc())
            .all()
        )
        logger.info(f"total {len(er_records)}")
        gened_count = 0
        for record in er_records:
            if gened_count >= 50:
                break
            err_string = gen_speech_4_meaning(record.meaning_id)
            if len(err_string) == 0:
                logger.info(f"gen speech for meaning {record.meaning_id} succeed")
                gened_count += 1
        logger.info(f"gened {gened_count} speeches")
        session.close()


if __name__ == "__main__":
    run()
