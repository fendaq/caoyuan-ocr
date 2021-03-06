import sys

import os

sys.path.append(os.path.realpath('..'))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config.common_config import config
from config.common_config import logger

mongo_config = config['mongo']


def get_db(host=mongo_config['host'],
           port=mongo_config['port'],
           database=mongo_config['database'],
           username=mongo_config['username'],
           password=mongo_config['password']):
    if username is None or password is None:
        uri = "mongodb://%s:%d/%s" % (host, port, database)
    else:
        uri = "mongodb://%s:%s@%s:%d/%s" % (username, password, host, port, database)

    try:
        client = MongoClient(uri)
        db = client[database]
    except ConnectionFailure as e:
        logger.info("Could not connect to MongoDB: %s" % e)
    return db
