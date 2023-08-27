import logging
import sys
import time
from functools import partial


from common.common import Types, UniteType, need_add_process, simple_exception_handling
from common.loghandler import init_log
from config import config
from ib.remoteprocess import RemoteProcess

USEWX, USEWEB, USEQT, SIMPLEMODE = config.UI.USEWX, config.UI.USEWEB, config.UI.USEQT, config.UI.SIMPLEMODE
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
    if proc.proc:
        try:
            kill_proc_tree(proc.proc.pid)
        except:
            pass
    kill_proc_tree(os.getpid())
    #del anotherproc

proc=RemoteProcess()

@simple_exception_handling(err_description="hide_if_needed")
def hide_if_needed():
    if (not config.Running.DISPLAY_CONSOLE) and (not (os.environ.get('PYCHARM_HOSTED') == '1')):
        import win32gui, win32con

        the_program_to_hide = win32gui.GetForegroundWindow()
        wndw_title = win32gui.GetWindowText(the_program_to_hide);
        if "compare-my-stocks.exe" in wndw_title:
            win32gui.ShowWindow(the_program_to_hide, win32con.SW_HIDE)
            logging.info('Hidding window')
        else:
            logging.info("Not hiding window because of title: " + wndw_title)
    else:
        logging.debug("Not hiding")
def main(console=False,ibconsole=False,debug=False):

    #logging.getLogger().setLevel(logging.INFO)
    init_log()
    if not console:
        hide_if_needed()

    config.Running.START_IBSRV_IN_CONSOLE = config.Running.START_IBSRV_IN_CONSOLE or ibconsole
    config.Running.DEBUG = config.Running.DEBUG  or debug

    import win32api
    win32api.SetConsoleCtrlHandler(func, True)
    logging.info("Started")



    #import signal
    #signal.signal(signal.SIGTERM,
    if config.IBConnection.ADDPROCESS and need_add_process(config):
        proc.run_additional_process()

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
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=config.DefaultParams.DefaultGroups, use_cache=config.DefaultParams.CACHEUSAGE,
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

