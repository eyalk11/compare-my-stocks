import sys, os

sys.path.insert(0,
    os.path.dirname(os.path.abspath(__file__)))
# from . import common
# from . import engine
# from . import input
# from . import gui
# from . import processing
# from . import graph
# from . import ib
# from . import config
from .runsit import main,USEWX, USEWEB, USEQT, SIMPLEMODE
#from config import config

import common
