import collections
import copy
import inspect
import locale
import pickle
import statistics
import sys

import config
from common import Types, UseCache, UniteType,config
from common import USEWX,USEWEB,USEQT
from graphgenerator import GraphGenerator
from refvar import *
#import mplfinance


from ib.ibtest import main,get_symbol_history



locale.setlocale(locale.LC_ALL, 'C')


if __name__=='__main__':
    if USEWX:

        import wx
        app = wx.App()
        frame = wx.Frame(parent=None, title='Hello World')
        frame.Show()
        #app.MainLoop()
        #locale = wx.Locale(wx.LANGUAGE_ENGLISH_US)


#
import matplotlib
import pandas as pd
from collections import defaultdict
import math
from dateutil import parser
import datetime

import numpy
#interactive(True)
import matplotlib.pyplot as plt

from orederedset import OrderedSet



#matplotlib.use('WebAgg')
#plt.rcParams['figure.constrained_layout.use'] = True

MIN=4000
MAXCOLS=30
MINCOLFORCOLUMS=80

#pd.DataFrame()
class MyOrderedSet(OrderedSet):
    def intersection(self,set):
        l=OrderedSet()
        for k in self:
            if k in set:
                l.add(k)
        return l


from orederedset import  *

linesandfig=[]

PROFITPRICE= Types.PROFIT | Types.ABS

class ParameterError(Exception):
    pass

class InputProcessor:
    def __init__(self,filename):
        self._symbols=set()
        self._fromdate=None
        self._fn=filename
        self._todate=None

    def populate_buydic(self):

        x=pd.read_csv(self._fn)
        self._buydic = {}
        self._symbols=set()
        for t in zip(x['Portfolio'], x['Symbol'], x['Quantity'], x['Cost Per Share'], x['Type'], x['Date'],
                     x['TimeOfDay']):
            #if not math.isnan(t[1]):
            #    self._symbols.add(t[1])

            if (self.portfolio and  t[0] != self.portfolio) or math.isnan(t[2]):
                continue
            dt = str(t[-2]) + ' ' + str(t[-1])
            # print(dt)
            try:
                if math.isnan(t[-2]):
                    print(t)
            except:
                pass
            arr = dt.split(' ')

            dt = parser.parse(' '.join([arr[0], arr[2], arr[1]]))
            while dt in self._buydic:
                dt+=datetime.timedelta(milliseconds=10)

            #aa=matplotlib.dates.date2num(dt)
            self._buydic[dt] = (t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1]) #Qty,cost,sym
            self._symbols.add(t[1])

    def process_ib(self):

        def update_curholding():
            stock = cur_action[1][2]
            old_cost = _cur_avg_cost_bystock[stock]


            old_holding= _cur_holding_bystock[stock]
            if old_holding<0:
                print('warning sell below zero',stock)
            if cur_action[1][0]>0:
                _cur_avg_cost_bystock[stock] = (old_holding * old_cost + cur_action[1][0] * cur_action[1][1]) / (old_holding + cur_action[1][0])
                #self._avg_cost_by_stock[stock][cur_action[0]] = nv
            else:
                _cur_relprofit_bystock[stock] += cur_action[1][0] * (cur_action[1][1]* (-1)  -_cur_avg_cost_bystock[stock])
                #self.rel_profit_by_stock[stock][cur_action[0]] =  _cur_relprofit_bystock[stock]

            _cur_holding_bystock[stock] += cur_action[1][0]

        self._alldates = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._unrel_profit = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._value = defaultdict(lambda: defaultdict(lambda: numpy.NaN)) #how much we hold
        self._avg_cost_by_stock=defaultdict(lambda: defaultdict(lambda: numpy.NaN)) #cost per unit
        self._rel_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  #re
        self._tot_profit_by_stock  = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._holding_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))

        _cur_avg_cost_bystock=defaultdict(lambda: 0)
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock=defaultdict(lambda: 0)


        b= collections.OrderedDict(sorted( self._buydic.items())) #ordered


        cur_action= b.popitem(False)

        if not cur_action:
            return
        if self.fromdate == None:
            self.fromdate=cur_action[0]

        ll = datetime.datetime.now(config.TZINFO) - self.fromdate

        #update_profit = lambda y: y[0]

        query_ib=True
        if self.use_cache!= UseCache.DONT :
            try:
                hist_by_date, self._cache_date = pickle.load(open(config.HIST_F, 'rb'))
                if self._cache_date - datetime.datetime.now() < config.MAXCACHETIMESPAN or self.use_cache== UseCache.FORCEUSE:
                    self._hist_by_date=hist_by_date
                query_ib = False
            except:
                print('failed to use cache')



        if query_ib:
            self._hist_by_date = collections.OrderedDict() #like all dates but by

            for sym in self._symbols:
                hist = get_symbol_history(sym, '%sd' % ll.days, '1d')  # should be rounded
                if hist==None:
                    continue
                for l in hist:
                    if not l['t'] in self._hist_by_date:
                        self._hist_by_date[l['t']]={}
                    self._hist_by_date[l['t']][sym]= (l['c']+l['o'])/2 #should be =l

            pickle.dump( (self._hist_by_date,datetime.datetime.now()), open(config.HIST_F,'wb') )

        tz=datetime.timezone(datetime.timedelta(hours=0),'UTC')
        self.mindate= datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate= datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)
        self._fset=set()
        for tim,dic in sorted(self._hist_by_date.items()):
            tim=datetime.datetime.fromtimestamp(tim/1000,tz)
            while tim>cur_action[0]:
                update_curholding()
                if len(b)==0:
                    cur_action=None
                    break
                cur_action = b.popitem(False)
                if self.todate and tim>self.todate:
                    break

            t=matplotlib.dates.date2num(tim)

            #even if no market data
            for sym in _cur_holding_bystock:
                self._holding_by_stock[sym][t] = _cur_holding_bystock[sym]
                self._rel_profit_by_stock[sym][t]=_cur_relprofit_bystock[sym]

            for sym,v in dic.items():
                self._alldates[sym][t]=v
                self._value[sym][t]=  v* _cur_holding_bystock[sym]
                self._unrel_profit[sym][t]= v * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * _cur_avg_cost_bystock[sym]
                self._tot_profit_by_stock[sym][t] = self._rel_profit_by_stock[sym][t] + self._unrel_profit[sym][t]
            self._fset.add(t)



        #  #sorted(self._alldates[sym].keys()) #last sym hopefully
        # for s in self._alldates.keys():
        #     if len(self._fset)!=self._alldates[s]:
        #         self._alldates.pop(s)

        if cur_action:
            update_curholding()
            print('after, should update rel_prof... ')

    def process(self):
        self.populate_buydic()
        self.process_ib()

    @property
    def todate(self):
        return self._todate

    @todate.setter
    def todate(self, value):
        self._todate=value
        self.adjust_date=1
        pass

    @property
    def fromdate(self):
        return self._fromdate

    @fromdate.setter
    def fromdate(self, value):
        self._fromdate = value
        self.adjust_date = 1
        pass


