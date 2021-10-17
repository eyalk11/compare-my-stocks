from abc import ABCMeta, ABC

import matplotlib
import numpy
import numpy as np
import pandas


from PySide6 import QtCore
from PySide6.QtCore import  Signal

from common.common import Types, UniteType, NoDataException, get_first_where_all_are_good
#from compareengine import CompareEngine
from processing.actondata import ActOnData
from input.inputdata import InputData
from engine.parameters import HasParamsAndGroups, ParameterError

from typing import TypeVar, Generic, List, Type

T = TypeVar('T')

class MySignal:
    class Emitter(QtCore.QObject):
        signal = Signal(tuple)
        def __init__(self):
            super(MySignal.Emitter, self).__init__()

    def __init__(self):
        self.emitter = MySignal.Emitter()

    def emit(self,*args,**kw):
        self.emitter.signal.emit(*args,**kw)

    def connect(self,  slot):
        self.emitter.signal.connect(slot)

class MyIntSignal:
    class Emitter(QtCore.QObject):
        signal = Signal(int)
        def __init__(self):
            super(MyIntSignal.Emitter, self).__init__()

    def __init__(self):
        self.emitter = MyIntSignal.Emitter()

    def emit(self,*args,**kw):
        self.emitter.signal.emit(*args,**kw)

    def connect(self,  slot):
        self.emitter.signal.connect(slot)

#
# class MyIntSignal:
#     def __init__(self):
#         self.emitter = MyIntSignal.Emitter()
#
#     def emit(self,*args,**kw):
#         self.emitter.signal.emit(*args,**kw)
#
#     def connect(self,  slot):
#         self.emitter.signal.connect(slot)
#
# from abc import ABCMeta
#
#
# X= TypeVar('X')
# class MyABC(ABC,Generic[X]):
#     pass

#
# class NEmitter(QtCore.QObject,NEmitterAbs[X]):
#         signal = Signal(Type[S])
#         def __init__(self):
#             super(NEmitter, self).__init__()
# T = TypeVar('T')
#
# def addSignal(typ):
#     def decorator(klass):
#         klass.__new__ =Signal(typ)
#         return klass
#     return decorator
#
#
# class MySignal(Generic[T]):
#     def __new__(cls):
#         print("Creating instance")
#         x= super(MySignal, cls).__new__(cls)
#
#         return x
#
#     #@addSignal(typ=T)
#     class Emitter(QtCore.QObject):
#
#         def __init__(self):
#             super(MySignal.Emitter, self).__init__()
#     def initemit(self):
#         self.__class__.Emitter.signal = Signal(T)
#         self.emitter = self.Emitter()
#     def __init__(self):
#         pass#self.emitter = self.Emitter()
#
#     def emit(self,*args,**kw):
#         self.emitter.signal.emit(*args,**kw)
#
#
# class SignalTypeMeta:
#     def __new__(cls, name, bases, namespace, **kwargs):
#         #res= QtCore.QObject.__new__(NEmitter)
#         cls= type.__new__(cls, name, bases, namespace)
#         cls.emitter=type('Emitter', (QtCore.QObject,), {'signal':Signal(kwargs['typ'])})
#         return cls
#     pass
#

# class NMySignal(metaclass=SignalTypeMeta,typ=T):
#      def emit(self,*args,**kw):
#          self.emitter.signal.emit(*args,**kw)
# #
#      def connect(self,  slot):
#          self.emitter.signal.connect(slot)
    
    
# class NMySignal(Generic[T]):
#     class NEmitter(metaclass=EmitterTypeMeta,typ=T):
#         pass
#         #signal = Signal(X)
#         #def __init__(self):
#             #super(MySignal.NEmitter, self).__init__()
#
#     def __init__(self):
#         self.emitter = self.NEmitter()
#
#     def emit(self,*args,**kw):
#         self.emitter.signal.emit(*args,**kw)
#
#     def connect(self,  slot):
#         self.emitter.signal.connect(slot)

