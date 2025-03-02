# 1️⃣ Install kokoro
# pip install -q kokoro>=0.7.11 soundfile
# pip install
# 2️⃣ Install espeak, used for English OOD fallback and some non-English languages
# !apt-get -qq -y install espeak-ng > /dev/null 2>&1
# 🇪🇸 'e' => Spanish es
# 🇫🇷 'f' => French fr-fr
# 🇮🇳 'h' => Hindi hi
# 🇮🇹 'i' => Italian it
# 🇧🇷 'p' => Brazilian Portuguese pt-br

# 3️⃣ Initalize a pipeline
import os
from kokoro import KPipeline
from IPython.display import display, Audio
import soundfile as sf
import torch
from parrot_v2.util import logger

pt_model_dir = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'voice_pt')

cn_voice = 'zf_xiaoyi'
en_voice = 'af_heart'

# 🇺🇸 'a' => American English, 🇬🇧 'b' => British English
# 🇯🇵 'j' => Japanese: pip install misaki[ja]
# 🇨🇳 'z' => Mandarin Chinese: pip install misaki[zh]
# <= make sure lang_code matches voice
cn_pipeline = KPipeline(lang_code=cn_voice[0])
en_pipeline = KPipeline(lang_code=en_voice[0])

# This text is for demonstration purposes only, unseen during training
# text = '''
# The sky above the port was the color of television, tuned to a dead channel.
# "It's not like I'm using," Case heard someone say, as he shouldered his way through the crowd around the door of the Chat. "It's like my body's developed this massive drug deficiency."
# It was a Sprawl voice and a Sprawl joke. The Chatsubo was a bar for professional expatriates; you could drink there for a week and never hear two words in Japanese.

# These were to have an enormous impact, not only because they were associated with Constantine, but also because, as in so many other areas, the decisions taken by Constantine (or in his name) were to have great significance for centuries to come. One of the main issues was the shape that Christian churches were to take, since there was not, apparently, a tradition of monumental church buildings when Constantine decided to help the Christian church build a series of truly spectacular structures. The main form that these churches took was that of the basilica, a multipurpose rectangular structure, based ultimately on the earlier Greek stoa, which could be found in most of the great cities of the empire. Christianity, unlike classical polytheism, needed a large interior space for the celebration of its religious services, and the basilica aptly filled that need. We naturally do not know the degree to which the emperor was involved in the design of new churches, but it is tempting to connect this with the secular basilica that Constantine completed in the Roman forum (the so-called Basilica of Maxentius) and the one he probably built in Trier, in connection with his residence in the city at a time when he was still caesar.

# [Kokoro](/kˈOkəɹO/) is an open-weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost-efficient. With Apache-licensed weights, [Kokoro](/kˈOkəɹO/) can be deployed anywhere from production environments to personal projects.
# '''
# text = '「もしおれがただ偶然、そしてこうしようというつもりでなくここに立っているのなら、ちょっとばかり絶望するところだな」と、そんなことが彼の頭に思い浮かんだ。'
# text = '中國人民不信邪也不怕邪，不惹事也不怕事，任何外國不要指望我們會拿自己的核心利益做交易，不要指望我們會吞下損害我國主權、安全、發展利益的苦果！'
# text = 'Los partidos políticos tradicionales compiten con los populismos y los movimientos asamblearios.'
# text = 'Le dromadaire resplendissant déambulait tranquillement dans les méandres en mastiquant de petites feuilles vernissées.'
# text = 'ट्रांसपोर्टरों की हड़ताल लगातार पांचवें दिन जारी, दिसंबर से इलेक्ट्रॉनिक टोल कलेक्शनल सिस्टम'
# text = "Allora cominciava l'insonnia, o un dormiveglia peggiore dell'insonnia, che talvolta assumeva i caratteri dell'incubo."
# text = 'Elabora relatórios de acompanhamento cronológico para as diferentes unidades do Departamento que propõem contratos.'

# 4️⃣ Generate, display, and save audio files in a loop.
# generator = pipeline(
#     text, voice=voice, # <= change voice here
#     speed=1, _SPLIT_PATTERN=r'\n+'
# )

# text = '中國人民不信邪也不怕邪，不惹事也不怕事，任何外國不要指望我們會拿自己的核心利益做交易，不要指望我們會吞下損害我國主權、安全、發展利益的苦果！'
# text = '命令中 Python 的版本可以根据需要自行更改。我比较喜欢指定环境安装位置在项目根目录，方便后期打包备份。如果不准备在其他电脑上运行也可以用 -n 参数创建一个命名环境，这个环境一般会保存在当前电脑用户的文件夹下。'
# text = 'than they were uh last year and we have uh a lot of fixed short short-term Investments that are very responsive to the changes in interest[ˈɪn.trɪst] rates so that'


# Alternatively, load voice tensor directly:
cn_voice_tensor = torch.load(
    f'{pt_model_dir}/{cn_voice}.pt', weights_only=True)
en_voice_tensor = torch.load(
    f'{pt_model_dir}/{en_voice}.pt', weights_only=True)

_SAMPLE_RATE = 24000
_SPLIT_PATTERN = r'\n+'
# _SPLIT_PATTERN = r'。+'


print('tts module initialized')


def gen_cn_mp3(text, outpath: str) -> str:
    text = text.replace('\n', ' ')

    cn_generator = cn_pipeline(
        text, voice=cn_voice_tensor,
        speed=1, split_pattern=_SPLIT_PATTERN
    )

    for i, (gs, ps, audio) in enumerate(cn_generator):
        sf.write(outpath, audio, _SAMPLE_RATE, compression_level=.99)


def gen_en_mp3(text, outpath: str) -> str:
    text = text.replace('\n', ' ')

    en_generator = en_pipeline(
        text, voice=en_voice_tensor,
        speed=1, split_pattern=_SPLIT_PATTERN
    )
    for i, (gs, ps, audio) in enumerate(en_generator):
        sf.write(outpath, audio, _SAMPLE_RATE, compression_level=.99)
    logger.info(f'torch allocated {torch.cuda.memory_allocated()}')
