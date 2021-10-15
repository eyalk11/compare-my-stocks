from abc import ABC, abstractmethod

import numpy as np

USEWX=0
USEWEB=0
USEQT=1
import sys



from enum import Flag, auto, Enum


class Types(Flag):
    ABS = 0
    PRICE=auto()
    VALUE=auto()
    PROFIT = auto()
    TOTPROFIT = auto()
    RELPROFIT = auto()
    THEORTICAL_PROFIT=auto()

    RELTOMAX=auto()
    RELTOMIN=auto()
    RELTOSTART=auto()
    RELTOEND=auto()
    PRECENTAGE=auto()
    DIFF=auto()
    COMPARE=auto()
    PRECDIFF = PRECENTAGE | DIFF




class UseCache(Enum):
    DONT=0
    USEIFAVALIABLE=1
    FORCEUSE=2


class UniteType(Flag):
    NONE=0
    SUM=auto()
    AVG=auto()
    ADDTOTAL=auto()

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


def get_first_where_all_are_good(arr):
    getnan = np.any(np.isnan(arr), axis=0)
    return (list(getnan).index(False))

class NoDataException(Exception):
    pass