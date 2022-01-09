import json
from abc import abstractmethod
from functools import partial

from PySide6.QtCore import QThread
import PySide6.QtCore
import PySide6.QtWidgets

from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QRadioButton, QLineEdit, QInputDialog, QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from superqt.sliders._labeled import EdgeLabelMode

from common.common import UniteType, Types, index_of
from common.dolongprocess import DoLongProcess, DoLongProcessSlots
from config import config
from engine.parameters import Parameters, EnhancedJSONEncoder, copyit
from engine.symbolsinterface import SymbolsInterface

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        FigureCanvasQTAgg.__init__(self, self.fig)
        FigureCanvasQTAgg.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvasQTAgg.updateGeometry(self)
try:
    from json_editor import json_editor_ui
except:
    import json_editor_ui

class ListsObserver:
    def process_elem(self,params):
        while True:
            ls = self.addqueue.copy()
            self.window.last_status.setText('processing added stocks')
            self._graphObj.process(set(ls),params) #blocks. should have mutex here
            self.window.last_status.setText('finshed processing')
            self.addqueue = list(set(self.addqueue) - set(ls))
            if len(self.addqueue)==0:
                break


    def __init__(self):
        self.addqueue=[]
        self.grep_from_queue_task= DoLongProcess(self.process_elem)

    def process_if_needed(self,stock):
        if not stock in self._graphObj._usable_symbols:
            self.addqueue+=[stock]

            if not self.grep_from_queue_task.is_started:
                params = copyit(self._graphObj.params)
                params.transactions_todate = None  # datetime.now() #always till the end
                self.grep_from_queue_task.startit(params)



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
        text = self.window.addstock.currentText()
        self.process_if_needed(text)
        org.addItem(text)
        self.update_graph(1)

    def add_reserved(self):
        org: QListWidget = self.window.refstocks  # type:
        text = self.window.addstock.currentText()
        self.process_if_needed(text)
        org.addItem(text)
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
        self.setup_controls_from_params(0)


class FormObserver(ListsObserver,GraphsHandler):
    def update_task(self,params):
        # self.window.last_status.setText('started refreshing')
        self._graphObj.update_graph(params)
        # self.window.last_status.setText('finshed refreshing')

    def refresh_task(self,x,params):
        self.window.last_status.setText('started refreshing')
        self._graphObj.process(set(x),params)
        self.update_graph(1, True)
        self.window.last_status.setText('finshed refreshing')

    def __init__(self):
        ListsObserver.__init__(self)
        GraphsHandler.__init__(self)
        self._graphObj : SymbolsInterface = None
        self.window=None
        self._toshow=True
        self._initiated=False
        self.disable_slider_values_updates=False
        self.json_editor = json_editor_ui.JSONEditorWindow(None)
        self.ignore_updates_for_now = False
        #self._dolongprocess=DoLongProces()
        #self._toselectall=False
        #task = lambda x: self._graphObj.process(set(x))
        self._refresh_stocks_task = DoLongProcess(self.refresh_task)
        self._update_graph_task = DoLongProcessSlots(self.update_task)


    def refresh_stocks(self,*args):
        wantitall = self._graphObj.used_unitetype & UniteType.ADDPROT == UniteType.ADDPROT
        toupdate= self._graphObj.required_syms(True,wantitall,True)
        params= copyit(self._graphObj.params)
        params.transactions_todate=None #datetime.now() #always till the end
        if len(toupdate)==0:
            return

        if self._refresh_stocks_task.is_started:
            self.window.last_status.setText("already runnning another")
            return
        self._refresh_stocks_task.startit(toupdate,params)

        #self._dolongprocess.run(set(toupdate))


    def update_graph(self,reset_ranges,force=False):
        self.window.last_status.setText('')
        if self.ignore_updates_for_now:
            return
        try:
            if (self.window.findChild(QCheckBox, name="auto_update").isChecked() and self._initiated) or force:
                self._update_graph_task.command.emit((Parameters(ignore_minmax=reset_ranges),))
                # self._graphObj.update_graph(Parameters(ignore_minmax=reset_ranges))
                self.update_ranges(reset_ranges)
        except:
            print('failed updating graph')
            self.window.last_status.setText('failed updating graph')
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
        self._graphObj.params.compare_with=self.window.comparebox.currentText()
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

    def update_status(self,text):
        self.window.last_status.setText(text)
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

        self.window.findChild(QPushButton, name="refresh_stock").pressed.connect(self.refresh_stocks)
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
        self._graphObj.statusChanges.connect(self.update_status)

        self.json_editor.onCloseEvent.connect(self.on_json_closed)
        self._initiated=True


    @abstractmethod
    def update_stock_list(self):
        pass


