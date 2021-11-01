import sys

import matplotlib
from PySide6.QtWidgets import QApplication

from common.common import USEWX, USEWEB, USEQT, InputSourceType, Types
from config import config
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from ib.ibtest import main as ibmain

from gui.mainwindow import MainWindow

def initialize_graph_and_ib():
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    elif USEQT:
        matplotlib.use('QtAgg')
    else:
        matplotlib.use('TKAgg')

    if config.INPUTSOURCE==InputSourceType.IB:
        ibmain(False)

    gg = CompareEngine(config.FN)
    return  gg

if __name__ == "__main__":
    app = QApplication([])
    gg = initialize_graph_and_ib()
    gg.gen_graph(Parameters(
        type=Types.PRICE, isline=True, groups=['FANG'], use_cache=config.CACHEUSAGE,
        show_graph=False))

    mainwindow= MainWindow(gg)
    mainwindow.run()
    sys.exit(app.exec_())


