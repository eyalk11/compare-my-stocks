# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import PySide6.QtCore
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QListWidget
import PySide6.QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow,QTabWidget,QVBoxLayout
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
#from superqt import QRangeSlider,QLabeledSlider
#from supportwidgets import get_options_from_groups
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT as NavigationToolbar

#matplotlib.use('QtAgg')
from daterangeslider import QDateRangeSlider
from formobserver import FormObserver
from graphgateway import initialize_graph_and_ib
from parameters import Parameters
from common import Types, UseCache


#import superqt.sliders._labeled.QLabeledSlider



class MplCanvas(FigureCanvasQTAgg):

    def __init__(self,axes, parent=None):
        #QWidget.__init__(parent)
        #fig = Figure(figsize=(width, height), dpi=dpi)

        self.axes = axes #fig.add_subplot(111)
        super(MplCanvas, self).__init__(axes.figure)
# class _DateMixin:
#     def _type_cast(self, pos) -> datetime:
#         return matplotlib.dates.num2date(pos)

class MainWindow(QMainWindow, FormObserver):
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
        self._graphObj.gen_graph(Parameters(
            type=Types.PRICE, isline=True,groups=['FANG'],mincrit=-100000,maxnum=4000,use_cache=UseCache.FORCEUSE,show_graph=False))

        self.setup_init_values()
        self.setup_observers()

        self.prepare_graph_widget()
        self.show()

    def prepare_graph_widget(self):
        tabWidget = self.window.tabWidget_8Page1  # type: QTabWidget
        sc = MplCanvas(self._graphObj._linesandfig[-1][2], self)
        toolbar = NavigationToolbar(sc, self.window)
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(sc)
        tabWidget.setLayout(layout)


    def setup_init_values(self):

        options=list(self._graphObj.Groups.keys())
        value = self._graphObj.params.groups if self._graphObj.params.groups != None else list()


        self.window.groups.addItems( options)
        self.window.groups.setSelectionMode(PySide6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        #self.groups_changed()
        self.update_stock_list()
        self.select_rows(self.window.groups,[options.index(v) for v in value])
        self.window.max_num.setRange(-1*abs(self._graphObj.params.maxnum*2),abs(self._graphObj.params.maxnum*2))
        self.window.max_num.setRange(-1*abs(self._graphObj.params.mincrit * 2), abs(self._graphObj.params.mincrit * 2))
        self.window.max_num.setValue(self._graphObj.params.maxnum)
        self.window.min_crit.setValue(self._graphObj.params.mincrit)
        self.window.daterangepicker.update_prop()
        self.window.startdate.setDateTime(self._graphObj.mindate)
        self.window.enddate.setDateTime(self._graphObj.maxdate)
        self.window.daterangepicker.start=self._graphObj.mindate
        self.window.daterangepicker.end = self._graphObj.maxdate
        self.window.daterangepicker.update_obj()
        self.window.daterangepicker.dateValueChanged.connect(self.date_changed)
        #self.selection_changed()
        #self.refernced_changed()

    def update_stock_list(self):
        alloptions= list(self._graphObj._alldates.keys()) #CompareEngine.get_options_from_groups([g for g in CompareEngine.Groups])
        for comp in  [self.window.comparebox,self.window.addstock]:
            comp.clear()
            comp.addItems(alloptions)

        gr=self._graphObj.params.groups
        org: QListWidget = self.window.orgstocks  # type:
        org.clear()
        #org.addItems(self._graphObj.cols)
        refs: QListWidget = self.window.refstocks  # type:
        refs.clear()
        refs.addItems(self._graphObj.params.ext)

        if  self.window.unite_NONE.isChecked():
            org.addItems(self._graphObj.cols)


#from qtconsole.rich_jupyter_widget import RichJupyterWidget
def changed(tt):
    print(tt)


if __name__ == "__main__":
    app = QApplication([])
    mainwindow=MainWindow()
    mainwindow.run()


    #tabWidget.removeTab(0)
    #tabWidget.addTab(sc,"plot")




    #hs=mainwindow.centralWidget().horizontalSlider
    #hs.update_prop()
    #hs.valueChanged.connect(changed)

    #mm=QMainWindow()
    #widget = Widget()
    #mm.setCentralWidget(widget)
    #mm.show()
    #print(dir(widget))
    #from qtconsole.rich_jupyter_widget import RichJupyterWidget
    #r=RichJupyterWidget(widget)

    #r.show()
    #for f in widget.findChildren(QRadioButton,'.*'):
    #    print(dir(f))
    #a=1
    #widget.show()
    sys.exit(app.exec_())
