import collections
import math
import pickle
import time
from collections import defaultdict
# from datetime import datetime
import datetime
import matplotlib
import numpy
import pandas as pd
import pytz
from dateutil import parser

from config import config
from common.common import UseCache, InputSourceType, addAttrs

from input.inputsource import InputSource, IBSource, InvestPySource
from engine.parameters import HasParamsAndGroups


class TransactionHandler(HasParamsAndGroups):
    def __init__(self, filename):
        self._fn = filename

    def try_to_use_cache(self):
        try:
            (self._buydic, self._buysymbols) = pickle.load(open(config.BUYDICTCACHE, 'rb'))
            return 1
        except Exception as e:
            print(e)
            return 0

    def get_portfolio_stocks(self):  # TODO:: to fix
        return self.get_options_from_groups(self.Groups)

    def populate_buydic(self):
        if self.try_to_use_cache():
            return
        try:
            x = pd.read_csv(self._fn)
        except Exception as e:
            print(f'{e} while getting buydic data')
            return
        try:
            self.read_trasaction_table(x)
        except Exception as e:
            print(f'{e} while reading transaction data')
            return

        if config.BUYDICTCACHE:
            try:
                pickle.dump((self._buydic, self._buysymbols), open(config.BUYDICTCACHE, 'wb'))
                print('dumpted')
            except Exception as e:
                print(e)

    def read_trasaction_table(self, x):
        self._buydic = {}
        self._buysymbols = set()
        x = x.loc[['Portfolio', 'Symbol', 'Quantity', 'Cost Per Share', 'Type', 'Date']]
        #   x['TimeOfDay']
        for t in x.iterrows():  # zip(x['Portfolio'], x['Symbol'], x['Quantity'], x['Cost Per Share'], x['Type'], x['Date'],
            #   x['TimeOfDay']):
            # if not math.isnan(t[1]):
            #    self._symbols.add(t[1])

            if (self.params.portfolio and t[0] != self.params.portfolio) or math.isnan(t[2]):
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
                dt += datetime.timedelta(milliseconds=10)

            # aa=matplotlib.dates.date2num(dt)
            # timezone = pytz.timezone("UTC")
            # dt=timezone.normalize(dt)
            # dt=dt.replace(tzinfo=None)
            self._buydic[dt] = (t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1])  # Qty,cost,sym
            self._buysymbols.add(t[1])


@addAttrs(['tot_profit_by_stock', 'value', 'alldates', 'holding_by_stock', 'rel_profit_by_stock', 'unrel_profit',
           'avg_cost_by_stock'])
