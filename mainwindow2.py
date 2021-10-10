# This Python file uses the following encoding: utf-8
import os
from datetime import datetime
from functools import partial
from pathlib import Path
import sys
import PySide6.QtCore
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QPushButton, QListWidget
from PySide6.QtWidgets import QCheckBox, QRadioButton
from matplotlib.backends.backend_qt import  FigureCanvasQT
from typing import Any
import PySide6.QtWidgets
from PySide6.QtWidgets import QApplication, QWidget,QRadioButton,QMainWindow,QTabWidget,QVBoxLayout
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
#from superqt import QRangeSlider,QLabeledSlider
import pandas as pd
#from supportwidgets import get_options_from_groups
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib
#matplotlib.use('QtAgg')
from superqt.sliders._generic_range_slider import _GenericRangeSlider
from superqt.sliders._labeled import EdgeLabelMode,QLabeledSlider
from PySide6.QtCore import Signal
from getpositionsgraph import initialize_graph_and_ib, CompareEngine
from common import Types, UseCache, UniteType


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

class QDateRangeSlider(_GenericRangeSlider[float]):
    dateValueChanged = Signal(tuple)

    def __init__(self,*args, **kw):
        self.start=None
        self.end=None
        self.freq='D'
        self.fmt='%Y-%m-%d'
        super(QDateRangeSlider, self).__init__(*args, **kw)
        self.valueChanged.connect(self.my_val_change)
        #_DateMixin.__init__(self)#datetime.timdelta(days=1),datetime.timedelta(days=5))

        #hh=self.property('end')
        #super(QDesignerPropertyEditorInterface,self).__init__(*args, **kw)

    def update_prop(self):
        for  name in ["fmt","freq"]:
            setattr(self,name,self.property(name))
        #self.start=self.start.toPython()
        #self.update_obj()

    def update_obj(self):
        if self.start==None and self.end==None:
            return True
        self.date_range = [(x.to_pydatetime()) for x in pd.date_range(start=self.start, end=self.end, freq=self.freq)]
        self.options= [matplotlib.dates.date2num(y) for y in self.date_range]
        self._value= [min(self.options),max(self.options)]
        self._setPosition([min(self.options), max(self.options)])
        self.setRange(min(self.options),max(self.options))
        #self.setMinimum()
        #self.setinterval(self.date_range[1] - self.date_range[0])

        self.setSingleStep((self.options[1] - self.options[0]))
        self.setPageStep((self.options[5] - self.options[0]))

        #self.setvalue((min(self.date_range), max(self.date_range)))
        #self.options = [(item.strftime(self.fmt),item) for item in self.date_range]


    def my_val_change(self,val):
        self.dateValueChanged.emit( [matplotlib.dates.num2date(x) for x in val])

    @property
    def datevalue(self):
        return matplotlib.dates.num2date([matplotlib.dates.num2date(x) for x in self.value])
    #def valueChanged(self):
    #    return
    #self.value



class Widget(QWidget):
    def __init__(self):
        super(Widget, self).__init__()
        self.load_ui()

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()


