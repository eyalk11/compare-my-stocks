from abc import ABCMeta, abstractmethod
from typing import Set
from abc import ABC
from engine.symbolsinterface import SymbolsInterface

class CompareEngineInterface(SymbolsInterface):
    @abstractmethod
    def update_graph(self, params):
        pass


    @abstractmethod
    def process(self,  partial_symbol_update=Set,params=None):
        ...

    @abstractmethod
    def serialized_data(self):
        ...

    @abstractmethod
    def get_portfolio_stocks(self):  # TODO:: to fix
        ...

    @property
    @abstractmethod
    def adjust_date(self):
        ...
    @adjust_date.setter
    @abstractmethod
    def adjust_date(self,v):
        ...

    @property
    @abstractmethod
    def input_processor(self):
        ...
    @property
    @abstractmethod
    def transaction_handler(self):
        ...
    @property
    @abstractmethod
    def colswithoutext(self):
        ...
    @property
    @abstractmethod
    def minValue(self):
        ...
    @property
    @abstractmethod
    def maxValue(self):
        ...
    @property
    @abstractmethod
    def maxdate(self):
        ...
    @property
    @abstractmethod
    def mindate(self):
        ...
    @property
    @abstractmethod
    def to_use_ext(self):
        ...

    @to_use_ext.setter
    @abstractmethod
    def to_use_ext(self, v):
        ...

    @property

    @abstractmethod
    def used_unitetype(self):
        ...

    @used_unitetype.setter
    @abstractmethod
    def used_unitetype(self,v):
        ...

    @property
    @abstractmethod
    def usable_symbols(self):
        ...
    @abstractmethod
    def show_hide(self,val):
        ...