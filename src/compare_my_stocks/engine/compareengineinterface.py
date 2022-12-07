from abc import ABCMeta, abstractmethod
from typing import Set

from engine.symbolsinterface import SymbolsInterface

class CompareEngineInterface(SymbolsInterface):
    @abstractmethod
    def update_graph(self, params):
        pass


    @abstractmethod
    def process(self,  partial_symbol_update=Set,params=None):
        ...

    @abstractmethod
    def get_portfolio_stocks(self):  # TODO:: to fix
        ...