import logging
import os  # This Python file uses the following encoding: utf-8
from pathlib import Path
import sys

import PySide6
from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QFile, QTimer, Qt
from PySide6.QtUiTools import QUiLoader
from superqt.sliders._labeled import EdgeLabelMode
from superqt import QLabeledRangeSlider
from PySide6 import QtGui

from common.autoreloader import ModuleReloader
from qtvoila import QtVoila

from engine.symbolsinterface import SymbolsInterface
from gui.daterangeslider import QDateRangeSlider
from gui.forminitializer import FormInitializer
from qt_collapsible_section import Section

try:
    from config import config
except Exception as e :
    logging.debug(('please set a config file'))
    sys.exit(1)


from superqt import QLabeledDoubleRangeSlider

from six import with_metaclass

class MainWindow(QMainWindow, FormInitializer):

    def __init__(self):

        super(MainWindow, self).__init__()
        FormInitializer.__init__(self)


        self.load_ui()
        self._modreloader= ModuleReloader()

        #self.window.resize(w,h)

    def closeEvent(self, event):
        self.window.voila_widget.close_renderer()


    @property
    def graphObj(self) -> SymbolsInterface:
        return self._graphObj

    @graphObj.setter
    def graphObj(self, value):
        self._graphObj = value

    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(QDateRangeSlider)
        loader.registerCustomWidget(QLabeledRangeSlider)
        loader.registerCustomWidget(QLabeledDoubleRangeSlider)
        loader.registerCustomWidget(QtVoila)
        loader.registerCustomWidget(Section)
        path = os.fspath(Path(__file__).resolve().parent / "mainwindow.ui")
        iconpath = os.fspath(Path(__file__).resolve().parent / "icon.ico")

        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)

        self.window= loader.load(ui_file, None)
        self.window.closeEvent= self.closeEvent
        ui_file.close()
        self.setCentralWidget(self.window)

        self.setWindowIcon(QtGui.QIcon(iconpath))
        self.setWindowTitle(config.Running.TITLE)
        if os.name == 'nt':
            # This is needed to display the app icon on the taskbar on Windows 7
            import ctypes
            myappid = 'MyOrganization.MyGui.1.0.0' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.after_load()


    def run(self,graphObj : SymbolsInterface):
        self.graphObj = graphObj
        if self.graphObj==None:
            return

        self.prepare_sliders()
        self.setup_controls_from_params()
        self.setup_observers()

        self.showMaximized()
        if self.load_last_if_needed():
            self.update_graph(1)

        if  os.environ.get('PYCHARM_HOSTED') == '1':
            if config.Running.CHECKRELOADINTERVAL ==0:
                return
            logging.debug("checking and reloading")
            timer = QTimer(self)
            timer.setInterval(1000* config.Running.CHECKRELOADINTERVAL)
            timer.timeout.connect(self.check_reload)
            timer.start()

    def check_reload(self):
        #We check and reload all modules if they are changed, if we run on pycharm
        self._modreloader.check(True,True)

    #from PySide6.QtWidgets import QGroupBox
    #self.window.findChild(QGroupBox, name='graph_groupbox')
    #self.window.findChild(QGroupBox, name='graph_groupbox')
    def prepare_sliders(self):
        self.window.max_num: QLabeledRangeSlider
        self.window.max_num.setOrientation(PySide6.QtCore.Qt.Orientation.Horizontal)
        self.window.max_num.setEdgeLabelMode(EdgeLabelMode.NoLabel)
        self.window.min_crit : QLabeledDoubleRangeSlider
        self.window.min_crit.setOrientation(PySide6.QtCore.Qt.Orientation.Horizontal)
        self.window.min_crit.setEdgeLabelMode(EdgeLabelMode.NoLabel)
        self.window.min_crit.update()
        #self.window.min_crit.label_shift_x = 10
        #self.window.max_num.label_shift_x = 10

        pass


