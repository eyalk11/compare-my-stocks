import logging
# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys

import PySide6
from PySide6.QtWidgets import QMainWindow
from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from superqt.sliders._labeled import EdgeLabelMode
from superqt import QLabeledRangeSlider
from qtvoila import QtVoila

from engine.symbolsinterface import SymbolsInterface
from gui.daterangeslider import QDateRangeSlider
from gui.forminitializer import FormInitializer

try:
    from config import config
except Exception as e :
    logging.debug(('please set a config file'))
    sys.exit(1)


from superqt import QLabeledDoubleRangeSlider

#from noconflict import classmaker
from six import with_metaclass

class MainWindow(QMainWindow, FormInitializer):

    def __init__(self):

        super(MainWindow, self).__init__()
        FormInitializer.__init__(self)


        self.load_ui()

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
        path = os.fspath(Path(__file__).resolve().parent / "mainwindow.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)

        self.window= loader.load(ui_file, None)
        self.window.closeEvent= self.closeEvent
        ui_file.close()
        self.setCentralWidget(self.window)
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


