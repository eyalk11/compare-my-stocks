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
from common.common import UseCache, InputSourceType, addAttrs, dictfilt, ifnn, ifnn

from input.inputsource import InputSource, IBSource, InvestPySource
from engine.symbolsinterface import SymbolsInterface


class TransactionHandler(SymbolsInterface):
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

        return [config.TRANSLATEDIC.get(s,s) for s in  self._buysymbols] #get_options_from_groups(self.Groups)

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
        self.symbol_info = {}

        if config.INPUTSOURCE == InputSourceType.IB:
            self._inputsource: InputSource = IBSource()
        else:
            self._inputsource: InputSource = InvestPySource()

        self.init_input()
        self._initial_process_done=False

        self.dicts_names = ['alldates', 'unrel_profit', 'value', 'avg_cost_by_stock','rel_profit_by_stock', 'tot_profit_by_stock', 'holding_by_stock']
        self._relevant_currencies_rates={}



    def resolve_currency(self, sym, l, hist, fromdate, enddate):

        if 'Currency' in hist:
            currency = hist['Currency'][0]
        else:
            print('no currency ')
            currency = 'unk'

        if currency == 'unk':
            print('resolving borsa')
            currency = config.STOCK_CURRENCY.get(sym, 'unk')
        if currency == 'unk':
            currency = config.EXCHANGE_CURRENCY.get(l.get('exchange', 'unk'), 'unk')
        if currency == 'unk':
            print(f'giving up on {sym}')

        if currency != config.BASECUR and currency != 'unk':
            print('adjusted %s %s ' % (sym, currency))
            pair = (config.BASECUR, currency)
            currency_df = self.currency_hist.get(currency,
                                                 self._inputsource.get_currency_history(pair, fromdate, enddate))

            if currency not in self.currency_hist:
                self.currency_hist[currency] = currency_df
            inc=['Open', 'High', 'Low', 'Close']
            currency_df=currency_df[inc]
            hh= hist[inc].mul(currency_df, fill_value=numpy.NaN)
            if len(set(hist.index)-set(currency_df.index))>0:
                print( ' missing ', set(hist.index)-(set(currency_df.index)))
            #from scipy.interpolate import interp1d
            #missing = hh.isna().any(axis=1)
            #if len(missing)>0:
            #    for ij in inc:
            #        f = interp1d(currency_df.index, currency_df[ij])
            #        hh[missing]['Open'].mul(f(hh[missing].index))
            return hh ,currency
        else:
            return None , currency

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
            self.filter_input(partial_symbols_update)

        _cur_avg_cost_bystock = defaultdict(lambda: 0)
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock = defaultdict(lambda: 0)
        _cur_stock_price = defaultdict(lambda: (numpy.NaN,numpy.NaN))

        b = collections.OrderedDict(sorted(self._buydic.items()))  # ordered

        cur_action = b.popitem(False)





        #if not cur_action:
        #    return
        if self.params.transactions_fromdate == None:
            if not cur_action:
                print('where to start?')
                return
            self.params.transactions_fromdate = cur_action[0] #start from first buy

        # update_profit = lambda y: y[0]

        query_source = True
        if self.params.use_cache != UseCache.DONT and not partial_symbols_update:
            try:
                hist_by_date, self.symbol_info, self._cache_date = pickle.load(open(config.HIST_F, 'rb'))
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

        self.currency_hist= {}
        if query_source:
            if not partial_symbols_update:
                self._usable_symbols = set()
                self._hist_by_date = collections.OrderedDict()  # like all dates but by

            for sym in list(self._symbols_wanted if not partial_symbols_update else partial_symbols_update):
                todate = self.params.transactions_todate if self.params.transactions_todate is not None else datetime.datetime.now()

                todate= localize_me(todate)
                transactions_fromdate=localize_me(self.params.transactions_fromdate)
                numdays = (todate - transactions_fromdate).days
                sym_corrected = config.TRANSLATEDIC.get(sym,sym)

                l, hist = self._inputsource.get_symbol_history(sym_corrected, self.params.transactions_fromdate, todate,iscrypto = sym_corrected in config.CRYPTO )  # should be rounded
                self.symbol_info[sym]=l
                if hist is None:
                    print('bad %s' % sym)
                    continue

                adjusted, currency= self.resolve_currency(sym,l,hist,transactions_fromdate,todate)
                if not (self.symbol_info[sym] is None) :
                    self.symbol_info[sym]['currency']=currency
                else:
                    self.symbol_info[sym]={'currency':currency}

                hist = hist.to_dict('index')
                if adjusted is not None:
                    adjusted=adjusted.to_dict('index')
                prec = sum([1 for d in hist.values() if not math.isnan(d['Open'])])
                if prec / numdays < config.MINIMALPRECREQ and numdays > config.MINCHECKREQ:
                    print('not enough days %s %f' % (sym, prec / numdays))
                    continue
                self._usable_symbols.add(sym)

                for date, dic in hist.items():
                    if not date in self._hist_by_date:
                        self._hist_by_date[date] = {}

                    self._hist_by_date[date][sym] = (dic,adjusted.get(date) if adjusted else None )  # should be =l

            pickle.dump((self._hist_by_date, self.symbol_info, datetime.datetime.now()), open(config.HIST_F, 'wb'))

        self._simp_hist_by_date = collections.OrderedDict()
        for date, symdic in self._hist_by_date.items():
            for s, (dica,dicb) in symdic.items():
                if partial_symbols_update and s not in partial_symbols_update:
                    continue
                if not date in self._simp_hist_by_date:
                    self._simp_hist_by_date[date] = {}
                adjust= ifnn(dicb, lambda: (dicb['Close'] + dicb['Open']) / 2, lambda : (dica['Close'] + dica['Open']) / 2)
                self._simp_hist_by_date[date][s] = ( (dica['Close'] + dica['Open']) / 2 , adjust)

        tz = datetime.timezone(datetime.timedelta(hours=0), 'UTC')
        self.mindate = min(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate = max(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)


        hh = pytz.UTC  # timezone('Israel')
        for t, dic in sorted(self._simp_hist_by_date.items()):
            if partial_symbols_update:
                dic= dictfilt(dic, partial_symbols_update)
            t = hh.localize(t, True)
            # t=pytz.normalize(t,cur_action[0].tzinfo())#t.replace(tzinfo=pytz.UTC)
            if self.params.transactions_todate and t > self.params.transactions_todate:
                break
            while cur_action and (t > cur_action[0]):
                update_curholding()
                if len(b) == 0:
                    cur_action = None
                    break
                cur_action = b.popitem(False)

            tim = matplotlib.dates.date2num(t)
            holdopt =  set(_cur_holding_bystock.keys()).intersection(partial_symbols_update) if partial_symbols_update else _cur_holding_bystock.keys()
            for sym in holdopt:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                self._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                self._rel_profit_by_stock[sym][tim] = _cur_relprofit_bystock[sym]
                self._avg_cost_by_stock[sym][tim]=_cur_avg_cost_bystock[sym]

            symopt =  self._usable_symbols.intersection(partial_symbols_update) if partial_symbols_update else self._usable_symbols
            for sym in symopt:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                if sym in dic:
                    v = dic[sym]
                else:
                    v = _cur_stock_price[sym]#actually, should fix for currency. but doesn't matter

                self._alldates[sym][tim] = v[0]
                self._alldates_adjusted[sym][tim]=v[1]
                _cur_stock_price[sym]=v
                v=v[0]
                self._value[sym][tim] = v * _cur_holding_bystock[sym]
                self._unrel_profit[sym][tim] = v * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * \
                                               _cur_avg_cost_bystock[sym]
                self._tot_profit_by_stock[sym][tim] = self._rel_profit_by_stock[sym][tim] + self._unrel_profit[sym][tim]


        if cur_action:
            #run_cur_action(None)
            print('after, should update rel_prof... ')
            # cur_action[0]
        #self.convert_dicts_to_df()
        #relevant_currencies = set([ v['currency'] for v in self.symbol_info.values() if not (v is None) ]) -set(['unk',config.BASECUR])
        #for x in relevant_currencies:
        #    self._relevant_currencies_rates[x]=self._inputsource.get_current_currency((config.BASECUR,x) )
        #self.adjust_for_currency()


    def convert_dicts_to_df(self):
        dataframes = []
        self.dicts = [self._alldates, self._unrel_profit, self._value, self._avg_cost_by_stock,
                      self._rel_profit_by_stock, self._tot_profit_by_stock, self._holding_by_stock,
                      self._alldates_adjusted]
        # no more dicts #we removed alldatesadjusted from dicts..
        for name, dic in zip(self.dicts_names, self.dicts[:-1]):
            df = pd.DataFrame.from_dict(dic)
            # df["Name"]= name
            # dataframes.append(df.set_index(['name',df.index]))

            df.columns = pd.MultiIndex.from_product([[name], list(df.columns)], names=['Name', 'Symbols'])
            dataframes.append(df)
        self.reg_panel = pd.concat(dataframes)  # pd.Panel(data= dict( ),)

    def adjust_for_currency(self):
        TOADJUST=[ 'unrel_profit', 'value', 'avg_cost_by_stock', 'rel_profit_by_stock']

        dic={k:self._relevant_currencies_rates[v['currency']] for k,v in self.symbol_info.items() if ifnn(v,lambda : v['currency']!=config.BASECUR  and (v['currency'] in self._relevant_currencies_rates))}
        #cur = pd.DataFrame(dic, index=self.reg_panel.index,
        #                   )
        multiIndex = pd.MultiIndex.from_product([TOADJUST, list(dic.keys())], names=['Name', 'Symbols'])
        df=pd.DataFrame(index=self.reg_panel.index,columns=multiIndex)
        for x in TOADJUST:
            for k,v in dic.items():
                df.loc[:,(x,k)] = dic[k]
        # dataframes=[]
        # for name in TOADJUST:
        #
        #     # df["Name"]= name
        #     # dataframes.append(df.set_index(['name',df.index]))

        #    df.columns = pd.MultiIndex.from_product([[name], list(df.columns)], names=['Name', 'Symbols'])
        #    dataframes.append(df)

        #df=pd.DataFrame()
        #for k in TOADJUST:
        #    df[k]=cur

        nn=self.reg_panel.copy()
        uu= self.reg_panel[multiIndex].mul(df)
        nn[multiIndex] =uu
        nn=nn




    def init_input(self):
        #todo: make dataframe... but it is 3d...
        self._alldates = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._alldates_adjusted= defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._unrel_profit = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._value = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # how much we hold
        self._avg_cost_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # cost per unit
        self._rel_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # re
        self._tot_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._holding_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))

    def filter_input(self,keys):

        for x in self.dicts:
            for k in keys:
                x.pop(k,'')



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

