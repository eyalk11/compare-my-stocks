from abc import abstractmethod
from functools import partial

import PySide6.QtCore
import PySide6.QtWidgets
from PySide6 import QtCore
from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QRadioButton
from superqt.sliders._labeled import EdgeLabelMode

from common.common import UniteType, Types
from engine.parameters import HasParamsAndGroups, Parameters


class ListsObserver:
    @staticmethod
    def del_selected(z):
        listItems = z.selectedItems()
        if not listItems: return
        for item in listItems:
            z.takeItem(z.row(item))

    def del_in_lists(self):
        for z in [self.window.orgstocks,self.window.refstocks]:
            self.del_selected(z)

    @staticmethod
    def generic_add_lists(org, dst):
        items = set([x.text() for x in org.selectedItems()])
        items = items - set([dst.item(x).text() for x in range(dst.count())])
        dst.addItems(items)
        FormObserver.del_selected(org)

    def add_to_ref(self):
        self.generic_add_lists(self.window.orgstocks, self.window.refstocks)

    def add_to_sel(self):
        self.generic_add_lists(self.window.refstocks, self.window.orgstocks)

    def add_selected(self):
        org: QListWidget = self.window.orgstocks  # type:
        org.addItem(self.window.addstock.currentText())
        self.update_graph(1)

    def add_reserved(self):
        org: QListWidget = self.window.refstocks  # type:
        org.addItem(self.window.addstock.currentText())
        self.update_graph(1)


