import logging
import os
from compare_my_stocks.common.common import Serialized
logging.getLogger().setLevel(logging.CRITICAL)
from config import config
import pickle



def load_data() -> Serialized:
    if os.path.exists(config.File.DATAFILEPTR):
        filename =open(config.File.DATAFILEPTR,'rt').read()
        if os.path.exists(filename):
            data: Serialized = pickle.load(open(filename, 'rb'))
            return data

    logging.error(('data file not available'))

def display_graph():
    pass
