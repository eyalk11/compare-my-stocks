import collections
import math
import pickle
from collections import defaultdict
#from datetime import datetime
import datetime
import matplotlib
import numpy
import pandas as pd
from dateutil import parser

import config
from common import UseCache
from ib.ibtest import get_symbol_history


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

            if (self.params.portfolio and  t[0] != self.params.portfolio) or math.isnan(t[2]):
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
        if self.params.fromdate == None:
            self.params.fromdate=cur_action[0]

        ll = datetime.datetime.now(config.TZINFO) - self.params.fromdate

        #update_profit = lambda y: y[0]

        query_ib=True
        if self.params.use_cache!= UseCache.DONT :
            try:
                hist_by_date, self._cache_date = pickle.load(open(config.HIST_F, 'rb'))
                if self._cache_date - datetime.datetime.now() < config.MAXCACHETIMESPAN or self.params.use_cache== UseCache.FORCEUSE:
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
                if self.params.todate and tim>self.params.todate:
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