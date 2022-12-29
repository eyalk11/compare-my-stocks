from abc import ABCMeta, abstractmethod, ABC
from typing import Generic, Set

from engine.parameters import Parameters
from input.inputsource import InputSource, InputSourceInterface
from transactions.transactioninterface import TransactionHandlerInterface

'''
A subset of compareengine. Used by input processor to resolve it.
'''

class SymbolsInterface(ABC):
    TOADJUST = ['avg_cost_by_stock', 'rel_profit_by_stock']
    #TOADJUST = ['unrel_profit', 'value', 'avg_cost_by_stock', 'rel_profit_by_stock']
    TOADJUSTLONG = ['alldates', 'unrel_profit', 'value', 'tot_profit_by_stock']
    TOKEEP= ['holding_by_stock','rel_profit_by_stock','avg_cost_by_stock','peratio','pricesells']

    # @property casues some headache.
    # @abstractmethod
    # def symbol_info(self):
    #     ...
    @property
    @abstractmethod
    def usable_symbols(self):
        ...

    @property
    @abstractmethod
    def inputsource(self) -> InputSourceInterface:
        ...

    @abstractmethod
    def get_options_from_groups(self, ls):
        ...

    @abstractmethod
    def read_groups_from_file(self):
        pass

    @abstractmethod


    def required_syms(self,include_ext = True, want_portfolio_if_needed = False, want_unite_symbols = False, only_unite = False):
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

