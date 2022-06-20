from abc import abstractmethod
from abc import ABC

class AbstractSymbol(ABC):

    @abstractmethod
    @property
    def dic(self):
        ...
    @abstractmethod
    @property
    def symbol(self):
        ...

class SimpleSymbol(AbstractSymbol):
    @property
    def dic(self):
        return self._dic

    @property
    def symbol(self):
        return self.text

    def __str__(self):
        return self.text


    def __init__(self,t):
        self._dic=None
        if type(t)==str:
            self.text=t
        elif type(t)==dict:
            self._dic=t
            self.text=t['symbol']
        elif isinstance(t,AbstractSymbol):
            self._dic=t.dic
            self.text=t.symbol


