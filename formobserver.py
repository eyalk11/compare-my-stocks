from abc import abstractmethod
from functools import partial

import PySide6.QtCore
import PySide6.QtWidgets
from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QRadioButton

from common import UniteType, Types


class FormObserver:
    def __init__(self):
        self._graphObj = None
        self.window=None
        self._toshow=True
        self._initiated=False
        #self._toselectall=False

    def update_graph(self):
        if self.window.findChild(QCheckBox, name="auto_update").isChecked() and self._initiated:
            self._graphObj.update_graph()

    def type_unite_toggled(self, name, value):
        unite_ref=False
        if name.startswith('unite'):
            name=name[len('unite')+1:]
            unite_ref=True


        curType=UniteType[name] if unite_ref else  Types[name]

        if unite_ref :
            if value:
                self._graphObj.params.unite_by_group |= curType
            else:
                self._graphObj.params.unite_by_group &= ~curType

        else:
            if value:
                self._graphObj.params.type |= curType
            else:
                self._graphObj.params.type &= ~curType


        self.update_graph()

    def attribute_move(self,attr,value):
        setattr(self._graphObj.params,attr,value)
        # attr.value=value
        self.update_graph()

    def groups_changed(self):
        self._graphObj.params.groups= gr= [t.text() for t in self.window.groups.selectedItems()]
        self.update_stock_list()
        self.update_graph()



    def date_changed(self, value):
        self.window.startdate.setDateTime(value[0])
        self.window.enddate.setDateTime(value[1])
        self._graphObj.params.fromdate=value[0]
        self._graphObj.params.todate = value[1]
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
        if len(gr.selectedItems())!=gr.count():
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

    def compare_changed(self,num):

        self.window.findChild(QCheckBox, name="COMPARE").setChecked(1)
        self._graphObj.params.compare_with=self.window.comparebox.itemText(num)
        self._graphObj.params.type=self._graphObj.params.type | Types.COMPARE
        self.update_graph()

    def selected_changed(self,*args,**kw):
        self._graphObj.params.selected_stocks=[self.window.orgstocks.item(x).text()  for x in range(self.window.orgstocks.count())]
        if not self.window.use_groups.isChecked():
            self.update_graph()

    def refernced_changed(self,*args,**kw):
        #befext=self._graphObj.params.ext
        self._graphObj.params.ext=[self.window.refstocks.item(x).text()  for x in range(self.window.refstocks.count())]
        if self.window.findChild(QCheckBox, name="usereferncestock").isChecked():
            self.update_graph()



    def setup_observers(self):
        genobs=lambda x:partial(self.attribute_move,x)
        #self.window.max_num.setEdgeLabelMode(EdgeLabelMode.LabelIsValue)
        self.window.min_crit.valueChanged.connect(genobs('mincrit'))
        self.window.max_num.valueChanged.connect(genobs('maxnum'))
        self.window.use_groups.toggled.connect(genobs('use_groups'))
        self.window.groups.itemSelectionChanged.connect(self.groups_changed)
        self.window.addselected.pressed.connect(self.addselected)
        self.window.addreserved.pressed.connect(self.addreserved)
        self.window.showhide.pressed.connect(self.showhide)
        self.window.selectallnone.toggled.connect(self.doselect)

        self.window.findChild(QCheckBox, name="start_hidden").toggled.connect(genobs('starthidden'))
        self.window.findChild(QPushButton,name="update_btn").pressed.connect(self._graphObj.update_graph)
       # self.window.findChildd(QCheckBox, name="COMPARE").toggled.connect()
        self.window.comparebox.currentIndexChanged.connect(self.compare_changed)
        self.window.orgstocks.model().rowsInserted.connect(self.selected_changed)
        self.window.orgstocks.model().rowsRemoved.connect(self.selected_changed)
        self.window.refstocks.model().rowsInserted.connect(self.refernced_changed)
        self.window.refstocks.model().rowsRemoved.connect(self.refernced_changed)
        self.window.findChild(QCheckBox, name="usereferncestock").toggled.connect(genobs('use_ext'))




        #model=PySide6.QtCore.QItemSelectionModel()
        #selection= PySide6.QtCore.QItemSelectionRange([options.index(v) for v in value])
        #model.select(selection, PySide6.QtCore.QItemSelectionModel.Select)
        #self.window.groups.setSelectionModel(model)

        #stockl=list(get_options_from_groups(d.value))






        for rad in self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,name="unite_ADDTOTAL")+ self.window.findChildren(QCheckBox, name="COMPARE"):
            rad.toggled.connect(partial(FormObserver.type_unite_toggled, self, rad.objectName()))

        self._initiated=True

    @abstractmethod
    def update_stock_list(self):
        pass


class FormInitializer(FormObserver):
    def set_all_toggled_value(self):
        type= self._graphObj.params.type
        unite = self._graphObj.params.unite_by_group
        for rad in self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,
                                                                                     name="unite_ADDTOTAL") + self.window.findChildren(
                QCheckBox, name="COMPARE"):
            name=rad.objectName()
            #func= rad.setChecked if type(rad)==QCheckBox else rad.setCheckState
            #x : QCheckBox
            if name.startswith('unite'):
                name = name[len('unite') + 1:]
                rad.setChecked( bool(unite &  getattr(UniteType,name)))
            else:
                try:
                    rad.setChecked(bool(type & getattr(Types, name)))
                except:
                    pass

    def setup_init_values(self):

        options=list(self._graphObj.Groups.keys())
        value = self._graphObj.params.groups if self._graphObj.params.groups != None else list()


        self.window.groups.addItems( options)
        self.window.groups.setSelectionMode(PySide6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        #self.groups_changed()
        self.update_stock_list(1)
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
        self.window.use_groups.setChecked(self._graphObj.params.use_groups)
        self.window.findChild(QCheckBox, name="usereferncestock").setChecked(self._graphObj.params.use_ext)

        #self.window.use_groups.setValue(self._graphObj.params.use_groups)
        #self.selection_changed()
        #self.refernced_changed()
        self.set_all_toggled_value()

    def update_stock_list(self,isinital=0):
        alloptions= list(self._graphObj._usable_symbols) #CompareEngine.get_options_from_groups([g for g in CompareEngine.Groups])
        for comp in  [self.window.comparebox,self.window.addstock]:
            comp.clear()
            comp.addItems(alloptions)

        gr=self._graphObj.params.groups
        org: QListWidget = self.window.orgstocks  # type:
        #org.addItems(self._graphObj.cols)
        refs: QListWidget = self.window.refstocks  # type:
        refs.clear()
        refs.addItems(self._graphObj.params.ext)

        if  self.window.unite_NONE.isChecked():
            if self._graphObj.params.use_groups:
                org.clear()
                org.addItems(self._graphObj.get_options_from_groups(self._graphObj.params.groups))
            elif isinital:
                org.clear()
                org.addItems(self._graphObj.params.selected_stocks)
