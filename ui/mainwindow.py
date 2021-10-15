# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
from PySide6.QtWidgets import QMainWindow,QTabWidget,QVBoxLayout
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from superqt import QLabeledSlider

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT as NavigationToolbar
from superqt.sliders._labeled import LabelPosition

from ui.daterangeslider import QDateRangeSlider
from ui.formobserver import FormObserver, FormInitializer

try:
    from config import config
except Exception as e :
    print('please rename exampleconfig to config and adjust accordingly')
    sys.exit(1)


from superqt import QLabeledDoubleRangeSlider


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self,axes):
        self.axes = axes
        super(MplCanvas, self).__init__(axes.figure)


class MainWindow(QMainWindow, FormInitializer):
    def __init__(self,graphObj):

        super(MainWindow, self).__init__()
        FormObserver.__init__(self)
        self._graphObj = graphObj
        self.load_ui()


    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(QDateRangeSlider)
        path = os.fspath(Path(__file__).resolve().parent / "mainwindow.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)

        self.window= loader.load(ui_file, None)

        ui_file.close()
        self.setCentralWidget(self.window)

    def run(self):
        if self._graphObj==None:
            return


        self.setup_init_values()
        self.setup_observers()

        self.prepare_graph_widget()

        self.show()

    def prepare_graph_widget(self):
        tabWidget = self.window.tabWidget_8Page1  # type: QTabWidget
        if len(self._graphObj._linesandfig)==0:
            print('no cant do. No initial graph generated.')
            return
        sc = MplCanvas(self._graphObj._linesandfig[-1][2])
        toolbar = NavigationToolbar(sc, self.window)
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(sc)
        tabWidget.setLayout(layout)

    def replace_widgets(self):
        self.window.max_num=QLabeledSlider(parent=self.window.max_num.parent(),LabelPosition=LabelPosition.LabelsRight,layout=self.window.max_num.layout())



