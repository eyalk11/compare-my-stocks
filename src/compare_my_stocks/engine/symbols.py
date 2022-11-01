import json
from abc import abstractmethod
from abc import ABC

from common.common import EnhancedJSONEncoder


class AbstractSymbol():


    @property
    @abstractmethod
    def dic(self):
        ...

    @property
    @abstractmethod
    def symbol(self):
        ...

    def __hash__(self): #TODO:to precalc
        if self.dic==None:
            return hash(self.symbol) #act like a string..
        return hash(json.dumps(self.dic,cls=EnhancedJSONEncoder))

    def __eq__(self, other):
        return hash(other)==hash(self) #work with string
    def __getattr__(self, item):
        if  self.dic:
            t= self.dic.get(item)
            if t!=None:
                return t
        raise AttributeError("%r object has not attribute %r" % (self.__class__.__name__, item))

class SimpleSymbol(AbstractSymbol):
    __hash__ = AbstractSymbol.__hash__
    @property
    def dic(self):
        return self._dic

    @property
    def symbol(self):
        return self._text

    def __str__(self):
        return str(self._text)
    def __gt__(self, other):
        return self.symbol.__gt__(str(other))

    def __lt__(self, other):
        return self.symbol.__lt__(str(other))

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d
    # def __getstate__(self):
    #     if self._dic == None:
    #         return {'symbol':self.symbol}
    #     else:
    #         return {'symbol': self.symbol,'dic':self.dic}

    def __init__(self,t):
        self._dic=None
        if type(t)==str:
            self._text=t
        elif type(t)==dict:
            self._dic=t
            self._text=t['symbol']
        elif isinstance(t,AbstractSymbol):
            self._dic=t.dic
            self._text=t.symbol
        else:
            if hasattr(t,'text'):
                self._text=t.text()
            else:
                self._text=str(t)


