import logging
import os
from compare_my_stocks.common.common import Serialized
from config import config
import pickle
logging.getLogger().setLevel(logging.ERROR)


def load_data() -> Serialized:
    if os.path.exists(config.DATAFILEPTR):
        filename =open(config.DATAFILEPTR,'rt').read()
        if os.path.exists(filename):
            data: Serialized = pickle.load(open(filename, 'rb'))
            return data

    logging.error(('data file not available'))

def display_graph():
    pass
