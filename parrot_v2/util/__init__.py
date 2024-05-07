import logging
import readline


def rlinput(prompt: str, prefill: str = ''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)  # or raw_input in Python 2
    finally:
        readline.set_startup_hook()


logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
