import copy
import math
from collections import defaultdict

import matplotlib
import numpy
import numpy as np
import pandas
import pandas as pd

import config
from common import Types, UniteType
from graphgenerator import GraphGenerator
from inputprocessor import InputProcessor
from orederedset import MyOrderedSet
from parameters import Parameters, ParameterError, HasParams


def params():
    doc = "The params property."

    def fget(self):
        return self._params

    def fset(self, value):
        self._params = value

    return locals()

def first_index_of(ls,fun=None):
    #ls=list(ls)
    if fun==None:
        fun=lambda x:x
    lst=[x for x in range(len(ls)) if fun(ls[x])]
    if lst:
        return lst[0]
    else:
        return -1

class CompareEngine(GraphGenerator, InputProcessor,HasParams):
    Groups = config.GROUPS

    @staticmethod
    def get_options_from_groups(ls):
        s = set()
        for g in ls:
            s = s.union(set(CompareEngine.Groups[g]))
        return list(s)



    params = property(**params())

    def __init__(self,filename):
        super(CompareEngine, self).__init__()
        InputProcessor.__init__(self, filename)
        self._alldates=None
        self._fset=set()
        self._annotation=[]
        self._cache_date=None
        self.params=None

        #t = inspect.getfullargspec(CompareEngine.gen_graph)  # generate all fields from paramters of gengraph
        #[self.__setattr__(a, d) for a, d in zip(t.args[1:], t.defaults)]
    @staticmethod
    def get_first_where_all_are_good(arr,add=None):
        getnan = np.any(np.isnan(arr), axis=0)
        return (list(getnan).index(False))

    def get_data_by_type(self, div= Types.RELTOMAX, compare_with=None):
        fromdateNum=matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate)  if self.params.todate else float('inf')
        curflist = list(filter(lambda x: (x >= fromdateNum and x <= todateNum), sorted(self._fset)))

        dic = self.get_dict_by_type(div)
        df = pandas.DataFrame.from_dict(dic)
        if (self.params.unite_by_group & ~UniteType.NONE):
            df  = self.unite_groups(df)


        df=df[(df.index >=fromdateNum) * (df.index <=todateNum)]

        compit_arr=None
        if div & Types.COMPARE:
            if not compare_with in df:
                print('to bad, no comp')
                div=div& ~Types.COMPARE

                #ind=first_index_of(compit_arr,np.isnan)
                #df=df.iloc[ind:]



        if not (self.params.unite_by_group & ~(UniteType.ADDTOTAL)): #in unite, the compare_with is already there
            cols = self.cols_by_selection(df,div)
            if div & Types.COMPARE:
                fulldf = df[list(cols.union(set([compare_with])))]
            else:
                fulldf=df
            ##else we need everything...


        arr = np.array(fulldf).transpose()  # will just work with arr

        fulldf=fulldf.drop(df.index[(np.all(np.isnan(arr),axis=0))]) # to check drop dates in which all stocks are none.

        df = fulldf[list(cols - set([compare_with]))]
        arr = np.array(df).transpose()  # will just work with arr

        if len(arr)==0:
            print('no data')
            return None,None

        if div & (Types.COMPARE |Types.PRECENTAGE | Types.DIFF):
            fullarr= np.array(fulldf).transpose()
            df = df.iloc[self.get_first_where_all_are_good(fullarr):]
            arr = np.array(df).transpose()

        self.org_data=fulldf.copy()


        if div & (Types.COMPARE | Types.THEORTICAL_PROFIT)==(Types.COMPARE | Types.THEORTICAL_PROFIT):
            #df = df[[c for c in df if c != compare_with]]  # remove col
            ign = False
            df = self.calc_theoritical_profit(compare_with, df)

        initialarr = arr[:, 0]
        transpose_arr = arr.transpose()

        ign=False
        if div & Types.COMPARE:
            compit_arr= np.array(fulldf[compare_with])
            compit_initial = compit_arr[0]  # at f=0
            compit = np.vstack([compit_arr] * len(df.columns))

            transpose_compit = compit.transpose()
            if div& (Types.PRECENTAGE |Types.DIFF) == (Types.PRECENTAGE |Types.DIFF):
                newarr= ((transpose_arr / initialarr - transpose_compit / compit_initial)) * 100
                ign=True

            elif div & Types.PRECENTAGE: #by what factor was it better...
                newarr = ((transpose_arr / initialarr) / (transpose_compit / compit_initial) - 1) * 100
            else:
                newarr= transpose_arr - transpose_compit
            arr=newarr.transpose()
            transpose_arr=newarr

        Marr= np.nanmax(arr, axis=1)
        M = np.vstack([Marr] * len(df.index))

        if div & Types.RELTOMAX:
            refarr = Marr
        elif div & Types.RELTOMIN:
            refarr = np.nanmin(arr, axis=1)

        elif div & Types.RELTOEND:
            refarr=arr[:,-1]
        else: #if div & Types.RELTOSTART:TODO:: the rel things should be another type like unite.. some messy code...
            refarr= initialarr
            
        if not ign:

            if div & Types.PRECENTAGE and not ign:
                newarr= (transpose_arr / refarr - (1 if div & Types.RELTOSTART | Types.RELTOMIN else 0)) * 100

            elif div & Types.DIFF:
                newarr= transpose_arr - refarr
            else: #if div & Types.ABS == Types.ABS:
                newarr = transpose_arr
        else:
            newarr=arr.transpose()

            #we want to transpose the array anyway to get it fit to df...
        df.loc[:, df.columns] = newarr


        return  df,Marr

    def get_dict_by_type(self, div):
        if div & Types.PROFIT:
            dic = self._unrel_profit
            self.params.use_ext = False
        elif div & Types.RELPROFIT:
            dic = self._rel_profit_by_stock
            self.params.use_ext = False
        elif div & Types.PRICE:
            dic = self._alldates
        elif div & Types.TOTPROFIT:
            dic = self._tot_profit_by_stock
        elif div & Types.VALUE:
            dic = self._value
            self.params.use_ext = False
        elif div & Types.THEORTICAL_PROFIT:
            dic = self._tot_profit_by_stock
        else:
            dic = self._alldates
        return dic

    def calc_theoritical_profit(self, compare_with, df):
        firstnotNan = lambda x: next((l for l in x.values() if not math.isnan(l)))
        firstKeynotNan = lambda x: next((k for k,l in x.items() if not math.isnan(l)))
        holdDF= self._holding_by_stockDF[[x for x in df] + [compare_with]]
        holdArr= np.array(holdDF).transpose()
        ind= self.get_first_where_all_are_good(holdArr)

        holdArr= holdArr.iloc[ind:] #we assume avg cost is valid if hold is
        minkey = firstKeynotNan(self._alldates[compare_with])
        holdArr=holdArr[(holdArr.index >= minkey) ]
        df = df[(df.index >= max(minkey,holdArr.index[0]) ) ]

        for st in df: #if we query on the df. we must be after hold and that is enough...
            # if we hold the same value as we hold for QQQ what is the difference
            initialHold = firstnotNan(self._holding_by_stock[st])
            intialCost = firstnotNan(self._avg_cost_by_stock[st])
            loc = firstKeynotNan(self._holding_by_stock[st])
            intialHoldComp = (initialHold * intialCost) / self._alldates[compare_with][loc]
            intialCostComp = self._alldates[compare_with][loc]
            holdcomp = lambda f: intialHoldComp * self._holding_by_stock[st][f] / initialHold
            costcomp = lambda f: intialCostComp * self._avg_cost_by_stock[st][f] / intialCost

            yield [holdcomp(f) * costcomp(f) for f in self._curflist]
                # compit_arr ={f:} #from here , either precentage or diff

    def unite_groups(self, df):

        items = [(g, CompareEngine.Groups[g]) for g in self.params.groups]
        if (self.params.unite_by_group & ~UniteType.ADDTOTAL):
            ndf=pandas.DataFrame(index=df.index)

        else:
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

        return ndf

    def gen_graph(self, params: Parameters, just_upd=0, reprocess=1):
        if just_upd and self.params:
             self.params.update_from(params)
        else:
            self.params=params

        self.params._baseclass=self

        if self.params.selected_stocks and not self.params.use_groups:
            if not ( set(self.params.selected_stocks)<=set(self._symbols_wanted)):
                print('should add stocks')
                reprocess=1

        B = (1, 0.5)
        if reprocess:
            self.process()
        self.dt = self.generate_data()
        if self.dt is None:
            return
        self.cols = list(self.dt)

        try:
            self.gen_actual_graph(B, self.cols, self.dt,  self.params.isline, self.params.starthidden,just_upd,self.params.type)
        except TypeError as e:
            e=e
            print("failed generating graph ")


    def generate_data(self):
        #self.params.use_ext=True #Will be changed by func
        try:
            df, Marr= self.get_data_by_type(self.params.type, self.params.compare_with)

            sordlist = [stock for (max, stock) in sorted(list(zip(Marr, df)), key=lambda x: x[0], reverse=True) if
                        max >= self.params.mincrit]
            df = df[sordlist[:self.params.maxnum]]  # rearrange columns by max
            df.rename({y: matplotlib.dates.num2date(y) for y in df.index},axis=0,inplace=1)
        except Exception as e :
            import traceback
            traceback.print_exc()
            e=e
            print('exception in generating data')
            return None
        return df
        





    def cols_by_selection(self,  data,div):
        cols = set([x for x in data])
        selected=set(['All']) #always include All if there is all..


        if self.params.use_ext:
            selected.update(set(self.params.ext))
        try:
            if self.params.use_groups:
                if self.params.groups:

                    for g in self.params.groups:
                        selected.update((set(self.Groups[g])))


            else:
                selected.update(set(self.params.selected_stocks))
        except KeyError:
            raise ParameterError("groups")



        return cols.intersection(selected)

    # makes the entire graph from the default attributes.
    def update_graph(self, params: Parameters = Parameters()):
        reprocess= 1 if  (not self._alldates) else 0

        params.increase_fig=False
        #t = inspect.getfullargspec(CompareEngine.gen_graph)
        #dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph(params,just_upd=1,reprocess=reprocess )
