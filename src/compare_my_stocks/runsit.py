import logging
from pathlib import Path
import sys
import time
from functools import partial

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSplashScreen


#nothing here uses config. important

from common.common import Types, UniteType, need_add_process, InputSourceType

from common.loghandler import init_log
from common.simpleexceptioncontext import simple_exception_handling, SimpleExceptionContext


import psutil, os




class MainClass:
    def __init__(self, UseWX=None, UseWEB=None, UseQT=None, SimpleMode=None):
        self.UseWX = UseWX
        self.UseWEB = UseWEB
        self.UseQT = UseQT
        self.SimpleMode = SimpleMode

        self.config= None

    def selectmode(self):
        import matplotlib
        matplotlib.interactive(True)
        if self.UseWX:
            matplotlib.use('WxAgg')
        elif self.UseWEB:
            matplotlib.use('WebAgg')
        elif self.UseQT:
            matplotlib.use('QtAgg')
        else:
            matplotlib.use('TKAgg')

    def initialize_graph_and_ib(self, axes=None):
        if self.SimpleMode:
            self.selectmode()
        from engine.compareengine import CompareEngine
        gg = CompareEngine(axes)
        return  gg

    def pd_ignore_warning(self):
        import warnings
        from pandas.errors import SettingWithCopyWarning
        warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

    @classmethod
    def kill_proc_tree(self, pid, including_parent=True):
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        gone, still_alive = psutil.wait_procs(children, timeout=5)
        if including_parent:
            parent.kill()
            parent.wait(5)

    @classmethod
    def killallchilds(self,x=None, tolog=True):
        if tolog:
            logging.info(("killed"))
        from ib.remoteprocess import RemoteProcess
        proc=RemoteProcess()
        if proc.proc:
            try:
                self.kill_proc_tree(proc.proc.pid)
            except:
                pass
        self.kill_proc_tree(os.getpid())

    @simple_exception_handling(err_description="hide_if_needed")
    def hide_if_needed(self,force):
        if not (os.name == 'nt'):
            logging.info("Not hiding window because it is not windows (not implemented)")
            return
        def check_conditions():
            if not os.name== 'nt':
                return False #not implemented
            if os.environ.get('PYCHARM_HOSTED') == '1':
                return False
            if force:
                return True
            if not self.config.Running.DisplayConsole:
                if 'python' in os.path.basename(sys.executable):
                    logging.info("Not hiding window because it is python")
                    return False
                import psutil

                # Get the parent process
                with SimpleExceptionContext(err_description='resolve parent',never_throw=True):
                    parent =psutil.Process().parent().name()

                    if ('explorer.exe' != parent.lower()):
                        logging.info("Not hiding window because parent is {}".format(parent))
                        return False
                    logging.debug('parent is explorer.exe, hiding')
                    return True
                logging.info('Not hiding because of exception resolving parent process')
                return False
            return False

        if check_conditions():
            import win32gui, win32con
            the_program_to_hide = win32gui.GetForegroundWindow()
            wndw_title = win32gui.GetWindowText(the_program_to_hide)
            if "compare" in wndw_title.lower(): #we don't want cmd etc.
                win32gui.ShowWindow(the_program_to_hide, win32con.SW_HIDE)
                logging.info('Hiding window')

            else:
                logging.info("Not hiding window because of title: " + wndw_title)
                logging.info("but will say we did")
            return True
        else:
            logging.debug("Not hiding")
        return False

    def get_scale_factor(self):
        import ctypes
        #scaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        #g1= 1/scaleFactor

        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        if abs( screensize[0] /screensize[1] - 1920/1080)>0.01:
            logging.warning("Screen resolution is not 1920x1080. This may cause problems. Adapting width.")


        return round(min(screensize[0]/1920,screensize[1]/1080),2)

    def main(self, console=False, ibconsole=False, debug=False,noconsole=False):
        # First we do logging to see what is going on
        #Then init_log to have basic formatting
        # Then we import config. SILENT should be false.
        # config calls init_log again with the right parameters.
        #logging.getLogger().setLevel(logging.INFO if not debug else logging.DEBUG)


        init_log(debug=debug)




        from config import config
        self.config = config


        self.UseWX, self.UseWEB, self.UseQT, self.SimpleMode \
        = config.UI.UseWX, config.UI.UseWEB, config.UI.UseQT, config.UI.SimpleMode
        config.Running.StartIbsrvInConsole = config.Running.StartIbsrvInConsole or ibconsole
        config.Running.Debug = config.Running.Debug or debug

        hiding=False
        if not console:
            hiding=self.hide_if_needed(noconsole)


        with SimpleExceptionContext(err_description="no win32api",detailed=False):
            import win32api
            win32api.SetConsoleCtrlHandler(MainClass.killallchilds, True)
        logging.info("Started")




        #import signal
        #signal.signal(signal.SIGTERM,
        if config.Sources.IBSource.AddProcess and need_add_process(config):
            from ib.remoteprocess import RemoteProcess
            succ=RemoteProcess().run_additional_process()
            for i in range(2):
                if succ:
                    break 
                import sys
                if 'python' in os.path.basename(sys.executable) and config.Sources.IBSource.UsePythonIfNotResolve:
                    config.Sources.IBSource.AddProcess= [sys.executable ,'-m compare_my_stocks --ibsrv']
                    succ=RemoteProcess().run_additional_process()
            else:
                config.Input.InputSource=InputSourceType.Cache
                logging.warn("Failed to start IBSrv. using cache instead")

        self.pd_ignore_warning()

        if self.UseQT:
            from PySide6.QtWidgets import QApplication
            from PySide6 import QtCore
            app = QApplication([])
            from .gui.mainwindow import MainWindow



            import os
            if config.Running.TryToScaleDisplay:
                os.environ['QT_SCALE_FACTOR']='%s' % self.get_scale_factor()
                logging.debug("QT_SCALE_FACTOR is %s" % os.environ['QT_SCALE_FACTOR'])

            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

            if hiding:
                path = os.fspath(Path(__file__).resolve().parent / "gui" / "splash.png")
                pixmap = QPixmap(path)
                splash = QSplashScreen(pixmap)
                splash.show()
            app.processEvents()
            app.aboutToQuit.connect(self.killallchilds)
            # from ib_insync import util
            # util.UseQT()
            # util.patchAsyncio()

        if not self.SimpleMode:
            from .gui.mainwindow import MainWindow
            mainwindow = MainWindow()

        
        from engine.parameters import Parameters


        gg = self.initialize_graph_and_ib(mainwindow.axes if not self.SimpleMode else None)

        gg.gen_graph(Parameters(
            type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=config.DefaultParams.DefaultGroups, use_cache=config.DefaultParams.CacheUsage,
            show_graph=False))
        #those parameters sets the default UI controls. Probably should be in config, though most of it is.
        # I do some assumptions on it later.

        if self.SimpleMode:
            from matplotlib import pyplot as plt
            plt.draw()  # no app , bitches
        elif self.UseQT:
            mainwindow.run(gg)
            #import QCore
            app.aboutToQuit.connect(partial(mainwindow.closeEvent,0))
            #import Qt
            #Qt.QtCo
            if hiding:
                splash.finish(mainwindow)

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
