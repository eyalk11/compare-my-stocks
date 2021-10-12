import copy
import math
from collections import defaultdict

import matplotlib
import numpy
import pandas as pd

import config
from common import Types, UniteType
from graphgenerator import GraphGenerator
from inputprocessor import InputProcessor
from orederedset import MyOrderedSet
from parameters import Parameters,ParameterError


class CompareEngine(GraphGenerator, InputProcessor):
    Groups = config.GROUPS

    @staticmethod
    def get_options_from_groups(ls):
        s = set()
        for g in ls:
            s = s.union(set(CompareEngine.Groups[g]))
        return list(s)

    def params():
        doc = "The params property."
        def fget(self):
            return self._params
        def fset(self, value):
            self._params = value
        return locals()

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


    def get_data_by_type(self, mincrit, div= Types.RELTOMAX, compare_with=None):
        fromdateNum=matplotlib.dates.date2num(self.params.fromdate) if self.params.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.params.todate)  if self.params.todate else float('inf')
        self._curflist = list(filter(lambda x: (x >= fromdateNum and x <= todateNum),sorted(self._fset)))


        if div & Types.PROFIT:
            dic=self._unrel_profit
            self.params.use_ext = False
        elif div & Types.RELPROFIT:
            dic=self._rel_profit_by_stock
            self.params.use_ext=False
        elif div & Types.PRICE:
            dic = self._alldates
        elif div & Types.TOTPROFIT:
            dic= self._tot_profit_by_stock
        elif div & Types.VALUE:
            dic=self._value
            self.params.use_ext = False
        elif div & Types.THEORTICAL_PROFIT:
            dic=self._tot_profit_by_stock
        else:
            dic= self._alldates



        if self.params.unite_by_group != UniteType.NONE:
            dic = self.unite_groups(copy.deepcopy(dic), self._curflist)

        firstnotNan = lambda x: next((l for l in x.values() if not math.isnan(l)))
        firstKeynotNan = lambda x: next((k for k,l in x.items() if not math.isnan(l)))

        if div & Types.COMPARE:
            compit = dic[compare_with]

        for st, v in dic.items():
            v= defaultdict(lambda: numpy.NaN,  dict(filter(lambda x: x[0] in self._curflist,  v.items())))

            if div& Types.COMPARE and st==compare_with:
                continue

            ign = False
            if div & Types.COMPARE:
                if div & Types.THEORTICAL_PROFIT:  # if we hold the same value as we hold for QQQ what is the difference
                    initialHold = firstnotNan(self._holding_by_stock[st])
                    intialCost=  firstnotNan(self._avg_cost_by_stock[st])
                    loc=firstKeynotNan(self._holding_by_stock[st])
                    intialHoldComp= (initialHold* intialCost)/self._alldates[compare_with][loc]
                    intialCostComp=  self._alldates[compare_with][loc]
                    holdcomp = lambda f :intialHoldComp *  self._holding_by_stock[st][f] / initialHold
                    costcomp = lambda f: intialCostComp * self._avg_cost_by_stock[st][f] / intialCost
                    compit ={f:holdcomp(f)*costcomp(f) for f in self._curflist} #from here , either precentage or diff


                if div& Types.PRECENTAGE:
                    fr=firstnotNan(v)
                    frcom=firstnotNan(compit)
                    #zfactor= v[]
                    v = {f : 100*((v[f]/fr) - compit[f]/frcom) for f in self._curflist}
                    ign=True
                #el
                else:
                    v= {f: v[f]- compit[f] for f in self._curflist}

            maxon=[l for l in v.values() if not math.isnan(l)]

            if len(maxon)==0:
                return
            M = max(maxon)

            if div & Types.RELTOMAX:
                values = [(v[f] / M) * 100 for f in self._curflist]
            elif div & Types.ABS:
                values = [v[f] for f in self._curflist]
            elif div & Types.PRECENTAGE and not ign:
                t=firstnotNan(v)
                values = [(v[f] / t - 1) * 100 for f in self._curflist]
                #t= self._curflist[0]
                #values= [(v[f]/v[t]-1) * 100 for f in self._curflist]
            elif div & Types.DIFF:
                t= self._curflist[0]
                values= [(v[f]-v[t]) for f in self._curflist]
            else:
                values = [v[f] for f in self._curflist] #ABS is the default

            if M > mincrit:
                yield st, values, M
            else:
                pass #print('ignoring ', st)

    def unite_groups(self, dic, flist):
        ndic = {}
        items = [(g, CompareEngine.Groups[g]) for g in self.params.groups]
        if self.params.unite_by_group & UniteType.ADDTOTAL:
            items += [('All', list(dic.keys()))]
            ndic = dic #start from the same dic


        for gr, stocks in items:
            n = numpy.empty([len(stocks), len(self._curflist)])
            for st in range(len(stocks)):
                for f in range(len(self._curflist)):
                    n[st][f]=dic[stocks[st]][self._curflist[f]]

            #curdat = {st:{f: dic[stocks[st]][self._curflist[f]]}  for st in range(len(stocks)) for f in range(len(self._curflist))} #should have default args
            #A=numpy.array(curdat)
            # = n[~numpy.isnan(n)]

            if self.params.unite_by_group & UniteType.SUM or gr=='All':
                ndic[gr] = dict(zip(flist, numpy.sum(n, axis=0 )))
            elif self.params.unite_by_group & UniteType.AVG:
                ndic[gr] = dict(zip(flist,numpy.mean(n, axis=0 )))

        return ndic

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

        try:
            self.gen_actual_graph(B, self.cols, self.dt,  self.params.isline, self.params.starthidden,just_upd,self.params.type)
        except TypeError as e:
            e=e
            print("failed generating graph ")


    def generate_data(self):
        #self.params.use_ext=True #Will be changed by func
        data = list(self.get_data_by_type(self.params.mincrit, self.params.type, self.params.compare_with))

        data.sort(key=lambda x: x[2])
        if (not (self.params.unite_by_group & (UniteType.SUM | UniteType.AVG))):
            data = self.adjust_cols_by_selection(data)

        data = data[(-1) * self.params.maxnum:]
        self.data = self.filter_dates(data)

        dt = pd.DataFrame(self.data, columns=self.cols, index=[matplotlib.dates.num2date(y) for y in self._curflist])
        return  dt

    def filter_dates(self, data):
        useful = set()
        data = {x: y for (x, y, z) in data}
        for i in self.cols:
            for j in range(len(data[i])):
                if not math.isnan(data[i][j]):
                    useful.add(j)
        indexfilt = lambda y: filter(lambda m: m != None, [y[k] if k in useful else None for k in range(len(y))])
        self._curflist = indexfilt(self._curflist)
        data = {x: indexfilt(y) for (x, y) in data.items()}
        return data

    def adjust_cols_by_selection(self,  data):
        ll = [x[0] for x in data]
        cols = MyOrderedSet(ll)
        try:
            if self.params.use_groups:
                if self.params.groups:
                    curse = set()
                    for g in self.params.groups:
                        curse = curse.union(set(self.Groups[g]))

                    cols = cols.intersection(curse)
            else:
                cols = cols.intersection(set(self.params.selected_stocks))
        except KeyError:
            raise ParameterError("groups")

        if self.params.use_ext:
            for sym in self.params.ext:
                if not sym in cols:
                    m = [(k, x, y) for k, x, y in data if k == sym]
                    if len(m) > 0:  # odata contains it, could be filter out by compar
                        data += m
                        cols.add(sym)
        self.cols=cols
        return data

    # makes the entire graph from the default attributes.
    def update_graph(self, params: Parameters = Parameters()):
        reprocess= 1 if  (not self._alldates) else 0

        params.increase_fig=False
        #t = inspect.getfullargspec(CompareEngine.gen_graph)
        #dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph(params,just_upd=1,reprocess=reprocess )