@refproperty('mincrit')
@refproperty('maxnum')
@refproperty('use_groups')

class CompareEngine(GraphGenerator, InputProcessor):
    Groups = config.GROUPS

    @staticmethod
    def get_options_from_groups(ls):
        s = set()
        for g in ls:
            s = s.union(set(CompareEngine.Groups[g]))
        return list(s)

    def __init__(self,filename):
        super(CompareEngine, self).__init__()
        InputProcessor.__init__(self,filename)
        self._alldates=None
        self._fset=set()
        self._annotation=[]
        self._cache_date=None
        t = inspect.getfullargspec(CompareEngine.gen_graph)  # generate all fields from paramters of gengraph
        [self.__setattr__(a, d) for a, d in zip(t.args[1:], t.defaults)]


    def get_data_by_type(self, mincrit, div= Types.RELTOMAX, compare_with=None):
        fromdateNum=matplotlib.dates.date2num(self.fromdate) if self.fromdate else 0
        todateNum = matplotlib.dates.date2num(self.todate)  if self.todate else float('inf')
        self._curflist = list(filter(lambda x: (x >= fromdateNum and x <= todateNum),sorted(self._fset)))


        if div & Types.PROFIT:
            dic=self._unrel_profit
            self.use_ext = False
        elif div & Types.RELPROFIT:
            dic=self._rel_profit_by_stock
            self.use_ext=False
        elif div & Types.PRICE:
            dic = self._alldates
        elif div & Types.TOTPROFIT:
            dic= self._tot_profit_by_stock
        elif div & Types.VALUE:
            dic=self._value
            self.use_ext = False
        elif div & Types.THEORTICAL_PROFIT:
            dic=self._tot_profit_by_stock
        else:
            dic= self._alldates



        if self.unite_by_group != UniteType.NONE:
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
                    intialHoldComp= (initialHold* intialCost)/self._price[compare_with][loc]
                    intialCostComp=  self._price[compare_with][loc]
                    holdcomp = lambda f :intialHoldComp *  self._holding_by_stock[st][f] / initialHold
                    costcomp = lambda f: intialCostComp * self._avg_cost_by_stock[st][f] / intialCost
                    compit ={f:holdcomp[f]*costcomp[f] for f in self._curflist} #from here , either precentage or diff


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
        items = [(g, CompareEngine.Groups[g]) for g in self.groups]
        if self.unite_by_group & UniteType.ADDTOTAL:
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

            if self.unite_by_group & UniteType.SUM or gr=='All':
                ndic[gr] = dict(zip(flist, numpy.sum(n, axis=0 )))
            elif self.unite_by_group & UniteType.AVG:
                ndic[gr] = dict(zip(flist,numpy.mean(n, axis=0 )))

        return ndic

    def gen_graph(self, groups=None, mincrit=MIN, maxnum=MAXCOLS, type=Types.VALUE, ext=config.EXT.copy(), increase_fig=1, fromdate=None, todate=None, isline=True, starthidden=0, compare_with=None, reprocess=1, just_upd=0, shown_stock=set(), portfolio=config.DEF_PORTFOLIO, use_cache=UseCache.USEIFAVALIABLE, def_fig_size=config.DEF_FIG_SIZE, unite_by_group=UniteType.NONE, show_graph=False
                  , use_groups=True,selected_stocks=False):
        t = inspect.getfullargspec(CompareEngine.gen_graph)
        for a in t.args:
            self.__setattr__(a, locals()[a])
        B = (1, 0.5)
        if reprocess:
            self.process()
        self.dt = self.generate_data()

        try:
            self.gen_actual_graph(B, self.cols, self.dt, increase_fig, isline, starthidden,just_upd,type)
        except TypeError:
            print("failed generating graph ")


    def generate_data(self):
        self.use_ext=True #Will be changed by func
        data = list(self.get_data_by_type(self.mincrit, self.type, self.compare_with))

        data.sort(key=lambda x: x[2])
        if (not (self.unite_by_group & (UniteType.SUM | UniteType.AVG))):
            data = self.adjust_cols_by_selection(data)

        data = data[(-1) * self.maxnum:]
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
            if self.use_groups:
                if self.groups:
                    curse = set()
                    for g in self.groups:
                        curse = curse.union(set(self.Groups[g]))

                    cols = cols.intersection(curse)
            else:
                cols = cols.intersection(set(self.selected_stocks))
        except KeyError:
            raise ParameterError("groups")

        if self.use_ext:
            for sym in self.ext:
                if not sym in cols:
                    m = [(k, x, y) for k, x, y in data if k == sym]
                    if len(m) > 0:  # odata contains it, could be filter out by compar
                        data += m
                        cols.add(sym)
        self.cols=cols
        return data

    # makes the entire graph from the default attributes.
    def update_graph(self,**kwargs):
        reprocess= 1 if  (set(['fromdate','todate']).intersection(set(kwargs.keys())) or not self._alldates) else 0
        if self.selected_stocks and not self.use_groups:
            if not ( set(self.selected_stocks)<=set(self._alldates.keys())):
                print('should add stocks')
                reprocess=1

        for k in kwargs:
            if k in self.__dict__:
                self.__dict__[k]=kwargs[k]
        t = inspect.getfullargspec(CompareEngine.gen_graph)
        dd={x:self.__getattribute__(x) for x in t.args if x not in ['self','increase_fig','reprocess','just_upd' ] }
        self.gen_graph( increase_fig = 0,reprocess=reprocess,just_upd=1,**dd )






def initialize_graph_and_ib():
    if USEWX:
        matplotlib.use('WxAgg')
    elif USEWEB:
        matplotlib.use('WebAgg')
    elif USEQT:
        matplotlib.use('QtAgg')
    else:
        matplotlib.use('TKAgg')
    main(False)
    gg = CompareEngine(config.FN)


    return  gg

#fig.canvas.draw()
if __name__=='__main__':
    gg=initialize_graph_and_ib()
    #interactive(True)
    #gg.gen_graph()

    x= {'groups': ['FANG'],
 'type': Types(641),
 'compare_with': 'QQQ',
 'mincrit': 0,
 'maxnum': 0}

    gg.gen_graph(**x)
    #gg.gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ', mincrit=-100000, maxnum=4000, groups=["FANG"],  starthidden=0)
    #gg.gen_graph(type=Types.VALUE, isline=True,groups=['broadec'],mincrit=-100000,maxnum=4000,use_cache=UseCache.FORCEUSE)
    #gg.update_graph(type=Types.PROFIT)
    #plt.show(block=True)
    a=1
    #getch()






