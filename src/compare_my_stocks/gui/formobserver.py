import json
from abc import abstractmethod
from datetime import datetime
from enum import Enum
from functools import partial

from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import QThread,QTimer,QDateTime,QTime,QDate
import PySide6.QtCore
import PySide6.QtWidgets
from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QLineEdit,QDateEdit, QInputDialog,QGroupBox,QRadioButton,QSizePolicy
from superqt.sliders._labeled import EdgeLabelMode
import pytz

from common.common import UniteType, Types, LimitType
from common.dolongprocess import DoLongProcess, DoLongProcessSlots
from config import config
from engine.parameters import Parameters, EnhancedJSONEncoder, copyit
from engine.symbolsinterface import SymbolsInterface
from gui.jupyterhandler import JupyterHandler

class DisplayModes(int,Enum):
    MINIMAL=0,
    JUPYTER=1,
    NOJUPYTER = 2,
    FULL=3
class ResetRanges(int,Enum):
    DONT=0
    IfAPROP=1
    FORCE=2


try:
    from json_editor import json_editor_ui
except:
    import json_editor_ui

class ListsObserver():
    def process_elem(self,params):
        while True:
            ls = self.addqueue.copy()
            self.window.last_status.setText('processing added stocks')
            self.graphObj.process(set(ls),params) #blocks. should have mutex here
            self.window.last_status.setText('finshed processing')
            self.addqueue = list(set(self.addqueue) - set(ls))
            if len(self.addqueue)==0:
                break


    def __init__(self):
        self.addqueue=[]
        self.grep_from_queue_task= DoLongProcessSlots(self.process_elem)

    def process_if_needed(self,stock):
        if not stock in self.graphObj._usable_symbols:
            self.addqueue+=[stock]

            if not self.grep_from_queue_task.is_started:
                params = copyit(self.graphObj.params)
                params.transactions_todate = None  # datetime.now() #always till the end
                self.grep_from_queue_task.command.emit((params,))



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
            self.internal_save(text)

    def internal_save(self, text,upd=True):
        self.graphs[text] = copyit(self.graphObj.params)
        if upd:
            self.lastgraphtext = text
        json.dump(self.graphs, open(config.GRAPHFN, 'wt'), cls=EnhancedJSONEncoder)
        self.update_graph_list()

    def load_graph(self,text=None):
        if text==None:
            if not self.window.graphList.currentItem():
                return
            text=self.window.graphList.currentItem().text()
        self.graphObj.params = copyit(self.graphs[text])
        self.update_graph(ResetRanges.FORCE,force=True)
        self.setup_controls_from_params(0,1)

    def save_last_graph(self):
        if config.LASTGRAPHNAME:
            self.internal_save(config.LASTGRAPHNAME,upd=False)

    def load_last_if_needed(self):
        if config.LOADLASTATBEGIN:
            self.load_graph(config.LASTGRAPHNAME)
        return config.LOADLASTATBEGIN
        


