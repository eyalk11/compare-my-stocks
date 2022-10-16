import sys
import time
from functools import partial



#from matplotlib import pyplot as plt
#import Qt
from common.common import InputSourceType, Types, UniteType
from config import config

USEWX, USEWEB, USEQT, SIMPLEMODE = config.USEWX, config.USEWEB, config.USEQT, config.SIMPLEMODE
# if USEQT:
#     from PySide6.QtWidgets import QApplication

def selectmode():
    import matplotlib
    matplotlib.interactive(True)
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    elif USEQT:
        matplotlib.use('QtAgg')
    else:
        matplotlib.use('TKAgg')


def initialize_graph_and_ib(axes=None):
    if SIMPLEMODE:
        selectmode()

    # if config.INPUTSOURCE==InputSourceType.IB:
    #     try:
    #         from ib.ibtest import main as ibmain
    #     except:
    #         print("no IB. install interactive-broker-python-web-api")
    #         sys.exit(1)
    #     ibmain(False)
    from engine.compareengine import CompareEngine
    gg = CompareEngine(config.PORTFOLIOFN,axes)
    return  gg

def pd_ignore_warning():
    import warnings
    from pandas.core.common import SettingWithCopyWarning

    warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)


def main():
    from .gui.mainwindow import MainWindow
    pd_ignore_warning()

    if USEQT:
        from PySide6.QtWidgets import QApplication
        import matplotlib
        #from matplotlib import pyplot as plt
        from matplotlib import pyplot as plt
        
        #QGuiApplication.setAttribute(Qt.Qt);
        app = QApplication([])

    if not SIMPLEMODE:
        mainwindow = MainWindow()

    
    from engine.parameters import Parameters


    gg = initialize_graph_and_ib(mainwindow.axes if not SIMPLEMODE else None)

    gg.gen_graph(Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=config.CACHEUSAGE,
        show_graph=False))  # ,adjust_to_currency=True,currency_to_adjust='ILS'))

    if SIMPLEMODE:
        plt.draw()  # no app , bitches
    elif USEQT:
        mainwindow.run(gg)
        #import QCore
        app.aboutToQuit.connect(partial(mainwindow.closeEvent,0))
        #import Qt
        #Qt.QtCo
    if USEQT:
        sys.exit(app.exec_())
        a = 1
    else:
        # simple, should be ok.
        while (1):
            time.sleep(1)
