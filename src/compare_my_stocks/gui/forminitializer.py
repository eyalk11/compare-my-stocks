import logging

import PySide6.QtWidgets

from PySide6.QtWidgets import QRadioButton, QCheckBox, QListWidget, QSizePolicy,QComboBox
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from common.common import LimitType, UniteType, Types, index_of, really_close
from common.simpleexceptioncontext import simple_exception_handling
from config import config
from gui.forminitializerinterface import FormInitializerInterface
from gui.formobserver import FormObserver
from gui.formobserverinterface import ResetRanges
from gui.listobserver import additems


class FormInitializer(FormObserver, FormInitializerInterface):

    @property
    def window(self):
        return self.wind

    @window.setter
    def window(self, value):
        self.wind = value



    def __init__(self):
        super().__init__()

    @property
    def figure(self):
        return self._canvas.figure

    @property
    def axes(self):
        return self._canvas.ax

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
        self.window.filterrangesection.setTitle("Filter Range")
        self.window.filterrangesection.setContentLayout(self.window.formLayout)




    def set_all_toggled_value(self):
        type= self.graphObj.params.type
        unite = self.graphObj.params.unite_by_group
        limit_by= self.graphObj.params.limit_by
        for rad in self.rad_types:
            name=rad.objectName()
            #func= rad.setChecked if type(rad)==QCheckBox else rad.setCheckState
            #x : QCheckBox
            if name.startswith('limit'):
                name = name[len('limit') + 1:]
                rad.setChecked(bool(limit_by & getattr(LimitType,name)))
            elif name.startswith('unite'):
                name = name[len('unite') + 1:]
                rad.setChecked( bool(unite &  getattr(UniteType,name)))
            else:
                try:
                    rad.setChecked(bool(type & getattr(Types, name)))
                except:
                    pass

    def setup_controls_from_params(self,initial=True,isinitialforstock=None):
        self.ignore_cat_changes = False
        self.ignore_updates_for_now=True
        self.set_all_toggled_value()
        self.set_groups_values(isinitialforstock=initial if isinitialforstock==None else isinitialforstock)

        self.window.daterangepicker.update_prop()
        self.window.startdate.setDateTime(self.graphObj.mindate)
        self.window.enddate.setDateTime(self.graphObj.maxdate)
        self.window.daterangepicker.start=self.graphObj.mindate
        self.window.daterangepicker.end = self.graphObj.maxdate
        self.window.daterangepicker.update_obj()
        if not initial:
            self.window.daterangepicker.datevalue= (self.graphObj.params.fromdate,self.graphObj.params.todate)
        else:
            self.window.daterangepicker.dateValueChanged.connect(self.date_changed)
        self.window.use_groups.setChecked(self.graphObj.params.use_groups)
        self.window.findChild(QCheckBox, name="usereferncestock").setChecked(self.graphObj.params.use_ext)
        self.window.findChild(QCheckBox, name="limit_to_port").setChecked(self.graphObj.params.limit_to_portfolio)
        if self.graphObj.params.adjust_to_currency:
            self.window.findChild(QCheckBox, name="adjust_currency").setCheckState(PySide6.QtCore.Qt.CheckState.Checked)
        elif self.graphObj.params.adjusted_for_base_cur:
            self.window.findChild(QCheckBox, name="adjust_currency").setCheckState(PySide6.QtCore.Qt.CheckState.PartiallyChecked)
        else:
            self.window.findChild(QCheckBox, name="adjust_currency").setCheckState(PySide6.QtCore.Qt.CheckState.Unchecked)


        self.window.home_currency_combo.clear()
        self.window.home_currency_combo.addItems(list(config.Symbols.DefaultCurr), )


        if not initial and self.graphObj.params.compare_with:
            wc = self.window.comparebox

            l=[wc.itemText(x) for x in range(wc.count())]
            ind=index_of(self.graphObj.params.compare_with,l)
            self.window.comparebox.setCurrentIndex(ind)
            if ind==-1:
                self.window.comparebox.setCurrentText(self.graphObj.params.compare_with)
        self.window.findChild(QCheckBox, name="COMPARE").setChecked(self.graphObj.params.type & Types.COMPARE)
        if initial:
            self.load_existing_graphs()
        self.ignore_updates_for_now = False

    def set_groups_values(self, isinit=1,isinitialforstock=1):
        b=False
        wc: QComboBox= self.window.categoryCombo
        self.ignore_cat_changes = True
        if self.graphObj.Categories!=[wc.itemText(x) for x in range(wc.count())]:
            b=True

            wc.clear()
            wc.addItems(self.graphObj.Categories) #sorry

        if isinitialforstock and self.graphObj.params.cur_category:
            wc.setCurrentIndex(index_of( self.graphObj.params.cur_category ,self.graphObj.Categories) )
        self.ignore_cat_changes = False

        options = list(self.graphObj.Groups.keys())
        value = self.graphObj.params.groups if self.graphObj.params.groups != None else list()
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
        self.update_ranges(isinit+1) #if intial then force
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

    def update_ranges(self,reset_type=ResetRanges.IfAPROP):
        nuofoptions = len(self.graphObj.colswithoutext)

        self.disable_slider_values_updates=True #convert to ..
        if nuofoptions==0:
            nuofoptions =1
        self.window.max_num.setRange(0, nuofoptions)

        if self.graphObj.minValue is None or self.graphObj.maxValue is None:
            self.disable_slider_values_updates = False
            return
        if really_close(self.graphObj.minValue,self.graphObj.maxValue):
            logging.debug(('bad range'))
            self.window.min_crit.setRange(self.graphObj.minValue-0.1, self.graphObj.maxValue+0.1)
        else:
            self.window.min_crit.setRange(self.graphObj.minValue, self.graphObj.maxValue)

        if reset_type==ResetRanges.FORCE:
            self.window.max_num.setValue((0, nuofoptions))
            self.window.min_crit.setValue((self.graphObj.minValue, self.graphObj.maxValue))
        self.disable_slider_values_updates = False

    @simple_exception_handling(err_description="Error in adding items")
    def update_stock_list(self,isinitial=0,justorgs=False):
            org: QListWidget = self.window.orgstocks  # type:
            
            if  self.window.unite_NONE.isChecked() or not self.graphObj.params.use_groups:
                if self.graphObj.params.use_groups:
                    org.clear()
                    additems(org,self.graphObj.get_options_from_groups(self.graphObj.params.groups))
                elif isinitial:
                    org.clear()
                    additems(org,self.graphObj.params.selected_stocks)
            
            if justorgs:
                return
            

            alloptions= sorted(list(self.graphObj.usable_symbols)) #CompareEngine.get_options_from_groups([g for g in CompareEngine.Groups])
            
            #self._last_choice=  self.window.comparebox.currentText()
            if isinitial:
                for comp in  [self.window.comparebox,self.window.addstock] :
                    comp.clear()
                    comp.addItems(alloptions)
            
            
            
            
            
            #additems(org,self.graphObj.cols)
            refs: QListWidget = self.window.refstocks  # type:
            refs.clear()
            additems(refs, self.graphObj.params.ext)



class MplCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        FigureCanvasQTAgg.__init__(self, self.fig)
        FigureCanvasQTAgg.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvasQTAgg.updateGeometry(self)
