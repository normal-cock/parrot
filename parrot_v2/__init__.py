# coding=utf8

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from parrot_v2.dal.local_cache import CustmLocalCache
from flask import Flask

app = Flask(__name__)

DEBUG = (os.getenv("DEBUG") == "True")
# DEBUG = True
DATA_DIR = "{}/.parrot_v2".format(os.environ['HOME'])
if DEBUG or app.debug == True:
    DATA_DIR = "{}/.parrot_v2_test".format(os.environ['HOME'])
print("work dir is:", DATA_DIR)

sqlite_url = 'sqlite:///{}/dictionary.db'.format(DATA_DIR)
# engine = create_engine(sqlite_url, echo=DEBUG)
engine = create_engine(sqlite_url)
Session = sessionmaker(bind=engine)
# print(sqlite_url)
cache = CustmLocalCache(f'{DATA_DIR}/diskcache')


PW = 'Rkf7br9rmUMB'
