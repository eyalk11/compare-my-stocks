from functools import partial

import PySide6.QtCore
from PySide6.QtWidgets import QCheckBox, QListWidget, QPushButton, QRadioButton

from common import UniteType, Types


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

    def compare_changed(self,text):

        self.window.findChild(QCheckBox, name="COMPARE").setChecked(1)
        self._graphObj.params.compare_with=text
        self._graphObj.params.type=self._graphObj.params.type | Types.COMPARE
        self.update_graph()

    def selected_changed(self,*args,**kw):
        self._graphObj.params.selected_stocks=[self.window.orgstocks.item(x).text()  for x in range(self.window.orgstocks.count())]
        #self.update_graph()

    def refernced_changed(self,*args,**kw):
        self._graphObj.params.ext=[self.window.orgstocks.item(x).text()  for x in range(self.window.refstocks.count())]
        #self.update_graph()

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
        self.window.comparebox.currentTextChanged.connect(self.compare_changed)
        self.window.orgstocks.model().rowsInserted.connect(self.selected_changed)
        self.window.orgstocks.model().rowsRemoved.connect(self.selected_changed)




        #model=PySide6.QtCore.QItemSelectionModel()
        #selection= PySide6.QtCore.QItemSelectionRange([options.index(v) for v in value])
        #model.select(selection, PySide6.QtCore.QItemSelectionModel.Select)
        #self.window.groups.setSelectionModel(model)

        #stockl=list(get_options_from_groups(d.value))






        for rad in self.window.findChildren(QRadioButton) + self.window.findChildren(QCheckBox,name="unite_ADDTOTAL")+ self.window.findChildren(QCheckBox, name="COMPARE"):
            rad.toggled.connect(partial(FormObserver.type_unite_toggled, self, rad.objectName()))