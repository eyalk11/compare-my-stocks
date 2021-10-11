# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication, QMainWindow,QTabWidget,QVBoxLayout
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from superqt import QLabeledSlider
#from supportwidgets import get_options_from_groups
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT as NavigationToolbar
from superqt.sliders._labeled import LabelPosition

from daterangeslider import QDateRangeSlider
from formobserver import FormObserver, FormInitializer
from graphgateway import initialize_graph_and_ib
from parameters import Parameters
from common import Types, UseCache

try:
    import config
except Exception as e :
    print('please rename exampleconfig to config and adjust accordingly')
    sys.exit(1)





class MplCanvas(FigureCanvasQTAgg):

    def __init__(self,axes, parent=None):
        #QWidget.__init__(parent)
        #fig = Figure(figsize=(width, height), dpi=dpi)

        self.axes = axes #fig.add_subplot(111)
        super(MplCanvas, self).__init__(axes.figure)


class MainWindow(QMainWindow, FormInitializer):
    def __init__(self):
        super(MainWindow, self).__init__()
        FormObserver.__init__(self)
        self.load_ui()


    def load_ui(self):
        loader = QUiLoader()
        loader.registerCustomWidget(QDateRangeSlider)
        path = os.fspath(Path(__file__).resolve().parent / "mainwindow2.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)

        self.window= loader.load(ui_file, None)

        ui_file.close()
        self.setCentralWidget(self.window)

    def run(self):
        self._graphObj = initialize_graph_and_ib()
        #self.replace_widgets()
        self._graphObj.gen_graph(Parameters(
            type=Types.PRICE, isline=True,groups=['FANG'],mincrit=-100000,maxnum=4000,use_cache=config.CACHEUSAGE,show_graph=False))

        self.setup_init_values()
        self.setup_observers()

        self.prepare_graph_widget()

        self.show()

    def prepare_graph_widget(self):
        tabWidget = self.window.tabWidget_8Page1  # type: QTabWidget
        if len(self._graphObj._linesandfig)==0:
            print('no cant do. No initial graph generated.')
            return
        sc = MplCanvas(self._graphObj._linesandfig[-1][2], self)
        toolbar = NavigationToolbar(sc, self.window)
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(sc)
        tabWidget.setLayout(layout)

    def replace_widgets(self):
        self.window.max_num=QLabeledSlider(parent=self.window.max_num.parent(),LabelPosition=LabelPosition.LabelsRight,layout=self.window.max_num.layout())



if __name__ == "__main__":
    app = QApplication([])
    mainwindow=MainWindow()
    mainwindow.run()
    sys.exit(app.exec_())
