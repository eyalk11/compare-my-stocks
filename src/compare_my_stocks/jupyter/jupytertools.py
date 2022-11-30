import os
from compare_my_stocks.common.common import Serialized
from config import config
import pickle

def load_data() -> Serialized:
    if os.path.exists(config.DATAFILEPTR):
        filename =open(config.DATAFILEPTR,'rt').read()
        if os.path.exists(filename):
            data: Serialized = pickle.load(open(filename, 'rb'))
            return data

    logging.debug(('data file not available'))

def display_graph():
    pass
