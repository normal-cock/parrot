# coding=utf8

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sqlite_url = 'sqlite:///{}/.parrot/dictionary.db'.format(os.environ['HOME'], )
engine = create_engine(sqlite_url)
Session = sessionmaker(bind=engine)
# print(sqlite_url)