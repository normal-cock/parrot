from flask import Flask
from flask import render_template, make_response
from markupsafe import Markup
from parrot_v2.dal.aliyun_oss import oss_sington
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route("/<passport>")
def hello_world(passport):
    if passport.upper() != 'Rkf7br9rmUMB'.upper():
        return make_response('', 404)
    # file_name = 'audio'
    file_name = 'test2'
    subtitle_url = Markup(oss_sington.get_object_url(f'{file_name}.vtt'))
    audio_url = Markup(oss_sington.get_object_url(f'{file_name}.mp3'))
    video_url = Markup('')
    # app.logger.info(f'subtitle_url={subtitle_url}||audio_url={audio_url}')
    return render_template(
        'player.html',
        subtitle_url=subtitle_url,
        audio_url=audio_url,
        video_url=video_url,
    )
