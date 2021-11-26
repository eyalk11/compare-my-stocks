import sys
import time

import matplotlib
from matplotlib import pyplot as plt

from common.common import InputSourceType, Types
from config import config
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from ib.ibtest import main as ibmain

from gui.mainwindow import MainWindow

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
        ibmain(False)

    gg = CompareEngine(config.FN)
    return  gg

if __name__ == "__main__":
    if USEQT:
        app = QApplication([])

    gg = initialize_graph_and_ib()
    gg.gen_graph(Parameters(
        type=Types.PRICE, isline=True, groups=['FANG'], use_cache=config.CACHEUSAGE,
        show_graph=False))

    if not SIMPLEMODE:
        mainwindow= MainWindow(gg)
        mainwindow.run()
    else:
        plt.draw()  #no app , bitches
    if USEQT:
        sys.exit(app.exec_())
        a=1
    else:
        #simple, should be ok.
        while(1):
            time.sleep(1)



