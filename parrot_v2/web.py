import json
import time
from cachelib.file import FileSystemCache
from flask import Flask, session
from flask import render_template, make_response
from flask_session import Session
from markupsafe import Markup
from parrot_v2.dal.aliyun_oss import oss_sington
from werkzeug.middleware.proxy_fix import ProxyFix
from parrot_v2 import DATA_DIR
from parrot_v2.biz.service_v2 import get_media_url

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
def hello_world(passport):
    if passport.upper() != 'Rkf7br9rmUMB'.upper():
        return make_response('', 404)
    _media_url_key = 'media_url_dict'
    media_url_dict = json.loads(session.get(_media_url_key, '{}'))
    if not ('expiration_time' in media_url_dict and time.time() < media_url_dict['expiration_time']):
        media_url_dict = get_media_url()
        app.logger.info(f'regened media url:{media_url_dict}')
        session[_media_url_key] = json.dumps(media_url_dict)
    else:
        app.logger.info(f'reuse media url:{media_url_dict}')
    subtitle_url = Markup(media_url_dict['subtitle_url'])
    audio_url = Markup(media_url_dict['audio_url'])
    video_url = Markup(media_url_dict['video_url'])
    adjust_time = 0
    return render_template(
        'player.html',
        item_name=media_url_dict['item_name'],
        subtitle_url=subtitle_url,
        audio_url=audio_url,
        video_url=video_url,
        adjust_time=adjust_time,
    )


'''
data record

'''
