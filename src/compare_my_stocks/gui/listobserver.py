from PySide6.QtWidgets import QListWidget, QListWidgetItem

from common.dolongprocess import DoLongProcessSlots
from engine.parameters import copyit
from engine.symbols import AbstractSymbol, SimpleSymbol

from gui.stockchoice import PickSymbol


class MyItem(QListWidgetItem,AbstractSymbol):
    __hash__ = AbstractSymbol.__hash__
    def __init__(self,text,parent=None,*args):
        self._dic=None
        if type(text) == dict:
            self._dic=text
            text=self._dic['symbol']
        super().__init__(text,parent,*args)
    def __str__(self):
        return self.text()

    @property
    def dic(self):
        return self._dic

    @property
    def symbol(self):
        return self.text()


def to_simple(ls):
    return list(map(SimpleSymbol,ls))


class ListsObserver():
    def process_elem(self,params):
        while True:
            ls = to_simple(self.addqueue)
            self.window.last_status.setText('processing added stocks')
            self.graphObj.process(set(ls),params) #blocks. should have mutex here. We do partial update with params and list..
            self.window.last_status.setText('finshed processing')
            self.addqueue = list(set(self.addqueue) - set(ls))
            if len(self.addqueue)==0:
                break


    def __init__(self):
        self.addqueue=[]
        self.grep_from_queue_task= DoLongProcessSlots(self.process_elem)
        self.current_symbol=None
        self.last_txt=None

    def process_if_needed(self,stock):
        if not str(stock) in self.graphObj._usable_symbols:
            self.addqueue+=[SimpleSymbol(stock)]

            if not self.grep_from_queue_task.is_started: #theorticaly it could be that it was started but just on the last two lines. unlikely..
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
        items = set([x for x in org.selectedItems()])
        items = items - set([dst.item(x) for x in range(dst.count())])
        dst.addItems(items)
        ListsObserver.del_selected(org)

    def add_to_ref(self):
        self.generic_add_lists(self.window.orgstocks, self.window.refstocks)

    def add_to_sel(self):
        self.generic_add_lists(self.window.refstocks, self.window.orgstocks)

    def lookup_symbol(self):
        self.current_symbol = PickSymbol(self.graphObj.inputsource,self.window.addstock.currentText())
        if self.current_symbol==None:
            return
        #self.last_txt=self.current_symbol.text()
        self.last_txt = self.current_symbol['symbol']
        self.window.addstock.setEditText(self.last_txt+"*")


    def stock_edited(self):
        if not self.last_txt:
            return
        if self.last_txt+"*"!=self.window.addstock.currentText():
            self.current_symbol=None
            self.last_txt=None

    def add_selected(self):
        org: QListWidget = self.window.orgstocks  # type:
        self.add_current_to(org)

    def add_reserved(self):
        org: QListWidget = self.window.refstocks  # type:
        self.add_current_to(org)


    def add_current_to(self, org):
        text = self.window.addstock.currentText() if self.current_symbol==None else self.current_symbol
        it=MyItem(text)
        self.process_if_needed(it)
        org.addItem(it)
        self.update_graph(1)