class DataGenerator(HasParamsAndGroups, InputData):
    minMaxChanged=MySignal()
    namesChanged=MyIntSignal()
    #minMaxChanged=MySignal(typ=tuple)()
    #namesChanged = MySignal(typ=int)()
    def __init__(self):
        #DataGenerator.minMaxChanged.initemit()
        self.colswithoutext=[]
        self.tmp_colswithoutext=[]
        self.org_data=None
        self.minValue=None
        self.maxValue=None
        self.cols=None
    def get_data_by_type(self, type= Types.RELTOMAX, compare_with=None):
        arr, df, type, fulldf = self.generate_initial_data(compare_with, type)
        act= ActOnData(arr, df, type, fulldf,compare_with,self)
        act.do()

        return  act.df,act.Marr,act.min_arr,act.type

    def generate_initial_data(self, compare_with, type):
        fromdateNum = matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate) if self.params.todate else float('inf')
        dic = self.get_dict_by_type(type)
        df = pandas.DataFrame.from_dict(dic)
        if (self.params.unite_by_group & ~UniteType.NONE):
            df , colswithoutext = self.unite_groups(df) #in case really unite groups, colswithoutext is correct
        df = df[(df.index >= fromdateNum) * (df.index <= todateNum)]
        compit_arr = None
        if type & Types.COMPARE:
            if not compare_with in df:
                print('to bad, no comp')
                type = type & ~Types.COMPARE

                # ind=first_index_of(compit_arr,np.isnan)
                # df=df.iloc[ind:]
        if not (self.params.unite_by_group & ~(UniteType.ADDTOTAL)):  # in unite, the compare_with is already there.
            # If the  unite is non-trivial, then colswithoutext already returned
            cols,colswithoutext = self.cols_by_selection(df)
            if type & Types.COMPARE:
                fulldf = df[list(cols.union(set([compare_with])))]
            else:
                fulldf = df[list(cols)]
        else: #colswithoutext non-trivial
            fulldf = df
            cols=set(df.columns)

            ##else we need everything...
        arr = np.array(fulldf).transpose()  # will just work with arr
        fulldf = fulldf.drop(
            df.index[(np.all(np.isnan(arr), axis=0))])  # to check drop dates in which all stocks are none.
        df = fulldf[list(cols - set([compare_with]))]
        arr = np.array(df).transpose()  # will just work with arr

        if len(arr)==0:
            raise NoDataException("arr is empty")

        if type & (Types.COMPARE | Types.PRECENTAGE | Types.DIFF):
            fullarr= np.array(fulldf).transpose()
            df = df.iloc[get_first_where_all_are_good(fullarr, type & Types.PRECENTAGE):]
            arr = np.array(df).transpose()

        self.tmp_colswithoutext=  set(colswithoutext).intersection(df.columns)
        self.org_data=fulldf.copy()

        return arr, df, type, fulldf

    def get_dict_by_type(self, div):
        if div & Types.PROFIT:
            dic = self.unrel_profit
            self.params.use_ext = False
        elif div & Types.RELPROFIT:
            dic = self.rel_profit_by_stock
            self.params.use_ext = False
        elif div & Types.PRICE:
            dic = self.alldates
        elif div & Types.TOTPROFIT:
            dic = self.tot_profit_by_stock
        elif div & Types.VALUE:
            dic = self.value
            self.params.use_ext = False
        elif div & Types.THEORTICAL_PROFIT:
            dic = self.tot_profit_by_stock
        else:
            dic = self.alldates
        return dic

    def unite_groups(self, df):

        items = [(g, self.Groups[g]) for g in self.params.groups]
        if (self.params.unite_by_group & ~UniteType.ADDTOTAL): #Non trivial unite. groups
            if len(self.params.ext)>0 and self.params.use_ext:
                ndf= df.loc[:, list(self.params.ext)]
            else:
                ndf=pandas.DataFrame(index=df.index,)
        else: #just add total
            ndf=df


        if self.params.unite_by_group & UniteType.ADDTOTAL:
            items += [('All', list(df.columns))]




        for gr, stocks in items:
            try:
                arr = np.array(df[stocks]).transpose()
            except KeyError:
                print('none of the values here')
                continue
            incomplete= (arr.shape[0]!=len(stocks))
            if incomplete:
                print('incomplete unite')
            #curdat = {st:{f: dic[stocks[st]][self._curflist[f]]}  for st in range(len(stocks)) for f in range(len(self._curflist))} #should have default args
            #A=numpy.array(curdat)
            # = n[~numpy.isnan(n)]

            if self.params.unite_by_group & UniteType.SUM or gr=='All':
                ndf.loc[:, gr] = numpy.sum(arr, axis=0)
                #df.append({'gr':  },ignore_index=True)
            elif self.params.unite_by_group & UniteType.AVG:
                ndf.loc[:, gr] = numpy.nanmean(arr, axis=0 )

        return ndf ,[x[0] for x in items]



    def cols_by_selection(self,  data):
        cols = set([x for x in data])
        selected=self.required_syms(True).union(set(['All'])) #always include All if there is all..
        withoutext=self.required_syms(False).union(set(['All']))
        return cols.intersection(selected),cols.intersection(withoutext)

    def generate_data(self):
        #self.params.use_ext=True #Will be changed by func

        df, Marr ,min_arr, type= self.get_data_by_type(self.params.type, self.params.compare_with)

        self.cols = df.columns


        self.update_ranges(df)

        mainlst= sorted(list(zip(Marr, min_arr, self.colswithoutext)), key=lambda x: x[0], reverse=True)


        sordlist = [stock for (max,min, stock) in mainlst  if
                    (min >= self.params.valuerange[0] and max<= self.params.valuerange[1]) or (self.params.ignore_minmax) ]
        restofcols= set(df.columns) - set(self.colswithoutext)
        if not self.params.ignore_minmax:
            rang =  (self.params.numrange[0],  self.params.numrange[1])
        else:
            rang=(None,None)

        df = df[sorted(list(restofcols))+ sordlist[rang[0]:rang[1]]  ]  # rearrange columns by max, and include rest
        df.rename({y: matplotlib.dates.num2date(y) for y in df.index},axis=0,inplace=1)

        return df,type

    def update_ranges(self, df):
        if self.tmp_colswithoutext!=self.colswithoutext:
            self.colswithoutext=self.tmp_colswithoutext
            self.namesChanged.emit(len(self.colswithoutext))

        M = max(list(df.max(numeric_only=True)))
        m = min(list(df.min(numeric_only=True)))
        diff = self.maxValue != M or self.minValue != m
        self.minValue, self.maxValue = m, M
        if diff:
            self.minMaxChanged.emit((self.minValue, self.maxValue))