class FormObserver(ListsObserver, GraphsHandler, JupyterHandler):
    def update_task(self,params):
        # self.window.last_status.setText('started refreshing')
        self.graphObj.update_graph(params)
        # self.window.last_status.setText('finshed refreshing')

    def refresh_task(self,x,params):
        self.window.last_status.setText('started refreshing')
        self.graphObj.process(set(x),params)
        self.update_graph(1, True)
        self.window.last_status.setText('finshed refreshing')

    def decrease(self):
        self._update_graph_task.command_waiting = self._update_graph_task.command_waiting - 1

    def __init__(self):
        ListsObserver.__init__(self)
        GraphsHandler.__init__(self)
        JupyterHandler.__init__(self)
        self.graphObj : SymbolsInterface = None
        self.window=None
        self._toshow=True
        self._initiated=False
        self.disable_slider_values_updates=False
        self.json_editor = json_editor_ui.JSONEditorWindow(None)
        self.ignore_updates_for_now = False
        #self._dolongprocess=DoLongProces()
        #self._toselectall=False
        #task = lambda x: self.graphObj.process(set(x))
        self._refresh_stocks_task = DoLongProcessSlots(self.refresh_task)

        #self._refresh_stocks_task.postinit()
        #self._refresh_stocks_task.moveToThread(self._refresh_stocks_task.thread)
        self._update_graph_task = DoLongProcessSlots(self.update_task)
        #self.command_waiting=0
        self._update_graph_task.finished.connect(self.decrease)
        self.current_mode=DisplayModes.FULL
        self.placeholder=QGroupBox()


    def refresh_stocks(self,*args):
        TOLLERANCEGETIT=5
        wantitall = self.graphObj.used_unitetype & UniteType.ADDPROT == UniteType.ADDPROT
        toupdate= self.graphObj.required_syms(True,wantitall,True)
        params= copyit(self.graphObj.params)
        print(f'refreshing {toupdate} from {params.fromdate} to {params.todate}')
        now= datetime.now(tz=params.todate.tzinfo)
        if params.todate<now and (now- params.todate).days < TOLLERANCEGETIT:
            params.todate=None
        #if self.window.enddate.date().toPy-datetime.
        #params.transactions_todate=None #datetime.now() #always till the end
        print('updating stocks from ')
        if len(toupdate)==0:
            return

        if self._refresh_stocks_task.is_started:
            self.window.last_status.setText("already runnning another")
            return
        self._refresh_stocks_task.command.emit((toupdate,params))

        #self._dolongprocess.run(set(toupdate))


    def update_graph(self,reset_ranges : ResetRanges ,force=False):
        def call():
            self.decrease()
            self.update_ranges(reset_ranges)

        self.window.last_status.setText('')
        if self.ignore_updates_for_now:
            return
        try:
            if (self.window.findChild(QCheckBox, name="auto_update").isChecked() and self._initiated) or force:
                self._update_graph_task.command_waiting+=1
                if self._update_graph_task.command_waiting >=3:
                    print('update waiting')
                    self.window.last_status.setText('Update is waiting (generating graph probably)')


                self._update_graph_task.finished.disconnect()
                self._update_graph_task.finished.connect(call)
                self._update_graph_task.command.emit((Parameters(ignore_minmax=reset_ranges),))
                # self.graphObj.update_graph(Parameters(ignore_minmax=reset_ranges))

        except:
            print('failed updating graph')
            self.window.last_status.setText('failed updating graph')
            import traceback
            traceback.print_exc()

    def type_unite_toggled(self, name, value):
        types_dic = {
            'unite': (UniteType,'unite_by_group',ResetRanges.FORCE),
            'limit' : (LimitType,'limit_by',0),
            '':(Types,'type',ResetRanges.FORCE)
        }
        for k in types_dic:
            if name.startswith(k):
                if len(k)>0:
                    name=name[len(k)+1:] #account for _
                curType = types_dic[k][0][name]
                curpar=types_dic[k][1]
                update_ranges = types_dic[k][2]
                break
        if value:
            setattr(self.graphObj.params,curpar,getattr(self.graphObj.params,curpar) | curType)
        else:
            setattr(self.graphObj.params, curpar, getattr(self.graphObj.params, curpar) & ~curType)

        self.update_graph(update_ranges)

    def attribute_set(self, attr, value, reset_ranges=0):
        if attr in ['valuerange','numrange'] and  self.disable_slider_values_updates:
            return
        setattr(self.graphObj.params, attr, value)
        self.update_graph(reset_ranges)

    def groups_changed(self):
        self.graphObj.params.groups= gr= [t.text() for t in self.window.groups.selectedItems()]
        self.update_stock_list()
        self.update_graph(ResetRanges.IfAPROP)



    def date_changed(self, value,toupdate=True):
        if toupdate:
            self.window.startdate.setDateTime(value[0])
            self.window.enddate.setDateTime(value[1])
        self.graphObj.params.fromdate=value[0]
        self.graphObj.params.todate = value[1]
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
        self.graphObj.show_hide( self._toshow)

    def do_select(self):
        gr : QListWidget= self.window.groups
        if len(gr.selectedItems())!=gr.count():
            gr.selectAll()
            #select all
        else:
            gr.clearSelection()

    def compare_changed(self,num):
        if self.ignore_updates_for_now:
            return
        self.window.findChild(QCheckBox, name="COMPARE").setChecked(1)
        self.graphObj.params.compare_with=self.window.comparebox.currentText()
        self.graphObj.params.type=self.graphObj.params.type | Types.COMPARE
        self.update_graph(ResetRanges.FORCE)

    def selected_changed(self,*args,**kw):
        self.graphObj.params.selected_stocks=[self.window.orgstocks.item(x).text()  for x in range(self.window.orgstocks.count())]
        if not self.window.use_groups.isChecked():
            self.update_graph(1)

    def refernced_changed(self,*args,**kw):
        #befext=self.graphObj.params.ext
        self.graphObj.params.ext=[self.window.refstocks.item(x).text()  for x in range(self.window.refstocks.count())]
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
        self.graphObj.read_groups_from_file()
        self.set_groups_values(0)

    def category_changed(self,num):
        if self.ignore_cat_changes:
            return
        category= self.window.categoryCombo.itemText(num)
        self.graphObj.cur_category=category
        self.set_groups_values(0)

    def limit_port_changed(self,val):

        self.attribute_set('limit_to_portfolio',val,reset_ranges=1)
        self.update_stock_list(justorgs=True)

    def setup_observers(self):
        genobs=lambda x:partial(self.attribute_set, x,reset_ranges=ResetRanges.DONT)
        genobsReset = lambda x: partial(self.attribute_set, x, reset_ranges=1)
        genobsResetForce = lambda x: partial(self.attribute_set, x, reset_ranges=ResetRanges.FORCE)
        self.window.max_num.setEdgeLabelMode(EdgeLabelMode.LabelIsValue)
        self.window.min_crit.valueChanged.connect(genobs('valuerange'))
        self.window.max_num.valueChanged.connect(genobs('numrange'))
        self.window.findChild(QCheckBox, name="limit_to_port").toggled.connect(self.limit_port_changed)
        self.window.findChild(QCheckBox, name="usereferncestock").toggled.connect(genobsResetForce('use_ext'))
        self.window.findChild(QCheckBox, name="start_hidden").toggled.connect(genobs('starthidden'))
        self.window.findChild(QCheckBox, name="adjust_currency").toggled.connect(genobsResetForce('adjust_to_currency'))
        self.window.home_currency_combo.currentTextChanged.connect(genobsResetForce('currency_to_adjust'))

        self.window.findChild(QPushButton, name="refresh_stock").pressed.connect(self.refresh_stocks)
        self.window.findChild(QPushButton, name="update_btn").pressed.connect(
            partial(self.update_graph,force=True,reset_ranges=ResetRanges.FORCE))
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
        self.window.startdate : QDateEdit
        self.window.startdate.editingFinished.connect(self.update_from_datefields)
        self.window.enddate.editingFinished.connect(self.update_from_datefields)
        self.window.save_graph_btn.pressed.connect(self.save_graph)
        self.window.load_graph_btn.pressed.connect(self.load_graph)


        for rad in self.rad_types:
            if not '_mode' in rad.objectName():
                rad.toggled.connect(partial(FormObserver.type_unite_toggled, self, rad.objectName()))

        #PySide6.QObject
        #connect()


        self.graphObj.minMaxChanged.connect(self.update_rangeb)
        self.graphObj.namesChanged.connect(self.update_range_num)
        self.graphObj.statusChanges.connect(self.update_status)

        self.json_editor.onCloseEvent.connect(self.on_json_closed)
        self._initiated=True

        self.load_jupyter_observers()

        self.window.findChild(QRadioButton, name="minimal_mode").toggled.connect(partial(self.change_mode, DisplayModes.MINIMAL))
        self.window.findChild(QRadioButton, name="full_mode").toggled.connect(
            partial(self.change_mode, DisplayModes.FULL))
        self.window.findChild(QRadioButton, name="nojpy_mode").toggled.connect(
            partial(self.change_mode, DisplayModes.NOJUPYTER))

        self.window.findChild(QRadioButton, name="jupyter_mode").toggled.connect(
            partial(self.change_mode, DisplayModes.JUPYTER))

        self.graphObj.finishedGeneration.connect(self.save_last_graph)

    def update_from_datefields(self):
        def todatetime(x):
            return pytz.UTC.localize( QDateTime(x,QTime(0,0,0)).toPython(), True)

        self.window.daterangepicker.start=todatetime(self.window.startdate.date())
        self.window.daterangepicker.end = todatetime(self.window.enddate.date())
        pair=(self.window.startdate.date(),self.window.enddate.date())
        #QDateTime(value[0], QTime())
        self.date_changed(list(map(todatetime,pair)),False )
    def change_mode(self,mode,val):
        def update_sizes():
            but=[self.window.adjust_group,            self.window.main_group,            self.window.note_group,self.window.graph_groupbox]
            for x in but:
                if not x.isHidden():
                    x.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
                    x.resize(x.maximumSize())
            self.window.resize(self.window.minimumSizeHint())
        def switch_adjust(tosize=True):

            x = self.window.frame_9


            self.window.main_group.hide()
            if tosize:
                self.window.horz_buttom.removeWidget(self.window.adjust_group)
                self.window.stock_vert.addWidget(self.window.adjust_group)
                self.window.savedgraph_group.hide()
                #self.window.currencygroup.hide()
                self.window.currencygroup.hide()
                self.window.gridLayout_11.removeWidget(self.window.currencygroup)
                #self.window.gridLayout_11.removeWidget(self.window.groupBox)
                self.window.gridLayout_11.removeWidget(self.window.savedgraph_group)

                #mylayout = QHBoxLayout()
                #mylayout.addWidget(self.window.groups_lay2)
                #mylayout.addWidget(self.window.groupBox)
                #self.window.adjust_group.setLayou(mylayout)
                #self.window.gridLayout_9.replaceWidget(self.window.groupBox_datepicker,self.placeholder)
                self.window.gridLayout_9.removeWidget(self.window.groupBox_datepicker)
                self.window.gridLayout_2.removeWidget(self.window.buttom_frame)
                self.window.gridLayout_2.addWidget(self.window.groupBox_datepicker,1, 0, 1, 2)


            else:
                self.window.horz_buttom.addWidget(self.window.adjust_group)
                self.window.stock_vert.removeWidget(self.window.adjust_group)
                self.window.gridLayout_11.addWidget(self.window.currencygroup, 0, 1, 1, 2)
                #self.window.gridLayout_11.addWidget(self.groupBox5, 1, 2, 1, 1)
                self.window.gridLayout_11.addWidget(self.window.savedgraph_group, 1, 0, 1, 2)

                self.window.gridLayout_2.removeWidget(self.window.groupBox_datepicker)
                self.window.gridLayout_9.addWidget(self.window.groupBox_datepicker, 0, 0, 1, 2)
                self.window.gridLayout_2.addWidget(self.window.buttom_frame, 1, 0, 1, 2)

                #self.window.gridLayout_9.replaceWidget(self.placeholder,self.window.groupBox_datepicker)

                self.window.savedgraph_group.show()
                self.window.currencygroup.show()

                #self.window.currencygroup.show()
            if tosize:
                self.window.frame_9.setMaximumSize(400, 900)
                #x.resize(x.maximumSize())
            else:
                self.window.frame_9.setMaximumSize(400,400)
        if val==False:
            return
        if self.current_mode == DisplayModes.MINIMAL:
            switch_adjust(False)

        if mode==DisplayModes.MINIMAL:

            self.window.buttom_frame.hide()

            self.window.adjust_group.show()
            switch_adjust(True)

            self.window.note_group.hide()
        elif mode==DisplayModes.FULL:
            self.window.buttom_frame.show()
            self.window.adjust_group.show()
            self.window.main_group.show()
            self.window.note_group.show()
        elif mode == DisplayModes.NOJUPYTER:
            self.window.buttom_frame.show()
            self.window.adjust_group.show()
            self.window.main_group.show()
            self.window.note_group.hide()
        else:
            #self.window.findChild(QSpacerItem,name='horizontalSpacer').hide()
            #self.window.findChild(QSpacerItem,name='horizontalSpacer_2').hide()
            self.window.buttom_frame.show()
            self.window.adjust_group.hide()
            self.window.main_group.hide()
            self.window.note_group.show()
        self.current_mode = mode
        timer=QTimer()
        timer.singleShot(1,update_sizes)

    @abstractmethod
    def update_stock_list(self):
        pass



