import logging
import sys
import time
from functools import partial


#nothing here uses config. important

from common.common import Types, UniteType, need_add_process, InputSourceType
from common.loghandler import init_log
from common.simpleexceptioncontext import simple_exception_handling


import logging
import sys
import time
from functools import partial

import psutil, os

class MainClass:
    def __init__(self, USEWX=None, USEWEB=None, USEQT=None, SIMPLEMODE=None):
        self.USEWX = USEWX
        self.USEWEB = USEWEB
        self.USEQT = USEQT
        self.SIMPLEMODE = SIMPLEMODE
        self.proc =None
        self.config= None

    def selectmode(self):
        import matplotlib
        matplotlib.interactive(True)
        if self.USEWX:
            matplotlib.use('WxAgg')
        elif self.USEWEB:
            matplotlib.use('WebAgg')
        elif self.USEQT:
            matplotlib.use('QtAgg')
        else:
            matplotlib.use('TKAgg')

    def initialize_graph_and_ib(self, axes=None):
        if self.SIMPLEMODE:
            self.selectmode()
        from engine.compareengine import CompareEngine
        gg = CompareEngine(axes)
        return  gg

    def pd_ignore_warning(self):
        import warnings
        from pandas.core.common import SettingWithCopyWarning
        warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

    def kill_proc_tree(self, pid, including_parent=True):
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        gone, still_alive = psutil.wait_procs(children, timeout=5)
        if including_parent:
            parent.kill()
            parent.wait(5)

    def func(self, x=None, tolog=True):
        if tolog:
            logging.info(("killed"))
        if self.proc.proc:
            try:
                self.kill_proc_tree(self.proc.proc.pid)
            except:
                pass
        self.kill_proc_tree(os.getpid())

    @simple_exception_handling(err_description="hide_if_needed")
    def hide_if_needed(self):
        if (not self.config.Running.DISPLAY_CONSOLE) and (not (os.environ.get('PYCHARM_HOSTED') == '1')):
            import win32gui, win32con
            the_program_to_hide = win32gui.GetForegroundWindow()
            wndw_title = win32gui.GetWindowText(the_program_to_hide)
            if "compare-my-stocks.exe" in wndw_title:
                win32gui.ShowWindow(the_program_to_hide, win32con.SW_HIDE)
                logging.info('Hiding window')
            else:
                logging.info("Not hiding window because of title: " + wndw_title)
        else:
            logging.debug("Not hiding")


    def main(self, console=False, ibconsole=False, debug=False):
        # First we do logging to see what is going on
        #Then init_log to have basic formatting
        # Then we import config. SILENT should be false.
        # config calls init_log again with the right parameters.
        logging.getLogger().setLevel(logging.INFO if not debug else logging.DEBUG)

        from common.common import Types, UniteType, need_add_process, InputSourceType

        from common.loghandler import init_log
        init_log()

        from ib.remoteprocess import RemoteProcess


        from config import config
        self.config = config
        self.proc = RemoteProcess()

        self.USEWX, self.USEWEB, self.USEQT, self.SIMPLEMODE \
        = config.UI.USEWX, config.UI.USEWEB, config.UI.USEQT, config.UI.SIMPLEMODE
        config.Running.START_IBSRV_IN_CONSOLE = config.Running.START_IBSRV_IN_CONSOLE or ibconsole
        config.Running.DEBUG = config.Running.DEBUG or debug


        if not console:
            self.hide_if_needed()


        import win32api
        win32api.SetConsoleCtrlHandler(self.func, True)
        logging.info("Started")



        #import signal
        #signal.signal(signal.SIGTERM,
        if config.IBConnection.ADDPROCESS and need_add_process(config):
            succ=self.proc.run_additional_process()
            for i in range(2):
                if succ:
                    break 
                import sys
                if 'python' in os.path.basename(sys.executable) and config.IBConnection.USE_PYTHON_IF_NOT_RESOLVE:
                    config.IBConnection.ADDPROCESS= [sys.executable ,'-m compare_my_stocks --ibsrv']
                    succ=self.proc.run_additional_process()
            else:
                config.Input.INPUTSOURCE=InputSourceType.Cache
                logging.warn("Failed to start IBSrv. using cache instead")

        self.pd_ignore_warning()

        if self.USEQT:
            from .gui.mainwindow import MainWindow
            from PySide6.QtWidgets import QApplication



            
            app = QApplication([])
            app.aboutToQuit.connect(self.func)
            # from ib_insync import util
            # util.useQt()
            # util.patchAsyncio()

        if not self.SIMPLEMODE:
            from .gui.mainwindow import MainWindow
            mainwindow = MainWindow()

        
        from engine.parameters import Parameters


        gg = self.initialize_graph_and_ib(mainwindow.axes if not self.SIMPLEMODE else None)

        gg.gen_graph(Parameters(
            type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=config.DefaultParams.DefaultGroups, use_cache=config.DefaultParams.CACHEUSAGE,
            show_graph=False))  # ,adjust_to_currency=True,currency_to_adjust='ILS'))

        if self.SIMPLEMODE:
            from matplotlib import pyplot as plt
            plt.draw()  # no app , bitches
        elif self.USEQT:
            mainwindow.run(gg)
            #import QCore
            app.aboutToQuit.connect(partial(mainwindow.closeEvent,0))
            #import Qt
            #Qt.QtCo
        if self.USEQT:
            def f():
                try:
                    app.exec_()
                except Exception as e :
                    logging.error(f'fatal error {e}')
                    raise
                logging.info(('Exit'))
            import sys
            sys.exit(f())
            a = 1
        else:
            # simple, should be ok.
            while (1):
                time.sleep(1)
