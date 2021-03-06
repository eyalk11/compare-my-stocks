from abc import ABCMeta, abstractmethod
from typing import Generic, Set

from engine.parameters import Parameters
from input.inputsource import InputSource


class SymbolsInterface(metaclass=ABCMeta):
    TOADJUST = ['avg_cost_by_stock', 'rel_profit_by_stock']
    #TOADJUST = ['unrel_profit', 'value', 'avg_cost_by_stock', 'rel_profit_by_stock']
    TOADJUSTLONG = ['alldates', 'unrel_profit', 'value', 'tot_profit_by_stock']
    TOKEEP= ['holding_by_stock','rel_profit_by_stock','avg_cost_by_stock','peratio','pricesells']

    @property
    @abstractmethod
    def inputsource(self) -> InputSource:
        pass

    @abstractmethod
    def get_options_from_groups(self, ls):
        pass

    @abstractmethod
    def read_groups_from_file(self):
        pass

    @abstractmethod
    def required_syms(self, include_ext, want_it_all, data_symbols_for_unite):
        pass

    @property
    @abstractmethod
    def Categories(self):
        ...

    @property
    @abstractmethod
    def params(self) -> Parameters:
        ...
    @property
    @abstractmethod
    def Groups(self) -> dict:
        ...

    @abstractmethod
    def get_portfolio_stocks(self):
        ...

    @abstractmethod
    def process(self,  partial_symbol_update=Set,params=None):
        ...