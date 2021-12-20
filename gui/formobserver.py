import json
from abc import abstractmethod
from functools import partial

import PySide6.QtCore
import PySide6.QtWidgets

from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QRadioButton,QLineEdit,QInputDialog
from superqt.sliders._labeled import EdgeLabelMode

from common.common import UniteType, Types
from config import config
from engine.parameters import Parameters, EnhancedJSONEncoder, copyit
from engine.symbolsinterface import SymbolsInterface

import json_editor_ui


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


class GraphsHandler:
    def __init__(self):
        self.graphs= {}
        self.lastgraphtext=""

    def load_existing_graphs(self):
        try:
            #gg=Deserializer(open(config.GRAPHFN,'rt'))
            gg=json.load(open(config.GRAPHFN,'rt'))#,object_hook=Deserializer
            self.graphs={k:Parameters.load_from_json_dict(v) for k,v in gg.items()}
            self.update_graph_list()
        except:
            print('err loading graphs')
            return


    def update_graph_list(self):
        self.window.graphList.clear()
        self.window.graphList.addItems(list(self.graphs.keys()))

    def save_graph(self):
        text, ok = QInputDialog().getText(self, "Enter Graph Name",
        "Graph name:",QLineEdit.Normal,
                                                  self.lastgraphtext)
        if ok and text:
            self.graphs[text]= copyit(self._graphObj.params)
            self.lastgraphtext=text
        json.dump(self.graphs,open(config.GRAPHFN,'wt'),cls=EnhancedJSONEncoder)
        self.update_graph_list()


    def load_graph(self):
        text=self.window.graphList.currentItem().text()
        self._graphObj.params = copyit(self.graphs[text])
        self.update_graph(1,force=True)
        self.setup_init_values()

class FormObserver(ListsObserver,GraphsHandler):
    def __init__(self):
        GraphsHandler.__init__(self)
        self._graphObj : SymbolsInterface = None
        self.window=None
        self._toshow=True
        self._initiated=False
        self.disable_slider_values_updates=False
        self.json_editor = json_editor_ui.JSONEditorWindow(None)
        #self._toselectall=False

    def update_graph(self,reset_ranges,force=False):
        try:
            if (self.window.findChild(QCheckBox, name="auto_update").isChecked() and self._initiated) or force:
                self._graphObj.update_graph(Parameters(ignore_minmax=reset_ranges))
                self.update_ranges(reset_ranges)
        except:
            print('failed updating graph')
            import traceback
            traceback.print_exc()

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
        if not val:
            self.selected_changed()
        else:
            self.groups_changed()

    def edit_groups(self):


        #jw=json_editor_ui.JSONEditorWindow(None)
        self.json_editor.set_json_path(config.JSONFILENAME)
        self.json_editor.show()
    def on_json_closed(self,*args):
        self._graphObj.read_groups_from_file()
        self.set_groups_values(0)

    def category_changed(self,num):
        if self.ignore_cat_changes:
            return
        category= self.window.categoryCombo.itemText(num)
        self._graphObj.cur_category=category
        self.set_groups_values(0)


    def setup_observers(self):
        genobs=lambda x:partial(self.attribute_set, x)
        genobsReset = lambda x: partial(self.attribute_set, x, reset_ranges=1)
        self.window.max_num.setEdgeLabelMode(EdgeLabelMode.LabelIsValue)
        self.window.min_crit.valueChanged.connect(genobs('valuerange'))
        self.window.max_num.valueChanged.connect(genobs('numrange'))

        self.window.findChild(QCheckBox, name="usereferncestock").toggled.connect(genobsReset('use_ext'))
        self.window.findChild(QCheckBox, name="start_hidden").toggled.connect(genobs('starthidden'))
        self.window.findChild(QCheckBox, name="adjust_currency").toggled.connect(genobsReset('adjust_to_currency'))
        self.window.home_currency_combo.currentTextChanged.connect(genobsReset('currency_to_adjust'))


        self.window.findChild(QPushButton, name="update_btn").pressed.connect(
            partial(self.update_graph,force=True,reset_ranges=1))
        self.window.use_groups.toggled.connect(self.use_groups)
        self.window.groups.itemSelectionChanged.connect(self.groups_changed)
        self.window.addselected.pressed.connect(self.add_selected)
        self.window.addreserved.pressed.connect(self.add_reserved)
        self.window.showhide.pressed.connect(self.showhide)
        self.window.selectallnone.pressed.connect(self.do_select)
        self.window.deletebtn.pressed.connect(self.del_in_lists)
        self.window.addtoref.pressed.connect(self.add_to_ref)
        self.window.addtosel.pressed.connect(self.add_to_sel)
        self.window.edit_groupBtn.pressed.connect(self.edit_groups)
        self.window.comparebox.currentIndexChanged.connect(self.compare_changed)
        self.window.orgstocks.model().rowsInserted.connect(self.selected_changed)
        self.window.orgstocks.model().rowsRemoved.connect(self.selected_changed)
        self.window.refstocks.model().rowsInserted.connect(self.refernced_changed)
        self.window.refstocks.model().rowsRemoved.connect(self.refernced_changed)
        self.window.categoryCombo.currentIndexChanged.connect(self.category_changed)
        self.window.debug_btn.pressed.connect(self._graphObj.serialize_me)
        self.window.save_graph_btn.pressed.connect(self.save_graph)
        self.window.load_graph_btn.pressed.connect(self.load_graph)


        for rad in self.rad_types:
            rad.toggled.connect(partial(FormObserver.type_unite_toggled, self, rad.objectName()))

        #PySide6.QObject
        #connect()


        self._graphObj.minMaxChanged.connect(self.update_rangeb)
        self._graphObj.namesChanged.connect(self.update_range_num)

        self.json_editor.onCloseEvent.connect(self.on_json_closed)
        self._initiated=True


    @abstractmethod
    def update_stock_list(self):
        pass


