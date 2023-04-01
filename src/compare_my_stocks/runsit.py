import logging
import os
import subprocess
import sys
import time
from functools import partial


#from matplotlib import pyplot as plt
#import Qt
import shlex

from common.common import InputSourceType, Types, UniteType, need_add_process
from common.loghandler import init_log
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
    #         logging.debug(("no IB. install interactive-broker-python-web-api"))
    #         sys.exit(1)
    #     ibmain(False)
    from engine.compareengine import CompareEngine
    gg = CompareEngine(axes)
    return  gg

def pd_ignore_warning():
    import warnings
    from pandas.core.common import SettingWithCopyWarning

    warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
import psutil, os

def kill_proc_tree(pid, including_parent=True):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    gone, still_alive = psutil.wait_procs(children, timeout=5)
    if including_parent:
        parent.kill()
        parent.wait(5)

def func(x=None,tolog=True):
    if tolog:
        logging.info(("killed"))
    if anotherproc:
        try:
            kill_proc_tree(anotherproc.pid)
        except:
            pass
    kill_proc_tree(os.getpid())
    #del anotherproc

anotherproc=None
def main():
    init_log()

    import win32api
    win32api.SetConsoleCtrlHandler(func, True)
    logging.info("Started")
    #import signal
    #signal.signal(signal.SIGTERM,
    if hasattr(config,'ADDPROCESS') and config.ADDPROCESS and need_add_process(config):
        run_additional_process()

    pd_ignore_warning()

    if USEQT:
        from .gui.mainwindow import MainWindow
        from PySide6.QtWidgets import QApplication


        import matplotlib
        #from matplotlib import pyplot as plt

        
        #QGuiApplication.setAttribute(Qt.Qt);
        app = QApplication([])
        app.aboutToQuit.connect(func)
        # from ib_insync import util
        # util.useQt()
        # util.patchAsyncio()

    if not SIMPLEMODE:
        from .gui.mainwindow import MainWindow
        mainwindow = MainWindow()

    
    from engine.parameters import Parameters


    gg = initialize_graph_and_ib(mainwindow.axes if not SIMPLEMODE else None)

    gg.gen_graph(Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=config.CACHEUSAGE,
        show_graph=False))  # ,adjust_to_currency=True,currency_to_adjust='ILS'))

    if SIMPLEMODE:
        from matplotlib import pyplot as plt
        plt.draw()  # no app , bitches
    elif USEQT:
        mainwindow.run(gg)
        #import QCore
        app.aboutToQuit.connect(partial(mainwindow.closeEvent,0))
        #import Qt
        #Qt.QtCo
    if USEQT:
        def f():
            try:
                app.exec_()
            except Exception as e :
                logging.error(f'fatal error {e}')
                raise
            logging.info(('Exit'))
        sys.exit(f())
        a = 1
    else:
        # simple, should be ok.
        while (1):
            time.sleep(1)


def run_additional_process():
    global anotherproc
    if type(config.ADDPROCESS)==str:
        rpath= os.path.abspath(config.ADDPROCESS)
        if not os.path.exists(rpath):
            logging.error(f"IBSRV path reosolved to {rpath} which doesn't exists")
            return
        else:
            logging.info(f"IBSRV path reosolved to {rpath}")
        v = ["start" ,"/wait" ,rpath]
    else:
        v = ["start" ,"/wait" ]+config.ADDPROCESS
    logging.debug("Running " + str(v))
    anotherproc = subprocess.Popen(v,shell=True)
    # os.spawnle(os.P_NOWAIT,'python',[config.ADDPROCESS])
    time.sleep(1)
