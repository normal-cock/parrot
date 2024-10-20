import json
import time
from cachelib.file import FileSystemCache
from flask import Flask, session, request
from flask import render_template, make_response
from flask_session import Session
from markupsafe import Markup
from parrot_v2.dal.aliyun_oss import oss_sington
from werkzeug.middleware.proxy_fix import ProxyFix
from parrot_v2 import DATA_DIR, PW, cache, CustmLocalCache
from parrot_v2.biz import service_v2 as biz_v2
from parrot_v2.biz import service_er as biz_er
from parrot_v2.util import logger, nlp_tool
from flask_paginate import Pagination, get_page_parameter

# app = Flask(__name__)
from parrot_v2 import app

SESSION_TYPE = 'cachelib'
SESSION_SERIALIZATION_FORMAT = 'json'
SESSION_CACHELIB = FileSystemCache(
    threshold=500, cache_dir=f"{DATA_DIR}/sessions")
app.config.from_object(__name__)
Session(app)

cache_in_flask = cache

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route("/<passport>")
def index(passport):
    if passport.upper() != PW.upper():
        return make_response('', 404)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    item_total = biz_v2.get_item_total()
    pagination = Pagination(page=page, total=item_total, css_framework='bootstrap5',
                            search=False, record_name='items')
    offsite = (page - 1) * pagination.per_page
    item_list = biz_v2.get_item_list(offsite, pagination.per_page)

    return render_template(
        'index.html',
        items=item_list,
        passport=passport,
        pagination=pagination,
    )


@app.route("/<passport>/<item_id>")
def item_play_page(passport, item_id):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    _media_url_key = f'media_url_dict:{item_id}'
    media_url_dict = json.loads(session.get(_media_url_key, '{}'))
    if not ('expiration_time' in media_url_dict and time.time() < media_url_dict['expiration_time']):
        media_url_dict, err_string = biz_v2.get_media_url(item_id)
        if len(err_string) != 0:
            logger.error(err_string)
            return make_response(err_string, 404)
        # logger.info(f'regened media url:{media_url_dict}')
        logger.info(f'regened media url')
        session[_media_url_key] = json.dumps(media_url_dict)
    else:
        # logger.info(f'reuse media url:{media_url_dict}')
        logger.info(f'reuse media url')
    subtitle_url = Markup(media_url_dict['subtitle_url'])
    subtitle_url_2 = Markup(media_url_dict.get('subtitle_url_2', ''))
    # audio_url = Markup(media_url_dict['audio_url'])
    audio_url = Markup('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8')
    audio_type = Markup('audio/mp3')
    audio_type = Markup('application/x-mpegURL')
    # video_url = Markup(media_url_dict['video_url'])
    video_url = Markup('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8')
    video_type = Markup('video/mp4')
    adjust_time = media_url_dict.get('adjustment', 10)
    return render_template(
        'player.html',
        item_id=item_id,
        subtitle_url=subtitle_url,
        subtitle_url_2=subtitle_url_2,
        audio_url=audio_url,
        audio_type=audio_type,
        video_url=video_url,
        video_type=video_type,
        adjust_time=adjust_time,
        passport=passport,
    )


@app.route("/<passport>/review-page")
def review_page(passport):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    return render_template(
        'review.html',
        passport=passport,
    )


@app.route("/<passport>/search/<q>")
def search(passport, q):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    result_list = biz_v2.blur_search(q.strip())
    resp_list = []
    for result in result_list:
        resp_list.append({
            'word': result[0],
            'meaning_id': result[1],
            'meaning': result[2],
            'usecase': result[3],
            'phonetic_symbol': result[4],
            'remark': result[5],
            'created_time': result.created_time.strftime("%Y-%m-%d %H:%M"),
        })

    return resp_list


