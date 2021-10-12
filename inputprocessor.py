import collections
import math
import pickle
from collections import defaultdict
#from datetime import datetime
import datetime
import matplotlib
import numpy
import pandas as pd
import pytz
from dateutil import parser

import config
from common import UseCache, InputSourceType

from abc import ABC, abstractmethod

from parameters import HasParams


class InputSource(ABC):
    @abstractmethod
    def get_symbol_history(self,sym,startdate,enddate):
        pass

class IBSource(InputSource):

    def get_symbol_history(self,sym,startdate,enddate):
        ll = datetime.datetime.now(config.TZINFO) - startdate
        from ib.ibtest import get_symbol_history
        return get_symbol_history(sym, '%sd' % ll.days, '1d')

class InvestPySource(InputSource):

    def get_symbol_history(self, sym, startdate, enddate):
        try:
            import investpy
            l=None
            for l in investpy.search_quotes(text=sym,n_results=10):
                l=l.__dict__
                if l['exchange'].lower() in  config.EXCHANGES:
                    break
            else:
                if l:
                    print(f'not  right exchange {sym}, picking {l}' )
                else:
                    print('nothing for %s ' % sym )
            if 1:
                df = investpy.get_etf_historical_data(etf=l['symbol'], country=l['country'],id=l['id_'],
                                                        from_date=startdate.strftime('%d/%m/%Y'),
                                                        to_date=enddate.strftime('%d/%m/%Y'))
            elif l['pair_type']=='stock':
                df = investpy.get_stock_historical_data(stock=l['symbol'],country= l['country'] ,from_date=startdate.strftime('%d/%m/%Y') ,to_date= enddate.strftime('%d/%m/%Y'))
            else:
                print(l['pair_type'])
                return None
            return { row[0].to_pydatetime():{j:row[1][j] for j in df} for row in df.iterrows()}
        except Exception as  r:
            print(f'{l if l else ""} is  {r}')
            return None


class TransactionHandler(HasParams):
    def __init__(self,filename):
        self._fn=filename

    def populate_buydic(self):

        x=pd.read_csv(self._fn)
        self._buydic = {}
        self._buysymbols=set()
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
            #timezone = pytz.timezone("UTC")
            #dt=timezone.normalize(dt)
            #dt=dt.replace(tzinfo=None)
            self._buydic[dt] = (t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1]) #Qty,cost,sym
            self._buysymbols.add(t[1])



