from abc import ABCMeta, abstractmethod
from enum import auto, Flag


class TrascationImplemenetorInterface(metaclass=ABCMeta):
    @abstractmethod
    def populate_buydic(self):
        pass



    @abstractmethod
    def get_portfolio_stocks(self):
        ...
class TransactionSourceType(Flag):
    Cache=0
    IB=auto()
    MyStock=auto()

class TransactionHandlerInterface(metaclass=ABCMeta):
    '''
    As seen by others
    '''

    @abstractmethod
    def process_transactions(self):
        ...

    @property
    def buydic(self) -> dict:
        ...

    def get_portfolio_stocks(self):  # TODO:: to fix
        ...

    def save_cache(self):
        ...