@app.route("/<passport>/queryword/<q>")
def query_word(passport, q):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    result_list = biz_v2.query_word(q.strip())
    resp_list = []
    for result in result_list:
        resp_list.append({
            'word': result[0],
            'meaning_id': result[1],
            'meaning': result[2],
            'usecase': result[3],
            'phonetic_symbol': result[4],
            'remark': result[5],
            'created_time': result[6].strftime("%Y-%m-%d %H:%M"),
        })
    return resp_list


@app.route("/<passport>/readd-er/<m_id>", methods=['POST'])
def readd_er(passport, m_id):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    if m_id.isdigit() == False:
        return make_response('', 400)
    err_str = biz_v2.readd_er(int(m_id))
    if len(err_str) != 0:
        return make_response(err_str, 400)
    return 'readd succeed'


@app.route("/<passport>/parsestc", methods=['POST'])
def parse_sentence(passport):
    '''
        qr_result: {
            'raw_word':'',
            'word':'', # cleaned word
            'qr_list':[{'pron':'', 'cn_def':'',}],
        }
        return {
            'raw_sentence':'',
            'selected':qr_result,
            'unknown_words':[qr_result, qr_result],
        }
    '''
    if passport.upper() != PW.upper():
        return make_response('', 404)
    selected = request.form.get('selected')
    sentence = request.form.get('sentence')
    selected = nlp_tool.clear_fmt(selected)
    sentence = nlp_tool.clear_fmt(sentence)

    logger.info(
        f'selected={selected}||sentence={sentence}||begin biz_v2.parse_sentence')
    result_dict = biz_v2.parse_sentence(selected, sentence)

    def qr_result_gen(raw_word, word, qr_list):
        return {
            'raw_word': raw_word,
            'word': word,
            'qr_list': qr_list,
        }
    resp_dict = {}
    result_selected = result_dict['selected']
    resp_dict['selected'] = qr_result_gen(
        selected, result_selected['cleaned_word'], result_selected['qr'])
    resp_dict['raw_sentence'] = sentence
    resp_dict['unknown_words'] = []
    for raw_word, qr_list in result_dict['unknown_words'].items():
        word = ''
        if len(qr_list) > 0:
            word = qr_list[0]['word']
        resp_dict['unknown_words'].append(
            qr_result_gen(raw_word, word, qr_list)
        )
    return resp_dict


@app.route("/<passport>/fetch-review-record", methods=['GET'])
def fetch_review_record(passport):
    logger.info('begin fetch_review_record')
    if passport.upper() != PW.upper():
        return make_response('', 404)
    review_record = biz_er.fetch_next_er_lookup_record()
    if review_record == None:
        return make_response('', 204)
    return review_record


@app.route("/<passport>/complete-review-record/<review_index>", methods=['POST'])
def complete_review_record(passport, review_index):
    logger.info('begin complete_review_record')
    if passport.upper() != PW.upper():
        return make_response('', 404)

    index = int(review_index)
    if biz_er.complete_er_lookup_record_review(index) == False:
        return make_response('complete failed', 400)

    review_record = biz_er.fetch_next_er_lookup_record()
    if review_record == None:
        return make_response('', 204)
    return review_record


@app.route("/<passport>/heartbeat/<item_id>", methods=['POST'])
def heartbeat(passport, item_id):
    logger.info('begin heartbeat')
    if passport.upper() != PW.upper():
        return make_response('', 404)
    new_hb_data = request.get_json()
    if (
        new_hb_data == None or 'version' not in new_hb_data or 'cue_index' not in new_hb_data
        or 'adjust_st' not in new_hb_data or 'adjust_et' not in new_hb_data
    ):
        logger.error(f'input={new_hb_data}||400')
        return make_response('', 400)

    succeed, final_hb_data = cache_in_flask.update_item_heartbeat(
        item_id, new_hb_data)
    if succeed == False:
        logger.info(f"input={new_hb_data}||heartbeat update failed")
    return final_hb_data


@app.route("/<passport>/clear_session/<item_id>")
def clear_session(passport, item_id):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    _media_url_key = f'media_url_dict:{item_id}'
    session.pop(_media_url_key)
    return "<p>Hello, World!</p>"
