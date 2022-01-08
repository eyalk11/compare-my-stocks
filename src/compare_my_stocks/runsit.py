import sys
import time

import matplotlib
#from matplotlib import pyplot as plt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from matplotlib import pyplot as plt
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
#import Qt
from common.common import InputSourceType, Types, UniteType
from config import config


from .gui.mainwindow import MainWindow

USEWX, USEWEB, USEQT, SIMPLEMODE = config.USEWX, config.USEWEB, config.USEQT, config.SIMPLEMODE
if USEQT:
    from PySide6.QtWidgets import QApplication

def selectmode():
    matplotlib.interactive(True)
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    elif USEQT:
        matplotlib.use('QtAgg')
    else:
        matplotlib.use('TKAgg')


def initialize_graph_and_ib():
    if SIMPLEMODE:
        selectmode()

    if config.INPUTSOURCE==InputSourceType.IB:
        try:
            from ib.ibtest import main as ibmain
        except:
            print("no IB. install interactive-broker-python-web-api")
            sys.exit(1)
        ibmain(False)

    gg = CompareEngine(config.PORTFOLIOFN)
    return  gg

def pd_ignore_warning():
    import warnings
    from pandas.core.common import SettingWithCopyWarning

    warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)


def main():
    pd_ignore_warning()

    if USEQT:
        #QGuiApplication.setAttribute(Qt.Qt);
        app = QApplication([])
    gg = initialize_graph_and_ib()
    gg.gen_graph(Parameters(
        type=Types.PRICE, unite_by_group=UniteType.ADDPROT, isline=True, groups=['FANG'], use_cache=config.CACHEUSAGE,
        show_graph=False))  # ,adjust_to_currency=True,currency_to_adjust='ILS'))
    if not SIMPLEMODE:
        mainwindow = MainWindow(gg)
        mainwindow.run()
    else:
        plt.draw()  # no app , bitches
    if USEQT:
        sys.exit(app.exec_())
        a = 1
    else:
        # simple, should be ok.
        while (1):
            time.sleep(1)
