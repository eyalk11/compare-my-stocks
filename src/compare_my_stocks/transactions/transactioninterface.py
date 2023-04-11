from abc import ABCMeta, abstractmethod
from collections import namedtuple
from datetime import datetime
from enum import auto,  Enum 
from typing import Dict

class TransactionSource(Enum):
    IB=1
    STOCK=2
    CACHEDIBINSTOCK=3
    
BuyDictItem=namedtuple("BuyDictItem","Qty Cost Symbol Notes IBContract Source",defaults=[None]*5)
BuyDictType=Dict[datetime,BuyDictItem]

class TransactionHandlerInterface(metaclass=ABCMeta):
    '''
    As seen by others
    '''

    @abstractmethod
    def process_transactions(self):
        ...

    @property
    def buydic(self) -> Dict[datetime,BuyDictItem]:
        ...

    def get_portfolio_stocks(self):  # TODO:: to fix
        ...

    def save_cache(self):
        ...


class TransactionHandlerImplementator(metaclass=ABCMeta):
    @abstractmethod
    def populate_buydic(self):
        pass

    @abstractmethod
    def set_vars_for_cache(self, v):
        pass

    @abstractmethod
    def get_vars_for_cache(self):
        pass
    @abstractmethod
    def get_portfolio_stocks(self):
        ...
