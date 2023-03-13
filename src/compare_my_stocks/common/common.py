import logging
import dataclasses
import os
from abc import ABC, abstractmethod
from collections import namedtuple
from datetime import datetime

import matplotlib
import numpy as np
import pytz

localize_it = lambda x: (pytz.UTC.localize(x, True) if not x.tzinfo else x)
def unlocalize_it(date):
    d=localize_it(date)
    return d.replace(tzinfo=None)

import sys

from django.core.serializers.json import DjangoJSONEncoder

from common.loghandler import init_log

#Found to work. Not the best.
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('Voila').setLevel(logging.ERROR)
init_log()
matplotlib.set_loglevel("INFO")

def index_of(val, in_list):
    try:
        return in_list.index(val)
    except ValueError:
        return -1

from enum import Flag, auto, Enum

class CombineStrategy(int,Flag):
    PREFERSTOCKS=auto()
    PREFERIB=auto()

class Types(int,Flag):
    ABS = 0
    PRICE=auto()
    VALUE=auto()
    PROFIT = auto()
    TOTPROFIT = auto() #Though I wanted it to be X | Y
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


class VerifySave(int,Enum):
    DONT=0,
    Ask=1,
    ForceSave=2



class UseCache(int,Enum):
    DONT=0
    USEIFAVALIABLE=1
    FORCEUSE=2

class LimitType(int,Flag):
    RANGE=0
    MIN=auto()
    MAX=auto()

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


def neverthrow(f,*args,**kwargs):
    try:
        return f(*args,**kwargs)
    except:
        return None


from Pyro5.errors import format_traceback


def simple_exception_handling(err_description=None,return_succ=False,never_throw=False):
    def decorated(func):
        def internal(*args,**kwargs):
            tostop= os.environ.get('PYCHARM_HOSTED') == '1'
            if 'config' in globals():
                tostop = tostop and globals()['config'].STOP_EXCEPTION_IN_DEBUG

            if tostop and not never_throw:
                return func(*args,**kwargs)
            else:
                try:
                    return func(*args,**kwargs)
                except Exception as e:
                    TmpHook.GetExceptionHook().emit(e)
                    if err_description:
                        logging.error((err_description))
                    print_formatted_traceback()
                    if return_succ:
                        return 0
        return internal
    return decorated



def print_formatted_traceback(detailed=True):
    logging.error((''.join([x[:500] for x in format_traceback(detailed=detailed)] )))

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
        logging.debug(('err EPS'))
        pass
    ind = np.isnan(arr)
    if remove_zeros:
        ind = np.bitwise_or(ind ,arr ==0)

    getnan = np.any(ind, axis=0)
    ls = list(getnan)
    if last:
        ls.reverse()
    ind=index_of(False,ls)



    return ( ind * (-1 if last else 1)) if ind!=-1 else -1

class NoDataException(Exception):
    pass

class MySignal:

    def __init__(self,typ):
        from PySide6 import QtCore
        from PySide6.QtCore import Signal
        Emitter = type('Emitter', (QtCore.QObject,), {'signal': Signal(typ)})
        self.emitter = Emitter()

    def emit(self,*args,**kw):
        self.emitter.signal.emit(*args,**kw)

    def connect(self,  slot):
        self.emitter.signal.connect(slot)

class SafeSignal:
    def __init__(self,signal,cond):
        self._signal=signal
        self._cond=cond

    def emit(self,*args,**kw):
        if self._cond():
            self._signal.emit(*args,**kw)

    def connect(self,  slot):
        self._signal.connect(slot)

Serialized=namedtuple('Serialized', ['origdata','beforedata','afterdata','act','parameters','Groups'])
dictfilt = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])
dictnfilt = lambda x, y: dict([(i, x[i]) for i in x if not(i in set(y))])

lmap= lambda x,y: list(map(x,y))
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

import dateutil.parser
def conv_date(dat):
    if type(dat)==str:
         return dateutil.parser.parse(dat)
    elif type(dat)==datetime:
        return dat
    else:
        raise AttributeError("no attr")


class EnhancedJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        try:
            return super().default(o)
        except TypeError:
            if hasattr(o,"dic"): #SimpleSymbol
                return o.dic
            logging.debug((f"{o,type(o)} is not json.. "))
            return o.__dict__


def need_add_process(config):
    return config.INPUTSOURCE== InputSourceType.IB

def log_conv(*tup):
    return '\t'.join([str(x) for x in tup ])


class TmpHook:
    EXCEPTIONHOOK=MySignal(Exception)
    MyHook=None
    @classmethod
    def GetExceptionHook(cls):
        if cls.MyHook is None:
            cls.MyHook=TmpHook()
        return cls.MyHook.EXCEPTIONHOOK