class InputProcessor(TransactionHandler):
    def __init__(self,filename):
        TransactionHandler.__init__(self,filename)
        self._symbols_wanted=set()
        self._fromdate=None
        self._todate=None
        if config.INPUTSOURCE==InputSourceType.IB:
            self._inputsource : InputSource=IBSource()
        else:
            self._inputsource: InputSource = InvestPySource()

    def process_history(self):

        def update_curholding():
            stock = cur_action[1][2]
            old_cost = _cur_avg_cost_bystock[stock]


            old_holding= _cur_holding_bystock[stock]

            if cur_action[1][0]>0:
                _cur_avg_cost_bystock[stock] = (old_holding * old_cost + cur_action[1][0] * cur_action[1][1]) / (old_holding + cur_action[1][0])
                #self._avg_cost_by_stock[stock][cur_action[0]] = nv
            else:
                _cur_relprofit_bystock[stock] += cur_action[1][0] * (cur_action[1][1]* (-1)  -_cur_avg_cost_bystock[stock])
                #self.rel_profit_by_stock[stock][cur_action[0]] =  _cur_relprofit_bystock[stock]

            _cur_holding_bystock[stock] += cur_action[1][0]
            if _cur_holding_bystock[stock] < 0:
                print('warning sell below zero', stock,cur_action[0])

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
        _cur_stock_price = defaultdict(lambda: numpy.NaN)


        b= collections.OrderedDict(sorted( self._buydic.items())) #ordered


        cur_action= b.popitem(False)

        if not cur_action:
            return
        if self.params.fromdate == None:
            self.params.fromdate=cur_action[0]



        #update_profit = lambda y: y[0]

        query_source=True
        if self.params.use_cache!= UseCache.DONT :
            try:
                hist_by_date, self._cache_date = pickle.load(open(config.HIST_F, 'rb'))
                if self._cache_date - datetime.datetime.now() < config.MAXCACHETIMESPAN or self.params.use_cache== UseCache.FORCEUSE:
                    self._hist_by_date=hist_by_date
                self.update_usable_symbols()
                if not self.params.use_cache==UseCache.FORCEUSE:
                    query_source = not (set(self._symbols_wanted) <= set(self._usable_symbols)) #all the buy and required are in there
                else:
                    print('not enough symbols , using anyway')
                    query_source=False
            except Exception as e :
                e=e
                print('failed to use cache')



        if query_source:
            self._usable_symbols=set()
            self._hist_by_date = collections.OrderedDict() #like all dates but by

            for sym in list(self._symbols_wanted):
                if self.params.todate is None:
                    todate = datetime.datetime.now()
                numdays= (todate-self.params.fromdate).days
                hist = self._inputsource.get_symbol_history(sym, self.params.fromdate,todate)  # should be rounded
                if hist==None:
                    print('bad %s' % sym)
                    continue
                prec= sum([1 for d in hist.values() if not math.isnan(d['Open'])])
                if prec/numdays < config.MINIMALPRECREQ and numdays>config.MINCHECKREQ:
                    print('not enough days %s %f' % (sym,prec/numdays))
                    continue
                self._usable_symbols.add(sym)

                for date,dic in hist.items():
                    if not date in self._hist_by_date:
                        self._hist_by_date[date]={}
                    self._hist_by_date[date][sym] = dic  # should be =l


            pickle.dump( (self._hist_by_date,datetime.datetime.now()), open(config.HIST_F,'wb') )


        self._simp_hist_by_date= collections.OrderedDict()
        for date,symdic in self._hist_by_date.items():
            for s,dic in symdic.items():
                if not date in self._simp_hist_by_date:
                    self._simp_hist_by_date[date]={}
                self._simp_hist_by_date[date][s] = (dic['Close'] + dic['Open']) / 2


        tz=datetime.timezone(datetime.timedelta(hours=0),'UTC')
        self.mindate= min(self._hist_by_date.keys())#datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate= max(self._hist_by_date.keys())#datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)
        self._fset=set()
        hh = pytz.UTC #timezone('Israel')
        for t,dic in sorted(self._simp_hist_by_date.items()):

            t=hh.localize(t,True)
            #t=pytz.normalize(t,cur_action[0].tzinfo())#t.replace(tzinfo=pytz.UTC)
            if self.params.todate and t > self.params.todate:
                break
            while cur_action and t>cur_action[0]:
                update_curholding()
                if len(b)==0:
                    cur_action=None
                    break
                cur_action = b.popitem(False)

            tim = matplotlib.dates.date2num(t)

            for sym in _cur_holding_bystock:
                self._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                self._rel_profit_by_stock[sym][tim]=_cur_relprofit_bystock[sym]

            for sym in self._usable_symbols:

                if sym in dic:
                    v=dic[sym]
                else:
                    v=_cur_stock_price[sym]


                self._alldates[sym][tim]=v
                self._value[sym][tim]=  v* _cur_holding_bystock[sym]
                self._unrel_profit[sym][tim]= v * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * _cur_avg_cost_bystock[sym]
                self._tot_profit_by_stock[sym][tim] = self._rel_profit_by_stock[sym][tim] + self._unrel_profit[sym][tim]
            self._fset.add(tim)

        if cur_action:
            update_curholding()
            print('after, should update rel_prof... ')

    def update_usable_symbols(self):
        self._usable_symbols = set()
        for t, dic in self._hist_by_date.items():
            self._usable_symbols.update (set(dic.keys()))

    def process(self):
        self.populate_buydic()
        self._symbols_wanted= self._buysymbols.union(set(self.params.selected_stocks)) #there are symbols to check...
        self.process_history()