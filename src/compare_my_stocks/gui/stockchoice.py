import logging
# importing libraries
import operator

from PySide6.QtCore import SIGNAL, QAbstractTableModel
from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import *
import sys

# creating a class
# that inherits the QDialog class
from input.inputsource import InputSource, InputSourceInterface


class MyTableModel(QAbstractTableModel):
    def __init__(self, parent, results, *args):
        header = list(results[0].keys())
        datalist = [list(r.values()) for r in results]
        QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = datalist
        self.header = header
        self._results=results

    def row_by_index(self,index):
        return self._results[index]

    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.mylist[0])
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.mylist = sorted(self.mylist,
                             key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.emit(SIGNAL("layoutChanged()"))


class Window(QDialog):
    myinstance=None

    # constructor
    def __init__(self,inpsource,initial):
        self._inpsource :InputSourceInterface =inpsource
        self.selected=None
        super(Window, self).__init__()

        # setting window title
        self.setWindowTitle("Symbol Picker")

        # setting geometry to the window
        self.setGeometry(100, 100, 300, 400)

        # creating a group box
        self.formGroupBox = QGroupBox("")


        # creating combo box to select degree
        self.choices = QTableView()
        self.choices.resizeColumnsToContents()
        # enable sorting
        self.choices.setSortingEnabled(True)
        self.choices.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.choices.setSelectionMode(QAbstractItemView.SingleSelection)
        #model = QStandardItemModel()
        #self.degreeComboBox.setModel(model)
        #self.degreeComboBox.selectionChanged()
        # adding items to the combo box
        #.degreeComboBox.addItems(["BTech", "MTech", "PhD"])

        # creating a line edit
        self.symbolName = QLineEdit()
        self.symbolName.setText(initial)
        self.symbolName.editingFinished.connect(self.edited)

        # calling the method that create the form
        self.createForm()

        # creating a dialog button for ok and cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # adding action when form is accepted
        self.buttonBox.accepted.connect(self.getInfo)
        #self.buttonBox.

        # adding action when form is rejected
        self.buttonBox.rejected.connect(self.reject)

        # creating a vertical layout
        mainLayout = QVBoxLayout()

        # adding form group box to the layout
        mainLayout.addWidget(self.formGroupBox)

        # adding button box to the layout
        mainLayout.addWidget(self.buttonBox)

        # setting lay out
        self.setLayout(mainLayout)

    def edited(self):
        sym=self.symbolName.text()
        try:

            results,_,_=self._inpsource.resolve_symbols(sym,strict=False)
        except:
            import traceback;traceback.print_exc()
        if len(results)==0:
            return
        table_model = MyTableModel(self,results)
        self.choices.setModel(table_model)
    # get info method called when form is accepted
    def getInfo(self):

        # printing the form information
        #logging.debug(("Person Name : {0}".format(self.nameLineEdit.text())))
        #logging.debug(("Degree : {0}".format(self.degreeComboBox.currentText())))
        #logging.debug(("Age : {0}".format(self.ageSpinBar.text())))
        indexes=self.choices.selectedIndexes()
        if len(indexes)>0:
            self.selected=self.choices.model().row_by_index(indexes[0].row())

        # closing the window
        self.close()

    # creat form method
    def createForm(self):

        # creating a form layout
        layout = QFormLayout()

        # adding rows
        # for name and adding input text
        layout.addRow(QLabel("Name"), self.symbolName)

        # for degree and adding combo box
        layout.addRow(QLabel("Choices"), self.choices)

        # for age and adding spin box
        #layout.addRow(QLabel("Age"), self.ageSpinBar)

        # setting layout
        self.formGroupBox.setLayout(layout)

def PickSymbol(inpsource,initial):
    w= Window(inpsource,initial)
    # showing the window
    w.exec_()
    return w.selected