class FormInitializer(FormObserver):
    def __init__(self):
        super().__init__()

    def after_load(self):
        self.rad_types = self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,
                                                                                           name="unite_ADDPROT") + self.window.findChildren(
            QCheckBox, name="unite_ADDTOTAL") + self.window.findChildren(QCheckBox, name="COMPARE")

    def set_all_toggled_value(self):
        type= self._graphObj.params.type
        unite = self._graphObj.params.unite_by_group
        for rad in self.rad_types:
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
        self.ignore_cat_changes = False
        self.set_groups_values()

        self.window.daterangepicker.update_prop()
        self.window.startdate.setDateTime(self._graphObj.mindate)
        self.window.enddate.setDateTime(self._graphObj.maxdate)
        self.window.daterangepicker.start=self._graphObj.mindate
        self.window.daterangepicker.end = self._graphObj.maxdate
        self.window.daterangepicker.update_obj()
        self.window.daterangepicker.dateValueChanged.connect(self.date_changed)
        self.window.use_groups.setChecked(self._graphObj.params.use_groups)
        self.window.findChild(QCheckBox, name="usereferncestock").setChecked(self._graphObj.params.use_ext)

        self.window.home_currency_combo.clear()
        self.window.home_currency_combo.addItems(list(config.DEFAULTCURR))

        self.set_all_toggled_value()
        self.load_existing_graphs()

    def set_groups_values(self, isinit=1):
        b=False
        wc= self.window.categoryCombo
        if self._graphObj.Categories!=[wc.itemText(x) for x in range(wc.count())]:
            b=True
            self.ignore_cat_changes=True
            wc.clear()
            wc.addItems(self._graphObj.Categories) #sorry
            self.ignore_cat_changes = False

        options = list(self._graphObj.Groups.keys())
        value = self._graphObj.params.groups if self._graphObj.params.groups != None else list()
        wc= self.window.groups
        if options != [wc.item(x).text() for x in range(wc.count())]:
            b=True
            wc.clear()
            wc.addItems(options)  # sorry
        if not b and not isinit:
            return
        #self.window.groups.addItems(options)
        self.window.groups.setSelectionMode(PySide6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        # self.groups_changed()
        self.update_stock_list(isinit)
        self.update_ranges(isinit)
        if isinit:
            self.select_rows(self.window.groups, [options.index(v) for v in value])

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
        if nuofoptions==0:
            nuofoptions =1
        self.window.max_num.setRange(0, nuofoptions)

        if self._graphObj.minValue is None or self._graphObj.maxValue is None:
            self.disable_slider_values_updates = False
            return

        self.window.min_crit.setRange(self._graphObj.minValue, self._graphObj.maxValue)

        if initial:
            self.window.max_num.setValue((0, nuofoptions))
            self.window.min_crit.setValue((self._graphObj.minValue, self._graphObj.maxValue))
        self.disable_slider_values_updates = False

    def update_stock_list(self,isinitial=0):
        if self.window.fromall.isChecked():
            alloptions = self
        else:
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

