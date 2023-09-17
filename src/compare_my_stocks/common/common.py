import logging
import dataclasses
from collections import namedtuple
from datetime import datetime,date
from functools import wraps
import time
from typing import TypeVar
from typing_extensions import ParamSpec
import numpy as np
import pytz
import psutil
from common.simpleexceptioncontext import simple_exception_handling, SimpleExceptionContext, print_formatted_traceback

T = TypeVar('T')
P = ParamSpec('P')
Q = ParamSpec('Q')
U = TypeVar('U')

def ass(x):
    assert x is not None 
    return x 


def c(*cargs):
    def composed(*args,**kwargs):
        res = cargs[-1](*args,**kwargs)
        for a in cargs[:-1][::-1]:
            res = a(res)
        return res
    
    return composed 

def rc(*args):
    return c(*args)()

def subdates(a,b):
    ach=tzawareness(a,b) 
    return ach-b 

def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logging.debug(f'Function {func.__name__} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper

def checkIfProcessRunning(processName):
    '''
    Check if there is any running process that contains the given name processName.
    '''
    #Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def localize_it (x):
    if x is None:
        return None
    return (pytz.UTC.localize(x, True) if not x.tzinfo else x)
def unlocalize_it(date):
    d=localize_it(date)
    return d.replace(tzinfo=None)


from django.core.serializers.json import DjangoJSONEncoder


def to_yaml(enum_class):
    def to_yaml_inner(cls,enum_value):
        return cls.represent_scalar(f'{enum_class.__name__}',u'{.name}'.format(enum_value),style=' ' )

    def from_yaml(loader, node):
        #x=loader.construct_scalar(node)
        return enum_class[node.value]
    def add_stuff(yaml):
    # add the representer to the yaml serializer
        #yaml.add_representer(enum_class, to_yaml_inner)
        yaml.add_constructor(f'{enum_class.__name__}',from_yaml,Loader=yaml.CLoader)
    # add the to_yaml method to the enum class
    enum_class.to_yaml = to_yaml_inner #lambda self: yaml.dump({self.name: self}, default_flow_style=False)
    enum_class.from_yaml = from_yaml
    enum_class.add_stuff = add_stuff


    return enum_class


def index_of(val, in_list):
    try:
        return in_list.index(val)
    except ValueError:
        return -1

from enum import Flag, auto, Enum

@to_yaml
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


@to_yaml
class VerifySave(int,Enum):
    DONT=0,
    Ask=1,
    ForceSave=2



@to_yaml
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
@to_yaml
class InputSourceType(Flag):
    Cache=0
    IB=auto()
    InvestPy=auto()
    Polygon=auto()


def neverthrow(f,*args,default=None,**kwargs):
    try:
        return f(*args,**kwargs)
    except:
        return default



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
smap = lambda x,y: set(map(x,y))

# def ifnn(t,v,els=None):
#     if t is not None:
#         return v
#     else:
#         return els

#Write a function that gets two dates and converts the first to timezone aware if the other one is timezone aware
def tzawareness(d1,d2):
    if d2.tzinfo is not None:
        return localize_it(d1)
    else:
        return unlocalize_it(d1)


def ifnotnan(t, v, els=lambda x: None):
    if t is not None:
        return v(t)
    else:
        return els(t)
def selfifnn(t,el):
    if t is not None:
        return t
    else:
        return el

def ifnn(t, v, els=lambda: None):
    if t is not None:
        return v()
    else:
        return els()

import dateutil.parser
def conv_date(dat,premissive=True):
    if premissive and dat is None:
        dat=datetime.now()
    if type(dat)==str:
         return dateutil.parser.parse(dat)
    elif type(dat)==datetime:
        return dat
    elif 'Timestamp' in str(type(dat)):
        return dat.to_pydatetime()
    elif type(dat)==date:
        return datetime.fromordinal(dat.toordinal())
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
    return config.Input.INPUTSOURCE== InputSourceType.IB

def log_conv(*tup):
    return '\t'.join([str(x) for x in tup ])


# class TmpHook:
#     EXCEPTIONHOOK=MySignal(Exception)
#     MyHook=None
#     @classmethod
#     def GetExceptionHook(cls):
#         if cls.MyHook is None:
#             cls.MyHook=TmpHook()
#         return cls.MyHook.EXCEPTIONHOOK


@to_yaml
class TransactionSourceType(Flag):
    Cache=0
    IB=auto()
    MyStock=auto()
    Both= IB | MyStock


StandardColumns = ['Open', 'High', 'Low', 'Close']