class FormInitializer(FormObserver):

    def __init__(self):

        super().__init__()

    @property
    def figure(self):
        return self._canvas.figure

    @property
    def axes(self):
        return self._canvas.ax
        return
    def prepare_graph_widget(self):
        #tabWidget = self.window.tabWidget_8Page1  # type: QTabWidget

        self._canvas = MplCanvas()
        #sc.manager.window.move(1,1)
        toolbar = NavigationToolbar(self._canvas, self.window)
        #layout = QVBoxLayout()
        self.window.graph_groupbox.layout().addWidget(toolbar)
        self.window.graph_groupbox.layout().addWidget(self._canvas)


    def after_load(self):
        self.rad_types = self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,
                                                                                           name="unite_ADDPROT") + self.window.findChildren(
            QCheckBox, name="unite_ADDTOTAL") + self.window.findChildren(QCheckBox, name="COMPARE")
        self.prepare_graph_widget()

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

    def setup_controls_from_params(self,initial=True):
        self.ignore_cat_changes = False
        self.ignore_updates_for_now=True
        self.set_groups_values(isinitialforstock=initial)

        self.window.daterangepicker.update_prop()
        self.window.startdate.setDateTime(self._graphObj.mindate)
        self.window.enddate.setDateTime(self._graphObj.maxdate)
        self.window.daterangepicker.start=self._graphObj.mindate
        self.window.daterangepicker.end = self._graphObj.maxdate
        self.window.daterangepicker.update_obj()
        if not initial:
            self.window.daterangepicker.datevalue= (self._graphObj.params.fromdate,self._graphObj.params.todate)
        else:
            self.window.daterangepicker.dateValueChanged.connect(self.date_changed)
        self.window.use_groups.setChecked(self._graphObj.params.use_groups)
        self.window.findChild(QCheckBox, name="usereferncestock").setChecked(self._graphObj.params.use_ext)

        self.window.home_currency_combo.clear()
        self.window.home_currency_combo.addItems(list(config.DEFAULTCURR))

        self.set_all_toggled_value()
        if not initial and self._graphObj.params.compare_with:
            wc = self.window.comparebox

            l=[wc.itemText(x) for x in range(wc.count())]
            ind=index_of(self._graphObj.params.compare_with,l)
            self.window.comparebox.setCurrentIndex(ind)
            if ind==-1:
                self.window.comparebox.setCurrentText(self._graphObj.params.compare_with)

        if initial:
            self.load_existing_graphs()
        self.ignore_updates_for_now = False

    def set_groups_values(self, isinit=1,isinitialforstock=1):
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
        self.update_stock_list(isinitialforstock and isinit)
        self.update_ranges(isinit)
        if isinit:
            self.select_rows(self.window.groups, [options.index(v) for v in value])

    def update_rangeb(self,minmax):
        self.disable_slider_values_updates=True
        if minmax[0]==minmax[1]:
            minmax = (minmax[0],minmax[0]+0.1)
        self.window.min_crit.setRange(minmax[0], minmax[1])
        self.window.min_crit.setValue(minmax)
        self.disable_slider_values_updates = False

    def update_range_num(self,nuofoptions):
        if nuofoptions==0:
            nuofoptions=1
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
        if self._graphObj.minValue==self._graphObj.maxValue and self._graphObj.maxValue==0:
            print('bad range')
            self.window.min_crit.setRange(self._graphObj.minValue, self._graphObj.maxValue+0.1)
        else:
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



    #self.window.gridLayout_8.addWidget(toolbar)
    #self.window.gridLayout_8.addWidget(sc)
    #self.window.tabWidget.setLayout(QVBoxLayout())
    #self.window.tabWidget.setCenteralWidget()
    #tabWidget.setCentralWidget(self.window.gridLayout_8)
    #self.window.graph_groupbox.gridLayout_3.setLayout(layout)
    #layoutq=QVBoxLayout()
    #self.window.tab