class FormObserver(ListsObserver):
    def __init__(self):
        self._graphObj : HasParamsAndGroups = None
        self.window=None
        self._toshow=True
        self._initiated=False
        self.disable_slider_values_updates=False
        #self._toselectall=False

    def update_graph(self,reset_ranges):
        if self.window.findChild(QCheckBox, name="auto_update").isChecked() and self._initiated:
            self._graphObj.update_graph(Parameters(ignore_minmax=reset_ranges))
            #self.update_ranges(reset_ranges)

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


        self.update_graph(1)

    def attribute_set(self, attr, value, reset_ranges=0):
        if attr in ['valuerange','numrange'] and  self.disable_slider_values_updates:
            return
        setattr(self._graphObj.params, attr, value)
        self.update_graph(reset_ranges)

    def groups_changed(self):
        self._graphObj.params.groups= gr= [t.text() for t in self.window.groups.selectedItems()]
        self.update_stock_list()
        self.update_graph(1)



    def date_changed(self, value):
        self.window.startdate.setDateTime(value[0])
        self.window.enddate.setDateTime(value[1])
        self._graphObj.params.fromdate=value[0]
        self._graphObj.params.todate = value[1]
        self.update_graph(1)

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

    def do_select(self):
        gr : QListWidget= self.window.groups
        if len(gr.selectedItems())!=gr.count():
            gr.selectAll()
            #select all
        else:
            gr.clearSelection()

    def compare_changed(self,num):

        self.window.findChild(QCheckBox, name="COMPARE").setChecked(1)
        self._graphObj.params.compare_with=self.window.comparebox.itemText(num)
        self._graphObj.params.type=self._graphObj.params.type | Types.COMPARE
        self.update_graph(1)

    def selected_changed(self,*args,**kw):
        self._graphObj.params.selected_stocks=[self.window.orgstocks.item(x).text()  for x in range(self.window.orgstocks.count())]
        if not self.window.use_groups.isChecked():
            self.update_graph(1)

    def refernced_changed(self,*args,**kw):
        #befext=self._graphObj.params.ext
        self._graphObj.params.ext=[self.window.refstocks.item(x).text()  for x in range(self.window.refstocks.count())]
        if self.window.findChild(QCheckBox, name="usereferncestock").isChecked():
            self.update_graph(1)


    def use_groups(self,val):
        self.attribute_set('use_groups', val)
        self.groups_changed()

    def setup_observers(self):
        genobs=lambda x:partial(self.attribute_set, x)
        genobsReset = lambda x: partial(self.attribute_set, x, reset_ranges=1)
        #self.window.max_num.setEdgeLabelMode(EdgeLabelMode.LabelIsValue)
        self.window.min_crit.valueChanged.connect(genobs('valuerange'))
        self.window.max_num.valueChanged.connect(genobs('numrange'))
        self.window.use_groups.toggled.connect(self.use_groups)
        self.window.groups.itemSelectionChanged.connect(self.groups_changed)
        self.window.addselected.pressed.connect(self.add_selected)
        self.window.addreserved.pressed.connect(self.add_reserved)
        self.window.showhide.pressed.connect(self.showhide)
        self.window.selectallnone.pressed.connect(self.do_select)
        self.window.deletebtn.pressed.connect(self.del_in_lists)
        self.window.addtoref.pressed.connect(self.add_to_ref)
        self.window.addtosel.pressed.connect(self.add_to_sel)


        self.window.findChild(QCheckBox, name="start_hidden").toggled.connect(genobs('starthidden'))
        self.window.findChild(QPushButton,name="update_btn").pressed.connect(self._graphObj.update_graph)
       # self.window.findChildd(QCheckBox, name="COMPARE").toggled.connect()
        self.window.comparebox.currentIndexChanged.connect(self.compare_changed)
        self.window.orgstocks.model().rowsInserted.connect(self.selected_changed)
        self.window.orgstocks.model().rowsRemoved.connect(self.selected_changed)
        self.window.refstocks.model().rowsInserted.connect(self.refernced_changed)
        self.window.refstocks.model().rowsRemoved.connect(self.refernced_changed)

        self.window.findChild(QCheckBox, name="usereferncestock").toggled.connect(genobsReset('use_ext'))

        for rad in self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,name="unite_ADDTOTAL")+ self.window.findChildren(QCheckBox, name="COMPARE"):
            rad.toggled.connect(partial(FormObserver.type_unite_toggled, self, rad.objectName()))

        #PySide6.QObject
        #connect()


        self._graphObj.minMaxChanged.connect(self.update_rangeb)
        self._graphObj.namesChanged.connect(self.update_range_num)
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
        self.update_ranges(1)
        self.select_rows(self.window.groups,[options.index(v) for v in value])

        self.window.daterangepicker.update_prop()
        self.window.startdate.setDateTime(self._graphObj.mindate)
        self.window.enddate.setDateTime(self._graphObj.maxdate)
        self.window.daterangepicker.start=self._graphObj.mindate
        self.window.daterangepicker.end = self._graphObj.maxdate
        self.window.daterangepicker.update_obj()
        self.window.daterangepicker.dateValueChanged.connect(self.date_changed)
        self.window.use_groups.setChecked(self._graphObj.params.use_groups)
        self.window.findChild(QCheckBox, name="usereferncestock").setChecked(self._graphObj.params.use_ext)


        self.set_all_toggled_value()

    def update_rangeb(self,minmax):
        self.disable_slider_values_updates=True
        self.window.min_crit.setRange(minmax[0], minmax[1])
        self.window.min_crit.setValue(minmax)
        self.disable_slider_values_updates = False

    def update_range_num(self,nuofoptions):
        self.disable_slider_values_updates=True
        self.window.max_num.setRange(0, nuofoptions)
        self.window.max_num.setValue((0, nuofoptions))
        self.disable_slider_values_updates = False

    def update_ranges(self,initial=1):
        nuofoptions = len(self._graphObj.colswithoutext)

        self.disable_slider_values_updates=True
        self.window.max_num.setRange(0, nuofoptions)


        self.window.min_crit.setRange(self._graphObj.minValue, self._graphObj.maxValue)

        if initial:
            self.window.max_num.setValue((0, nuofoptions))
            self.window.min_crit.setValue((self._graphObj.minValue, self._graphObj.maxValue))
        self.disable_slider_values_updates = False

    def update_stock_list(self,isinitial=0):
        alloptions= sorted(list(self._graphObj._usable_symbols)) #CompareEngine.get_options_from_groups([g for g in CompareEngine.Groups])

        #self._last_choice=  self.window.comparebox.currentText()
        if isinitial:
            for comp in  [self.window.comparebox,self.window.addstock] :
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
            elif isinitial:
                org.clear()
                org.addItems(self._graphObj.params.selected_stocks)

