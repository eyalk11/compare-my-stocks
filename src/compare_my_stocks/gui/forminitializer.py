import logging

import PySide6.QtWidgets


from PySide6.QtWidgets import QRadioButton, QCheckBox, QListWidget, QSizePolicy,QComboBox

from graph.pyqtgraph_canvas import PyQtGraphCanvas

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
        self._canvas = PyQtGraphCanvas()
        self.window.graph_groupbox.layout().addWidget(self._canvas)
        self._canvas.xRangeChanged.connect(self._on_chart_xrange)

    @simple_exception_handling(err_description="chart->datepicker sync failed",
                                never_throw=True)
    def _on_chart_xrange(self, start, end):
        logging.debug(f"[chart-zoom] _on_chart_xrange start={start} end={end}")
        """Mirror the chart's visible x-range into the DatePicker widgets.

        Visual sync only — does NOT trigger date_changed / re-filter, so
        zooming the chart stays a free interaction. Slider signals are
        blocked during the update to avoid the feedback loop
        (slider.setValue → dateValueChanged → date_changed → update_graph
        → setXRange → ...).
        """
        if start is None or end is None:
            return
        self.window.startdate.blockSignals(True)
        self.window.enddate.blockSignals(True)
        try:
            self.window.startdate.setDateTime(start)
            self.window.enddate.setDateTime(end)
        finally:
            self.window.startdate.blockSignals(False)
            self.window.enddate.blockSignals(False)
        slider = getattr(self.window, 'daterangepicker', None)
        if slider is not None:
            slider.blockSignals(True)
            try:
                slider.datevalue = (start, end)
            finally:
                slider.blockSignals(False)


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
                flag = getattr(UniteType, name)
                if flag == UniteType.NONE:
                    # NONE has no bit, so & always yields 0 — treat it as
                    # "checked iff no exclusive base-mode bit is set".
                    EXCLUSIVES = UniteType.SUM | UniteType.AVG | UniteType.MIN | UniteType.MAX
                    rad.setChecked((unite & EXCLUSIVES) == 0)
                else:
                    rad.setChecked(bool(unite & flag))
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
        self.window.findChild(QCheckBox, name="WEIGHTED").setChecked(self.graphObj.params.weighted_for_portfolio)
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
            # Block signals: setCurrentIndex/setCurrentText emit
            # currentIndexChanged, which would route to compare_changed and
            # OR Types.COMPARE into params.type even when the saved graph
            # had it off. ignore_updates_for_now also guards this, but
            # a deferred index resolution (when items are added later) can
            # fire the signal outside the guard window.
            was_blocked = wc.blockSignals(True)
            try:
                wc.setCurrentIndex(ind)
                if ind == -1:
                    wc.setCurrentText(self.graphObj.params.compare_with)
            finally:
                wc.blockSignals(was_blocked)
        self.window.findChild(QCheckBox, name="COMPARE").setChecked(self.graphObj.params.type & Types.COMPARE)
        if initial:
            self.load_existing_graphs()
        self.ignore_updates_for_now = False

    def set_groups_values(self, isinit=1,isinitialforstock=1):
        logging.debug(f"GUI set_groups_values: isinit={isinit} isinitialforstock={isinitialforstock} ext_in={self.graphObj.params.ext}")
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

        options = list(self.graphObj.Groups.keys()) + ['Portfolio'] #add constant
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
        # Preserve the user's lo/hi if they still fit inside the new
        # data bounds — otherwise the slider handles get yanked back to
        # the data extremes on every redraw and the user can't move them.
        # Reset only when the previous range is stale (out of bounds, or
        # unset) — that's the Type/Unite-switch case the regression test
        # in test_forminitializer_ranges.py protects against.
        cur = getattr(self.graphObj.params, 'valuerange', None)
        if (cur is None
                or cur[0] is None or cur[1] is None
                or cur[0] < minmax[0] or cur[1] > minmax[1]
                or cur[0] >= cur[1]):
            self.window.min_crit.setValue(minmax)
            self.graphObj.params.valuerange = list(minmax)
        else:
            self.window.min_crit.setValue(tuple(cur))
        self.disable_slider_values_updates = False

    def update_range_num(self,nuofoptions):
        if nuofoptions==0:
            nuofoptions=1
        self.disable_slider_values_updates=True
        self.window.max_num.setRange(0, nuofoptions)
        # Same preservation logic as update_rangeb: keep the user's
        # numrange selection across redraws unless it's stale.
        cur = getattr(self.graphObj.params, 'numrange', None)
        stale = (cur is None
                 or cur == (None, None)
                 or cur[0] is None or cur[1] is None
                 or cur[0] < 0 or cur[1] > nuofoptions
                 or cur[0] >= cur[1])
        if stale:
            self.window.max_num.setValue((0, nuofoptions))
            self.graphObj.params.numrange = (None, None)
        else:
            self.window.max_num.setValue(tuple(cur))
        self.disable_slider_values_updates = False

    def update_ranges(self,reset_type=ResetRanges.IfAPROP):
        nuofoptions = len(self.graphObj.colswithoutext)

        self.disable_slider_values_updates=True #convert to ..
        if nuofoptions==0:
            nuofoptions =1
        self.window.max_num.setRange(0, nuofoptions)

        mn, mx = self.graphObj.minValue, self.graphObj.maxValue
        if mn is None or mx is None or mn != mn or mx != mx:
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
            self.graphObj.params.valuerange = [self.graphObj.minValue, self.graphObj.maxValue]
            self.graphObj.params.numrange = (None, None)
        self.disable_slider_values_updates = False

    @simple_exception_handling(err_description="Error in adding items")
    def update_stock_list(self,isinitial=0,justorgs=False):
            org: QListWidget = self.window.orgstocks  # type:
            
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
                # Belt-and-suspenders: blockSignals on the combo, AND raise
                # ignore_updates_for_now. blockSignals alone isn't bulletproof
                # for editable combos (the inner QLineEdit can re-sync and
                # re-fire currentIndexChanged after blockSignals(False)). The
                # variable guard catches the deferred slot path too.
                prev_ignore = getattr(self, 'ignore_updates_for_now', False)
                self.ignore_updates_for_now = True
                try:
                    for comp in  [self.window.comparebox,self.window.addstock] :
                        was_blocked = comp.blockSignals(True)
                        try:
                            comp.clear()
                            comp.addItems(alloptions)
                        finally:
                            comp.blockSignals(was_blocked)
                finally:
                    self.ignore_updates_for_now = prev_ignore
            
            
            
            
            
            #additems(org,self.graphObj.cols)
            refs: QListWidget = self.window.refstocks  # type:
            ext_snapshot = list(self.graphObj.params.ext or [])
            logging.debug(f"GUI update_stock_list: isinitial={isinitial} ext_snapshot={ext_snapshot} params.ext={self.graphObj.params.ext}")
            refs.clear()
            logging.debug(f"GUI update_stock_list after refs.clear: params.ext={self.graphObj.params.ext}")
            additems(refs, ext_snapshot)
            logging.debug(f"GUI update_stock_list after additems: params.ext={self.graphObj.params.ext} widget_count={refs.count()}")



