from abc import ABC, abstractmethod
from collections import namedtuple

import numpy as np


import sys
from PySide6 import QtCore
from PySide6.QtCore import  Signal


from enum import Flag, auto, Enum


class Types(int,Flag):
    ABS = 0
    PRICE=auto()
    VALUE=auto()
    PROFIT = auto()
    TOTPROFIT = auto()
    RELPROFIT = auto()
    PERATIO = auto()
    PRICESELLS=auto()
    THEORTICAL_PROFIT=auto()

    RELTOMAX=auto()
    RELTOMIN=auto()
    RELTOSTART=auto()
    RELTOEND=auto()
    PRECENTAGE=auto()
    DIFF=auto()
    COMPARE=auto()
    PRECDIFF = PRECENTAGE | DIFF




class UseCache(int,Enum):
    DONT=0
    USEIFAVALIABLE=1
    FORCEUSE=2


class UniteType(int,Flag):
    NONE=0
    SUM=auto()
    AVG=auto()
    MIN=auto()
    MAX=auto()
    ADDTOTAL=auto()
    ADDPROT=auto()
    ADDTOTALS= ADDPROT | ADDTOTAL
#did this trick to keep ADDTOTAL
class InputSourceType(Flag):
    Cache=0
    IB=auto()
    InvestPy=auto()


def addAttrs(attr_names):
  def deco(cls):
    for attr_name in attr_names:
      def getAttr(self, attr_name=attr_name):
        return getattr(self, "_" + attr_name)
      def setAttr(self, value, attr_name=attr_name):
        setattr(self, "_" + attr_name, value)
      prop = property(getAttr, setAttr)
      setattr(cls, attr_name, prop)
      #setattr(cls, "_" + attr_name, None) # Default value for that attribute
    return cls
  return deco

EPS=0.0001

def get_first_where_all_are_good(arr,remove_zeros=False,last=0):
    try:
        arr[np.abs(arr) < EPS] = 0
    except:
        print('err EPS')
        pass
    ind = np.isnan(arr)
    if remove_zeros:
        ind = np.bitwise_or(ind ,arr ==0)

    getnan = np.any(ind, axis=0)
    ls = list(getnan)
    if last:
        ls.reverse()
    ind=ls.find(False)
    return ( ind * (-1 if last else 1)) if ind!=-1 else -1

class NoDataException(Exception):
    pass

class MySignal:
    def __init__(self,typ):
        Emitter = type('Emitter', (QtCore.QObject,), {'signal': Signal(typ)})
        self.emitter = Emitter()

    def emit(self,*args,**kw):
        self.emitter.signal.emit(*args,**kw)

    def connect(self,  slot):
        self.emitter.signal.connect(slot)


Serialized=namedtuple('Serialized', ['origdata','beforedata','afterdata','act'])
dictfilt = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
dictnfilt = lambda x, y: dict([(i, x[i]) for i in x if not(i in set(y))])

# def ifnn(t,v,els=None):
#     if t is not None:
#         return v
#     else:
#         return els

def ifnn(t, v, els=lambda: None):
    if t is not None:
        return v()
    else:
        return els()
