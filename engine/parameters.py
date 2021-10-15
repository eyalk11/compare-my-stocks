import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from config import config
from common.common import Types, UseCache, UniteType


def paramaware(klass):
    orginit=klass.__init__
    orgset = klass.__setattr__

    def __nsetattr__(self, name, value):
        if hasattr(self,'_changed_keys') and name in self.__dataclass_fields__.keys():
            self._changed_keys.add(name)
        return orgset(self,name,value)

    def newinit(self,*args,**kwargs):
        orginit(self,*args,**kwargs)
        self._changed_keys=set(kwargs.keys()).intersection(set(self.__dataclass_fields__.keys())) #TODO: take care of args.

    def update_from(self,another):
        dic= dataclasses.asdict(another)
        for k in another._changed_keys:
            setattr(self,k,dic[k])

    klass.__init__=newinit
    klass.__setattr__=__nsetattr__
    klass.update_from=update_from

    return klass


@paramaware
@dataclass
class Parameters:
    groups : list =field(default_factory=list)
    mincrit : int = config.MIN
    maxnum : int = config.MAXCOLS
    type : Types =Types.VALUE
    ext : list =field(default_factory=config.EXT.copy)
    increase_fig: bool =1
    _fromdate : datetime=None
    _todate: datetime =None
    isline: bool =True
    starthidden : bool =0
    compare_with: str =None
    portfolio: str  = config.DEF_PORTFOLIO
    use_cache : UseCache =UseCache.USEIFAVALIABLE
    def_fig_size : tuple = config.DEF_FIG_SIZE
    unite_by_group : UniteType =UniteType.NONE
    show_graph : bool =False
    use_groups: bool =True
    use_ext: bool = True
    selected_stocks: list =field(default_factory=list)
    shown_stock: list =field(default_factory=list)
    increase_fig: bool = False
    baseclass = dataclasses.InitVar

    def __post_init__(self,baseclass=None):
        # super(Parameters,self).__init__(*args,**kwargs)
        self._baseclass=baseclass


    @property
    def todate(self):
        return self._todate

    @todate.setter
    def todate(self, value):
        self._todate=value
        if self._baseclass:
            self._baseclass.adjust_date=1
        pass

    @property
    def fromdate(self):
        return self._fromdate

    @fromdate.setter
    def fromdate(self, value):
        self._fromdate = value
        if self._baseclass:
            self._baseclass.adjust_date = 1
        pass

class ParameterError(Exception):
    pass



class HasParamsAndGroups(ABC):
    @property
    @abstractmethod
    def params(self) -> Parameters:
        ...
    @classmethod
    @property
    def Groups(self) -> dict:
        ...