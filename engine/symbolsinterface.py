from abc import ABCMeta, abstractmethod

from engine.parameters import Parameters


class SymbolsInterface(metaclass=ABCMeta):
    TOADJUST = ['avg_cost_by_stock', 'rel_profit_by_stock']
    #TOADJUST = ['unrel_profit', 'value', 'avg_cost_by_stock', 'rel_profit_by_stock']
    TOADJUSTLONG = ['alldates', 'unrel_profit', 'value', 'tot_profit_by_stock']
    TOKEEP= ['holding_by_stock','rel_profit_by_stock','avg_cost_by_stock']

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