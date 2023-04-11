import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger('tornado').setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)
from compare_my_stocks.jupyter.jupytertools import load_data
data = load_data()
data