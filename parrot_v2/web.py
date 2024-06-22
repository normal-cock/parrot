import json
import time
from cachelib.file import FileSystemCache
from flask import Flask, session, request
from flask import render_template, make_response
from flask_session import Session
from markupsafe import Markup
from parrot_v2.dal.aliyun_oss import oss_sington
from werkzeug.middleware.proxy_fix import ProxyFix
from parrot_v2 import DATA_DIR, PW
from parrot_v2.biz.service_v2 import get_media_url, get_item_list, get_item_total, blur_search
from parrot_v2.util import logger
from flask_paginate import Pagination, get_page_parameter

app = Flask(__name__)


SESSION_TYPE = 'cachelib'
SESSION_SERIALIZATION_FORMAT = 'json'
SESSION_CACHELIB = FileSystemCache(
    threshold=500, cache_dir=f"{DATA_DIR}/sessions")
app.config.from_object(__name__)
Session(app)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route("/<passport>")
def index(passport):
    if passport.upper() != PW.upper():
        return make_response('', 404)

    page = request.args.get(get_page_parameter(), type=int, default=1)
    item_total = get_item_total()
    pagination = Pagination(page=page, total=item_total, css_framework='bootstrap5',
                            search=False, record_name='items')
    offsite = (page - 1) * pagination.per_page
    item_list = get_item_list(offsite, pagination.per_page)

    return render_template(
        'index.html',
        items=item_list,
        pagination=pagination,
    )


@app.route("/<passport>/<item_id>")
def item_play_page(passport, item_id):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    _media_url_key = f'media_url_dict:{item_id}'
    media_url_dict = json.loads(session.get(_media_url_key, '{}'))
    if not ('expiration_time' in media_url_dict and time.time() < media_url_dict['expiration_time']):
        media_url_dict, err_string = get_media_url(item_id)
        if len(err_string) != 0:
            logger.error(err_string)
            return make_response(err_string, 404)
        logger.info(f'regened media url:{media_url_dict}')
        session[_media_url_key] = json.dumps(media_url_dict)
    else:
        logger.info(f'reuse media url:{media_url_dict}')
    subtitle_url = Markup(media_url_dict['subtitle_url'])
    subtitle_url_2 = Markup(media_url_dict.get('subtitle_url_2', ''))
    audio_url = Markup(media_url_dict['audio_url'])
    video_url = Markup(media_url_dict['video_url'])
    adjust_time = media_url_dict.get('adjustment', 10)
    return render_template(
        'player.html',
        item_id=item_id,
        subtitle_url=subtitle_url,
        subtitle_url_2=subtitle_url_2,
        audio_url=audio_url,
        video_url=video_url,
        adjust_time=adjust_time,
        passport=passport,
    )


@app.route("/<passport>/search/<q>")
def search(passport, q):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    result_list = blur_search(q)
    resp_list = []
    for result in result_list:
        resp_list.append({
            'word': result[0],
            'meaning': result[2],
            'usecase': result[3],
            'phonetic_symbol': result[4],
            'remark': result[5],
        })
    return resp_list


@app.route("/<passport>/clear_session/<item_id>")
def clear_session(passport, item_id):
    if passport.upper() != PW.upper():
        return make_response('', 404)
    _media_url_key = f'media_url_dict:{item_id}'
    session.pop(_media_url_key)
    return "<p>Hello, World!</p>"