class InputProcessor(TransactionHandler):
    def __init__(self, filename):
        TransactionHandler.__init__(self, filename)
        self._symbols_wanted = set()
        self._fromdate = None
        self._todate = None
        if config.INPUTSOURCE == InputSourceType.IB:
            self._inputsource: InputSource = IBSource()
        else:
            self._inputsource: InputSource = InvestPySource()

        self.init_input()
        self._initial_process_done=False

    def process_history(self, partial_symbols_update=set()):

        def update_curholding():
            stock = cur_action[1][2]
            if partial_symbols_update and stock not in partial_symbols_update:
                return
            old_cost = _cur_avg_cost_bystock[stock]

            old_holding = _cur_holding_bystock[stock]

            if cur_action[1][0] > 0:
                _cur_avg_cost_bystock[stock] = (old_holding * old_cost + cur_action[1][0] * cur_action[1][1]) / (
                            old_holding + cur_action[1][0])
                # self._avg_cost_by_stock[stock][cur_action[0]] = nv
            else:
                _cur_relprofit_bystock[stock] += cur_action[1][0] * (
                            cur_action[1][1] * (-1) - _cur_avg_cost_bystock[stock])
                # self.rel_profit_by_stock[stock][cur_action[0]] =  _cur_relprofit_bystock[stock]

            _cur_holding_bystock[stock] += cur_action[1][0]
            if _cur_holding_bystock[stock] < 0:
                print('warning sell below zero', stock, cur_action[0])
        if not partial_symbols_update:
            self.init_input()
        else:
            assert(len([1 for s in partial_symbols_update if s in self._alldates]) == 0)

        _cur_avg_cost_bystock = defaultdict(lambda: 0)
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock = defaultdict(lambda: 0)
        _cur_stock_price = defaultdict(lambda: numpy.NaN)

        b = collections.OrderedDict(sorted(self._buydic.items()))  # ordered

        cur_action = b.popitem(False)





        #if not cur_action:
        #    return
        if self.params.fromdate == None:
            if not cur_action:
                print('where to start?')
                return
            self.params.fromdate = cur_action[0]

        # update_profit = lambda y: y[0]

        query_source = True
        if self.params.use_cache != UseCache.DONT and not partial_symbols_update:
            try:
                hist_by_date, self._cache_date = pickle.load(open(config.HIST_F, 'rb'))
                if self._cache_date - datetime.datetime.now() < config.MAXCACHETIMESPAN or self.params.use_cache == UseCache.FORCEUSE:
                    self._hist_by_date = hist_by_date
                self.update_usable_symbols()
                if not self.params.use_cache == UseCache.FORCEUSE:
                    query_source = not (set(self._symbols_wanted) <= set(
                        self._usable_symbols))  # all the buy and required are in there
                else:
                    print('using cache anyway', not (set(self._symbols_wanted) <= set(self._usable_symbols)))
                    query_source = False
            except Exception as e:
                e = e
                print('failed to use cache')
        localize_me = lambda x :  (pytz.UTC.localize(x, True) if not x.tzinfo else x)
        if query_source:
            if not partial_symbols_update:
                self._usable_symbols = set()
                self._hist_by_date = collections.OrderedDict()  # like all dates but by

            for sym in list(self._symbols_wanted if not partial_symbols_update else partial_symbols_update):
                todate = self.params.todate if self.params.todate is not None else datetime.datetime.now()

                todate= localize_me(todate)
                fromdate=localize_me(self.params.fromdate)
                numdays = (todate - fromdate).days
                sym_corrected = config.TRANSLATEDIC.get(sym,sym)
                if sym_corrected in config.CRYPTO:
                    print('crypto')
                else:
                    l, hist = self._inputsource.get_symbol_history(sym_corrected, self.params.fromdate, todate)  # should be rounded
                self.symbol_info[sym]=l
                if hist == None:
                    print('bad %s' % sym)
                    continue
                prec = sum([1 for d in hist.values() if not math.isnan(d['Open'])])
                if prec / numdays < config.MINIMALPRECREQ and numdays > config.MINCHECKREQ:
                    print('not enough days %s %f' % (sym, prec / numdays))
                    continue
                self._usable_symbols.add(sym)

                for date, dic in hist.items():
                    if not date in self._hist_by_date:
                        self._hist_by_date[date] = {}
                    self._hist_by_date[date][sym] = dic  # should be =l

            pickle.dump((self._hist_by_date, datetime.datetime.now()), open(config.HIST_F, 'wb'))

        self._simp_hist_by_date = collections.OrderedDict()
        for date, symdic in self._hist_by_date.items():
            for s, dic in symdic.items():
                if partial_symbols_update and s not in partial_symbols_update:
                    continue
                if not date in self._simp_hist_by_date:
                    self._simp_hist_by_date[date] = {}
                self._simp_hist_by_date[date][s] = (dic['Close'] + dic['Open']) / 2

        tz = datetime.timezone(datetime.timedelta(hours=0), 'UTC')
        self.mindate = min(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate = max(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)

        dictfilt = lambda x, y: dict([(i, x[i]) for i in x if i in set(y)])

        hh = pytz.UTC  # timezone('Israel')
        for t, dic in sorted(self._simp_hist_by_date.items()):
            if partial_symbols_update:
                dic=dictfilt(dic, partial_symbols_update)
            t = hh.localize(t, True)
            # t=pytz.normalize(t,cur_action[0].tzinfo())#t.replace(tzinfo=pytz.UTC)
            if self.params.todate and t > self.params.todate:
                break
            while cur_action and (t > cur_action[0]):
                update_curholding()
                if len(b) == 0:
                    cur_action = None
                    break
                cur_action = b.popitem(False)

            tim = matplotlib.dates.date2num(t)

            for sym in _cur_holding_bystock:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                self._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                self._rel_profit_by_stock[sym][tim] = _cur_relprofit_bystock[sym]

            for sym in self._usable_symbols:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                if sym in dic:
                    v = dic[sym]
                else:
                    v = _cur_stock_price[sym]

                self._alldates[sym][tim] = v
                self._value[sym][tim] = v * _cur_holding_bystock[sym]
                self._unrel_profit[sym][tim] = v * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * \
                                               _cur_avg_cost_bystock[sym]
                self._tot_profit_by_stock[sym][tim] = self._rel_profit_by_stock[sym][tim] + self._unrel_profit[sym][tim]

        if cur_action:
            #run_cur_action(None)
            print('after, should update rel_prof... ')
            # cur_action[0]



    def init_input(self):
        self._alldates = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._unrel_profit = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._value = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # how much we hold
        self._avg_cost_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # cost per unit
        self._rel_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # re
        self._tot_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._holding_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self.symbol_info={}

    def update_usable_symbols(self):
        self._usable_symbols = set()
        for t, dic in self._hist_by_date.items():
            self._usable_symbols.update(set(dic.keys()))

    def process(self, partial_symbol_update=set()):
        if not self._initial_process_done:
            self.populate_buydic()
            self._initial_process_done = True
        if not partial_symbol_update:
            required=set(self.required_syms(True,True))
            self._symbols_wanted = self._buysymbols.union(required)  # there are symbols to check...
        else:
            self._symbols_wanted.update(partial_symbol_update)
        t = time.process_time()
        self.process_history(partial_symbol_update)
        # do some stuff
        elapsed_time = time.process_time() - t
        print('elasped : %s' % elapsed_time)

