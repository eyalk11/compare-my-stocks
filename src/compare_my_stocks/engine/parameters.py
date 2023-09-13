import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import dateutil
import numpy

from common.paramaware import paramawareold
from config import config
from common.common import Types, UseCache, UniteType, LimitType, dictnfilt,tzawareness 
from engine.symbols import AbstractSymbol



#from dataclasses_json import dataclass_json

#@dataclass_json
@paramawareold
@dataclass
class Parameters:
    groups : list =field(default_factory=list)
    valuerange : List[float] = ( (-1)* numpy.inf, numpy.inf)
    numrange : List[int] = (None,None)
    type : Types =Types.VALUE
    _ext : list =field(default_factory=config.DefaultParams.EXT.copy)
    ext: dataclasses.InitVar[list] = field(default_factory=list) #same as reference stock
    increase_fig: bool =1
    _fromdate : datetime=None
    _todate: datetime =None
    transactions_fromdate : datetime = None
    transactions_todate: datetime = None
    isline: bool =True
    starthidden : bool =0
    compare_with: str =None
    portfolio: str  = None #The portfolio to read from transaction table in MyStocks
    use_cache : UseCache =UseCache.USEIFAVALIABLE
    def_fig_size : tuple = config.UI.DEF_FIG_SIZE
    unite_by_group : UniteType =UniteType.NONE
    show_graph : bool =False
    use_groups: bool =True
    use_ext: bool = True
    _selected_stocks: list =field(default_factory=list)
    shown_stock: list =field(default_factory=list)
    increase_fig: bool = False
    baseclass = dataclasses.InitVar
    ignore_minmax: bool = False
    adjusted_for_base_cur :bool =True
    adjust_to_currency : bool= True
    currency_to_adjust: str = None
    cur_category:str = None
    limit_by : LimitType = LimitType.RANGE
    limit_to_portfolio : bool =False
    resolve_hack: dict = field(default_factory=dict)
    show_transactions_graph : bool = True
    is_forced: bool = False #doesn't matter actually, only for caching

    #Resolve hack is meant to provide custom symbol data to the input processor
    #most of the code originally written to work with strings. So, here we input the entire info the dic and treat the symbol as dic.
    #Also useful in restoration.

    @property
    def selected_stocks(self):
        return self._selected_stocks

    @selected_stocks.setter
    def selected_stocks(self,v):
        self._selected_stocks=list(self.helper(v))
    @property
    def ext(self):
        return self._ext

    @ext.setter
    def ext(self,v):
        self._ext=list(self.helper(v))
    #def update_ext_with_hack(self,ls):

    def helper(self,ls):
        for l in ls:
            if isinstance(l,AbstractSymbol) and l.dic:
                self.resolve_hack[str(l.symbol)]=l
                yield str(l.symbol)
            else:
                yield str(l)


    @classmethod
    def load_from_json_dict(cls,dic):
        for d in dic:
            if 'date' in d and dic[d]:
                dic[d]= dateutil.parser.parse(dic[d])
        return Parameters(**dic)

    def __getstate__(self):
        return dictnfilt(self.__dict__,set(['_baseclass']))

    def __post_init__(self,ext,baseclass=None):
        if ext and type(ext)==list:
            self.ext=ext
        # super(Parameters,self).__init__(*args,**kwargs)
        self._baseclass=baseclass
        self.adjust_date=0
        self.is_forced=False #so that only if excplicitly set to true, it will be true


    @property
    def todate(self):
        return self._todate

    @todate.setter
    def todate(self, value):
        if not self.transactions_todate:
            self.transactions_todate = value

        value = tzawareness(value, self.transactions_todate)
        self._todate=value
        if (value is None) or (not self.transactions_todate) or  (self.transactions_todate and value > self.transactions_todate):
            self.transactions_todate = value


        self.adjust_date=1
        pass

    @property
    def fromdate(self):
        if  self._fromdate==None:
            return self.transactions_fromdate

        return self._fromdate

    @fromdate.setter
    def fromdate(self, value):
        self._fromdate = value
        if (not self.transactions_fromdate) or  (self.transactions_fromdate and value < self.transactions_fromdate):
            self.transactions_fromdate = value
        self.adjust_date = 1
        pass

class ParameterError(Exception):
    pass


def copyit(cls):
    return Parameters(**dataclasses.asdict(cls))