class FormObserver:
    def __init__(self):
        self._graphObj = None
        self.window=None
        self._toshow=True
        #self._toselectall=False

    def update_graph(self):
        if self.window.findChild(QCheckBox, name="auto_update").isChecked():
            self._graphObj.update_graph()

    def type_unite_toggled(self, name, value):
        unite_ref=False
        if name.startswith('unite'):
            name=name[len('unite')+1:]
            unite_ref=True


        curType=UniteType[name] if unite_ref else  Types[name]

        if unite_ref :
            if value:
                self._graphObj.unite_by_group |= curType
            else:
                self._graphObj.unite_by_group &= ~curType

        else:
            if value:
                self._graphObj.type |= curType
            else:
                self._graphObj.type &= ~curType


        self.update_graph()

    def attribute_move(self,attr,value):
        #setattr(self._graphObj,attr,value)
        attr.value=value
        self.update_graph()

    def groups_changed(self):
        self._graphObj.groups= gr= [t.text() for t in self.window.groups.selectedItems()]
        self.update_stock_list()
        self.update_graph()



    def date_changed(self, value):
        self.window.startdate.setDateTime(value[0])
        self.window.enddate.setDateTime(value[1])
        self._graphObj.fromdate=value[0]
        self._graphObj.todate = value[1]
        self.update_graph()

    @staticmethod
    def select_rows(widget,indices):
        """Since the widget sorts the rows, selecting rows isn't trivial."""

        selection = PySide6.QtCore.QItemSelection()
        for idx in indices:
            selection.append(PySide6.QtCore.QItemSelectionRange(widget.model().index(idx)))
        widget.selectionModel().select(
            selection, PySide6.QtCore.QItemSelectionModel.ClearAndSelect)
    def showhide(self):
        self._toshow= not self._toshow
        self._graphObj.show_hide( self._toshow)

    def doselect(self):
        gr : QListWidget= self.window.groups
        if len(gr.selectedItems())!=len(gr.items()):
            gr.selectAll()
            #select all
        else:
            gr.clearSelection()

    def addselected(self):
        org: QListWidget = self.window.orgstocks  # type:
        org.addItem(self.window.addstock.currentText())
        self.update_graph()

    def addreserved(self):
        org: QListWidget = self.window.refstocks  # type:
        org.addItem(self.window.addstock.currentText())
        self.update_graph()

    def compare_changed(self,text):

        self.window.findChild(QCheckBox, name="COMPARE").setChecked(1)
        self._graphObj.compare_with=text
        self._graphObj.type=self._graphObj.type | Types.COMPARE
        self.update_graph()

    def selected_changed(self,*args,**kw):
        self._graphObj.selected_stocks=[self.window.orgstocks.item(x).text()  for x in range(self.window.orgstocks.count())]
        #self.update_graph()

    def refernced_changed(self,*args,**kw):
        self._graphObj.ext=[self.window.orgstocks.item(x).text()  for x in range(self.window.refstocks.count())]
        #self.update_graph()

    def setup_observers(self):
        genobs=lambda x:partial(self.attribute_move,x)
        #self.window.max_num.setEdgeLabelMode(EdgeLabelMode.LabelIsValue)
        self.window.min_crit.valueChanged.connect(genobs(self._graphObj._mincrit))
        self.window.max_num.valueChanged.connect(genobs(self._graphObj._maxnum))
        self.window.use_groups.toggled.connect(genobs(self._graphObj._use_groups))
        self.window.groups.itemSelectionChanged.connect(self.groups_changed)
        self.window.addselected.pressed.connect(self.addselected)
        self.window.addreserved.pressed.connect(self.addreserved)
        self.window.showhide.pressed.connect(self.showhide)
        self.window.selectallnone.toggled.connect(self.doselect)

        self.window.findChild(QCheckBox, name="start_hidden").toggled.connect(genobs(self._graphObj.starthidden))
        self.window.findChild(QPushButton,name="update_btn").pressed.connect(self._graphObj.update_graph)
       # self.window.findChildd(QCheckBox, name="COMPARE").toggled.connect()
        self.window.comparebox.currentTextChanged.connect(self.compare_changed)
        self.window.orgstocks.model().rowsInserted.connect(self.selected_changed)
        self.window.orgstocks.model().rowsRemoved.connect(self.selected_changed)




        #model=PySide6.QtCore.QItemSelectionModel()
        #selection= PySide6.QtCore.QItemSelectionRange([options.index(v) for v in value])
        #model.select(selection, PySide6.QtCore.QItemSelectionModel.Select)
        #self.window.groups.setSelectionModel(model)

        #stockl=list(get_options_from_groups(d.value))






        for rad in self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,name="unite_ADDTOTAL")+ self.window.findChildren(QCheckBox, name="COMPARE"):
            rad.toggled.connect(partial(MainWindow.type_unite_toggled, self, rad.objectName()))


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
        self._graphObj.gen_graph(type=Types.PRICE, isline=True,groups=['FANG'],mincrit=-100000,maxnum=4000,use_cache=UseCache.FORCEUSE,show_graph=False)

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
        value = self._graphObj.groups if self._graphObj.groups != None else list()


        self.window.groups.addItems( options)
        self.window.groups.setSelectionMode(PySide6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        #self.groups_changed()
        self.update_stock_list()
        self.select_rows(self.window.groups,[options.index(v) for v in value])
        self.window.max_num.setRange(-1*abs(self._graphObj.maxnum*2),abs(self._graphObj.maxnum*2))
        self.window.max_num.setRange(-1*abs(self._graphObj.mincrit * 2), abs(self._graphObj.mincrit * 2))
        self.window.max_num.setValue(self._graphObj.maxnum)
        self.window.min_crit.setValue(self._graphObj.mincrit)
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

        gr=self._graphObj.groups
        org: QListWidget = self.window.orgstocks  # type:
        org.clear()
        #org.addItems(self._graphObj.cols)
        refs: QListWidget = self.window.refstocks  # type:
        refs.clear()
        refs.addItems(self._graphObj.ext)

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
