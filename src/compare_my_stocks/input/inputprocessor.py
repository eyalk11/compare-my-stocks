import collections
import math
import pickle
import time
from collections import defaultdict
# from datetime import datetime
import datetime
import matplotlib
import numpy
import pandas
import pandas as pd
import pytz
from PySide6.QtCore import QRecursiveMutex

from config import config
from common.common import UseCache, InputSourceType, addAttrs, dictfilt,  ifnn
from engine.parameters import copyit
from input.earningsproc import EarningProcessor

from input.inputsource import InputSource
from input.investpysource import InvestPySource
from input.ibsource import IBSource
from engine.symbolsinterface import SymbolsInterface
from input.transactionhandler import TransactionHandler
#import input.earningsinp
from input.earningsinp import get_earnings

@addAttrs(['tot_profit_by_stock', 'value', 'alldates', 'holding_by_stock', 'rel_profit_by_stock', 'unrel_profit',
           'avg_cost_by_stock'])
class InputProcessor(TransactionHandler):

    @property
    def reg_panel(self):
        self._proccessing_mutex.lock()
        x= self._reg_panel
        self._proccessing_mutex.unlock()
        return x

    @reg_panel.setter
    def reg_panel(self, value):
        self._reg_panel=value
        pass

    @property
    def adjusted_panel(self):
        self._proccessing_mutex.lock()
        x= self._adjusted_panel
        self._proccessing_mutex.unlock()
        return x

    @adjusted_panel.setter
    def adjusted_panel(self, value):
        self._adjusted_panel=value #we are under lock
        pass

    @property
    def inputsource(self) -> InputSource:
        return self._inputsource

    def __init__(self, filename):
        TransactionHandler.__init__(self, filename)
        self._income, self._revenue, = None,None
        self.cached_used = None
        self._symbols_wanted = set()
        #self.symbol_info = {}
        self._usable_symbols = set()
        self._bad_symbols = set()

        if config.INPUTSOURCE == InputSourceType.IB:
            self._inputsource: InputSource = IBSource()
        else:
            self._inputsource: InputSource = InvestPySource()

        self.init_input()
        self._initial_process_done=False

        self.dicts_names = ['alldates', 'unrel_profit', 'value', 'avg_cost_by_stock','rel_profit_by_stock', 'tot_profit_by_stock', 'holding_by_stock']
        self._relevant_currencies_rates={}
        self.currencyrange=None
        self._proccessing_mutex = QRecursiveMutex()
        self._reg_panel=None
        self._adjusted_panel=None
        self._earningProc=EarningProcessor.generate_or_make()


    def resolve_currency(self, sym, l, hist):
        #very inefficient . but for few..
        if 'Currency' in hist:
            currency = hist['Currency'][0]
        else:
            print('no currency ')
            currency = 'unk'

        if currency == 'unk':
            print(f'resolving currency for {sym}')
            currency = config.STOCK_CURRENCY.get(sym, 'unk')
        if currency == 'unk':
            currency = config.EXCHANGE_CURRENCY.get(l.get('exchange', 'unk'), 'unk')
        if currency == 'unk':
            print(f'unk currency for {sym}')
        return currency

    def adjust_sym_for_currency(self, currency, enddate, fromdate, hist, sym):
        print('adjusted %s %s ' % (sym, currency))
        currency_df = self.get_currency_hist(currency, fromdate, enddate)
        inc = ['Open', 'High', 'Low', 'Close']
        currency_df = currency_df[inc]
        hh = hist[inc].mul(currency_df, fill_value=numpy.NaN)
        if len(set(hist.index) - set(currency_df.index)) > 0:
            print(' missing ', set(hist.index) - (set(currency_df.index)))
        # from scipy.interpolate import interp1d
        # missing = hh.isna().any(axis=1)
        # if len(missing)>0:
        #    for ij in inc:
        #        f = interp1d(currency_df.index, currency_df[ij])
        #        hh[missing]['Open'].mul(f(hh[missing].index))
        return hh

    def get_currency_hist(self, currency, fromdate, enddate):
        pair = (config.BASECUR, currency)
        if self.currencyrange !=None: #if currencyrange is updated, then entire dict should be
            if currency in self.currency_hist:
                if (fromdate!= self.currencyrange[0] or  enddate!= self.currencyrange[1]):
                    self.currency_hist= {}
                    #[currency]=  self._inputsource.get_currency_history(pair, fromdate, enddate)

        currency_df = self.currency_hist.get(currency,
                                             self._inputsource.get_currency_history(pair, fromdate, enddate))
        self.currencyrange = ( fromdate, enddate)

        if currency not in self.currency_hist:
            self.currency_hist[currency] = currency_df
        return currency_df

    def process_history(self, partial_symbols_update=set()):

        if not partial_symbols_update:
            self.init_input()
        else:
            self.filter_input(partial_symbols_update)


        b = collections.OrderedDict(sorted(self._buydic.items()))  # ordered

        cur_action = b.popitem(False) if len(b)!=0 else None


        if self.process_params.transactions_fromdate == None:
            if not cur_action:
                self.process_params.transactions_fromdate = config.DEFAULTFROMDATE
                print('where to start?')
            else:
                self.process_params.transactions_fromdate = cur_action[0] #start from first buy

        if  partial_symbols_update:
            todate=self.process_params.todate
            fromdate=self.process_params.fromdate
        else:
            fromdate=self.process_params.transactions_fromdate
            todate=self.process_params.transactions_todate

        query_source = True
        if self.process_params.use_cache != UseCache.DONT and not partial_symbols_update:
            query_source = self.load_cache()


        self.currency_hist= {}
        if query_source:
            self.get_data_from_source(partial_symbols_update,fromdate,todate)
            self.save_data()
        print('finish initi')
        self.simplify_hist(partial_symbols_update)
        print('finish simpl')
        self.process_hist_internal(b, cur_action, partial_symbols_update)
        print('finish internal')
        try:
            print('entering lock')
            self._proccessing_mutex.lock()
            print('entered')
            self.convert_dicts_to_df_and_add_earnings(partial_symbols_update)
            print('fin convert')
            if config.IGNORE_ADJUST:
                self.adjusted_panel=self.reg_panel.copy()
            else:
                self.adjust_for_currency()
            print('last')
        finally:
            self._proccessing_mutex.unlock()
            print('exit proc lock')

    def load_cache(self):
        query_source = True
        try:
            hist_by_date, self.symbol_info, self._cache_date,self.currency_hist,self.currencyrange = pickle.load(open(config.HIST_F, 'rb'))
            if self._cache_date - datetime.datetime.now() < config.MAXCACHETIMESPAN or self.process_params.use_cache == UseCache.FORCEUSE:
                self._hist_by_date = hist_by_date
            self.update_usable_symbols()
            print(f'cache symbols used {sorted(list(self._usable_symbols))}')
            if not self.process_params.use_cache == UseCache.FORCEUSE:
                query_source = not (set(self._symbols_wanted) <= set(
                    self._usable_symbols))  # all the buy and required are in there
            else:
                print('using cache anyway', not (set(self._symbols_wanted) <= set(self._usable_symbols)))
                query_source = False
                self.cached_used=True
        except Exception as e:
            e = e
            print('failed to use cache')
            self.cached_used = False
        return query_source

    def process_hist_internal(self, b, cur_action, partial_symbols_update):
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
                _cur_relprofit_bystock[stock] += (-1) * ( cur_action[1][0] * (
                            cur_action[1][1]  - _cur_avg_cost_bystock[stock]))

                 #_cur_relprofit_bystock[stock] += cur_action[1][0] * (
                 #                        cur_action[1][1] * (-1) - _cur_avg_cost_bystock[stock])
                # self.rel_profit_by_stock[stock][cur_action[0]] =  _cur_relprofit_bystock[stock]

            _cur_holding_bystock[stock] += cur_action[1][0]
            if _cur_holding_bystock[stock] < 0:
                print('warning sell below zero', stock, cur_action[0])
        self.mindate = min(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate = max(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)
        _cur_avg_cost_bystock = defaultdict(lambda: 0)
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock = defaultdict(lambda: 0)
        _cur_stock_price = defaultdict(lambda: (numpy.NaN, numpy.NaN))
        hh = pytz.UTC  # timezone('Israel')
        if not partial_symbols_update:
            self._fset=set()
        for t, dic in sorted(self._simp_hist_by_date.items()):
            if partial_symbols_update:
                dic = dictfilt(dic, partial_symbols_update)
            t = hh.localize(t, True)
            # t=pytz.normalize(t,cur_action[0].tzinfo())#t.replace(tzinfo=pytz.UTC)
            if self.process_params.transactions_todate and t > self.process_params.transactions_todate:
                break
            while cur_action and (t > cur_action[0]):
                update_curholding()
                if len(b) == 0:
                    cur_action = None
                    break
                cur_action = b.popitem(False)

            tim = matplotlib.dates.date2num(t)
            holdopt = set(_cur_holding_bystock.keys()).intersection(
                partial_symbols_update) if partial_symbols_update else _cur_holding_bystock.keys()
            for sym in holdopt:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                self._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                self._rel_profit_by_stock[sym][tim] = _cur_relprofit_bystock[sym]
                self._avg_cost_by_stock[sym][tim] = _cur_avg_cost_bystock[sym]

            symopt = self._usable_symbols.intersection(
                partial_symbols_update) if partial_symbols_update else self._usable_symbols
            for sym in symopt:
                if partial_symbols_update and not sym in partial_symbols_update:
                    continue
                if sym in dic:
                    v = dic[sym]
                else:
                    v = _cur_stock_price[sym]  # actually, should fix for currency. but doesn't matter

                self._alldates[sym][tim] = v[0]
                self._alldates_adjusted[sym][tim]=v[1]
                _cur_stock_price[sym] = v
                #v = v[0]
                self._value[sym][tim] = v[0] * _cur_holding_bystock[sym]
                self._adjusted_value[sym][tim] = v[1] * _cur_holding_bystock[sym]
                self._unrel_profit[sym][tim] = v[0] * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * \
                                               _cur_avg_cost_bystock[sym]
                self._unrel_profit_adjusted[sym][tim] = v[1] * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * \
                                               _cur_avg_cost_bystock[sym]
                self._tot_profit_by_stock[sym][tim] = self._rel_profit_by_stock[sym][tim] + self._unrel_profit[sym][tim]
            self._fset.add(tim)
        if cur_action:
            # run_cur_action(None)
            print('after, should update rel_prof... ')
            # cur_action[0]

    def simplify_hist(self, partial_symbols_update):
        self._simp_hist_by_date = collections.OrderedDict()
        for date, symdic in self._hist_by_date.items():
            for s, (dica, dicb) in symdic.items():
                if partial_symbols_update and s not in partial_symbols_update:
                    continue
                if not date in self._simp_hist_by_date:
                    self._simp_hist_by_date[date] = {}
                adjust = ifnn(dicb, lambda: (dicb['Close'] + dicb['Open']) / 2,
                              lambda: (dica['Close'] + dica['Open']) / 2)
                self._simp_hist_by_date[date][s] = ((dica['Close'] + dica['Open']) / 2, adjust)

    def get_data_from_source(self, partial_symbols_update,fromdate,todate):
        TOLLERENCE=5 #config

        def get_range_gap(dates,fromdate,todate):

            #yields the gaps in data between dates ..
            dates=sorted(list(dates))
            if len(dates)<2 or dates[-1]<=fromdate:
                yield  fromdate,todate
            reachedfrom=False
            for da,af  in zip( dates[:-1],dates[1:]):
                if da<=fromdate:
                    if da==fromdate:
                        reachedfrom=True
                    continue
                #we are >=fromdate
                if da>fromdate and (da-fromdate).days>TOLLERENCE :
                    if not reachedfrom:
                        yield fromdate,da #days missing befor we reached
                        reachedfrom=True
                if da>=todate:
                    break
                if (af-da).days>TOLLERENCE: #gap
                    yield da,min(af,todate) #we miss all the days inbetween

            if af<todate and (todate-af).days>TOLLERENCE:
                yield af,  todate


        self.symbol_info_tmp={}
        localize_me = lambda x: (pytz.UTC.localize(x, True) if not x.tzinfo else x)
        if not partial_symbols_update:
            self._usable_symbols = set()
            self._bad_symbols = set()
            self._hist_by_date = collections.OrderedDict()  # like all dates but by
        else:
            self._bad_symbols=self._bad_symbols - set(partial_symbols_update) #meaning we don't ignore symbols here , even if before they were bad
        todate = todate if todate is not None else datetime.datetime.now()

        todate = localize_me(todate)

        fromdate = localize_me(fromdate)


        for sym in list(self._symbols_wanted if not partial_symbols_update else partial_symbols_update):


            sym_corrected = config.TRANSLATEDIC.get(sym, sym)
            skipget=False
            ls = get_range_gap(list(self._hist_by_date[sym].keys()),fromdate,todate) if sym in self._hist_by_date else [(fromdate,todate)]
            okdays=0
            requireddays=0
            try:
                for (mindate,maxdate) in  ls:
                    okdays+=self.get_hist_sym(mindate, maxdate, sym, sym_corrected)
                    requireddays+=(maxdate-mindate).days

            except AttributeError:
                print('bad %s' % sym)
                self._bad_symbols.add(sym) #we will not try again. But every run we do try once...
                continue
            if requireddays/okdays<0.5:
                print(f'mostly problematic {sym}')

    def get_hist_sym(self,mindate, maxdate, sym, sym_corrected):
        print(f'getting symbol hist for {sym} ({sym_corrected}) from {mindate} to {maxdate}')
        l, hist = self._inputsource.get_symbol_history(sym_corrected, mindate, maxdate,
                                                       iscrypto=sym_corrected in config.CRYPTO)  # should be rounded
        self.symbol_info_tmp[sym] = l #just for debug I think
        if hist is None:
            raise AttributeError("bad symbol")
        if not (sym in self.symbol_info and ('currency' in self.symbol_info[sym] ) and self.symbol_info[sym]['currency']) :
            currency = self.resolve_currency(sym, l, hist)
            self.symbol_info[sym].update( {'currency': currency})
        else:
            currency= self.symbol_info[sym]['currency']

        if currency != config.BASECUR and currency != 'unk':
            adjusted =  self.adjust_sym_for_currency(currency, maxdate, mindate, hist, sym)
        else:
            adjusted=None

        hist = hist.to_dict('index')
        if adjusted is not None:
            adjusted = adjusted.to_dict('index')
        okdays = sum([1 for d in hist.values() if not math.isnan(d['Open'])])

        self._usable_symbols.add(sym)
        for date, dic in hist.items():
            if not date in self._hist_by_date:
                self._hist_by_date[date] = {}

            self._hist_by_date[date][sym] = (dic, adjusted.get(date) if adjusted else None)  # should be =l
        return okdays
    def save_data(self):
        import shutil
        try:
            shutil.copy(config.HIST_F, config.HIST_F_BACKUP)
        except:
            print('error in backuping hist file')
        try:
            pickle.dump((self._hist_by_date, self.symbol_info, datetime.datetime.now(), self.currency_hist,
                         self.currencyrange), open(config.HIST_F, 'wb'))
        except:
            print("error in dumping hist")


    def convert_dicts_to_df_and_add_earnings(self,partial_symbols_update):
        dataframes = []
        self.dicts = [self._alldates, self._unrel_profit, self._value, self._avg_cost_by_stock,
                      self._rel_profit_by_stock, self._tot_profit_by_stock, self._holding_by_stock,
                      self._alldates_adjusted,self._unrel_profit_adjusted]
        NONADJUSTEDDICTS= len(self.dicts) -2
        # no more dicts #we removed alldatesadjusted from dicts..
        seldict= self.dicts[:NONADJUSTEDDICTS]
        symbols=list(self._symbols_wanted if not partial_symbols_update else partial_symbols_update)
        try:

            #income, revenue, cs =# get_earnings()
            income, revenue, cs = EarningProcessor
            hasearnings=True
            combinedindex = sorted(
                list(set(self._fset).union(set(cs.index)).union(set(income.index)).union(set(revenue.index))))
        except:
            print('earning reading failed')
            import traceback
            traceback.print_exc()
            hasearnings = False
            combinedindex=sorted(list(self._fset))


        for name, dic in zip(self.dicts_names,seldict):
            df = pd.DataFrame(dic, index=combinedindex)
            if name=='alldates':
                df = df.fillna(method='ffill', axis=0)
            #df = pd.DataFrame(dic,index=sorted(list(self._fset)))
            # combined index is needed to adjust for the df, but maybe can do without... pass to return_df
            #df = pd.DataFrame(dic, index=combinedindex)


            # df["Name"]= name
            df.columns = pd.MultiIndex.from_product([[name], list(df.columns)], names=['Name', 'Symbols'])

            dataframes.append(df)

        try:
            if hasearnings:
                dataframes +=  [InputProcessor.return_df(dataframes[0]['alldates'],income,cs,"peratio"), InputProcessor.return_df(dataframes[0]['alldates'],revenue,cs,"pricesells")] #InputProcessor.calculate_earnings(dataframes[0]['alldates'])
            else:
                dataframes += [pandas.DataFrame(), pandas.DataFrame(), pandas.DataFrame()]
        except:
            import traceback
            traceback.print_exc()
            print('earnings calc failed ')

        self._reg_panel = pd.concat(dataframes,axis=1)

    @staticmethod
    def return_df(df, cur,commonstock_df,name):
        cur.sort_index(axis=0, inplace=True)
        cur=cur.reindex(sorted(list(df.index)),method='pad')
        commonstock_df.sort_index(axis=0,inplace=True)
        commonstock_df=commonstock_df.reindex(df.index,method='pad')
        eps= cur.divide(commonstock_df)
        cur= df[cur.columns].divide(eps) #pr ps / eps = price / earnings
        cur.columns = pd.MultiIndex.from_product([[name], list(cur.columns)], names=['Name', 'Symbols'])
        return cur





    def get_relevant_currency(self,x):
        if x not in self._relevant_currencies_rates:
            self._relevant_currencies_rates[x] = self._inputsource.get_current_currency((config.BASECUR, x))
        return  self._relevant_currencies_rates[x]

    def adjust_for_currency(self):

        relevant_currencies = set([v['currency'] for v in self.symbol_info.values() if not (v is None)]) - \
                              set(['unk', config.BASECUR])
        for x in relevant_currencies:
            self._relevant_currencies_rates[x] = self._inputsource.get_current_currency((config.BASECUR, x))
        dic={k:self._relevant_currencies_rates[v['currency']] for k,v in self.symbol_info.items() if ifnn(v,lambda : v['currency']!=config.BASECUR  and (v['currency'] in self._relevant_currencies_rates))}

        self._adjusted_panel=self.get_adjusted_df_for_currency(dic)

    def init_input(self):
        #todo: make dataframe... but it is 3d...
        self._alldates = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._alldates_adjusted= defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._adjusted_value = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._unrel_profit = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._value = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # how much we hold
        self._avg_cost_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # cost per unit
        self._rel_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))  # re
        self._tot_profit_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._holding_by_stock = defaultdict(lambda: defaultdict(lambda: numpy.NaN))
        self._unrel_profit_adjusted = defaultdict(lambda: defaultdict(lambda: numpy.NaN))

    def get_adjusted_df_for_currency(self, dic):
        def return_subpanel(s,dic):
            t=pd.DataFrame.from_dict(dic)
            t.columns=pd.MultiIndex.from_product([[s], list(t.columns)], names=['Name', 'Symbols'])
            return t


        multiIndex = pd.MultiIndex.from_product([InputProcessor.TOADJUST, list(dic.keys())], names=['Name', 'Symbols'])
        df = pd.DataFrame(index=self._reg_panel.index, columns=multiIndex)
        for x in InputProcessor.TOADJUST:
            for k, v in dic.items():
                df.loc[:, (x, k)] = dic[k]

        nn=pd.DataFrame(index=self._reg_panel.index, columns=self._reg_panel.columns)#[ (c,d)  for (c,d) in   self.reg_panel.columns if c!='tot_profit_by_stock']  )
        for x in SymbolsInterface.TOKEEP:
            if x in self._reg_panel:
                nn[x] = self._reg_panel[x].copy() #nn.merge( self.reg_panel[x],on=nn.index, suffixes=None)

        uu = self._reg_panel[multiIndex].mul(df)
        nn[multiIndex] = uu
       # nn['alldates'] = pd.DataFrame.from_dict(self._alldates_adjusted)
        #nn['unrel_profit'] = pd.DataFrame.from_dict(self._unrel_profit_adjusted)
        #nn['value']  = pd.DataFrame.from_dict(self._adjusted_value)






        nn = nn[[(c, d) for (c, d) in self._reg_panel.columns if c not in self.TOADJUSTLONG]]
        n1= return_subpanel('value',self._adjusted_value)
        n2= return_subpanel('alldates', self._alldates_adjusted)
        n3 = return_subpanel('unrel_profit',self._unrel_profit_adjusted)
        nn['rel_profit_by_stock']= nn['rel_profit_by_stock'].fillna(0)
        t = nn['rel_profit_by_stock'] + n3['unrel_profit']
        t.columns = pd.MultiIndex.from_product([['tot_profit_by_stock'], list(t.columns)], names=['Name', 'Symbols'])
        x= pd.concat([nn,t,n1,n2,n3], axis=1)
        return  x


    def filter_input(self,keys):

        for x in self.dicts:
            for k in keys:
                x.pop(k,'')



    def update_usable_symbols(self):
        self._usable_symbols = set()
        for t, dic in self._hist_by_date.items():
            self._usable_symbols.update(set(dic.keys()))

    def process(self, partial_symbol_update=set(),params=None):



        if params==None:
            params= copyit(self.params) #For now on , under lock..

        self.process_params = params
        try:
            self.process_internal(partial_symbol_update)
        except Exception as e:
            print('exception in processing', e )
            self.statusChanges.emit(f'Exception in processing {e}' )


    def process_internal(self, partial_symbol_update):
        t = time.process_time()
        if not self._initial_process_done:
            self.populate_buydic()
            self._initial_process_done = True
        elapsed_time = time.process_time() - t
        print('elasped populating : %s' % elapsed_time)
        if not partial_symbol_update:
            self.used_unitetype = self.process_params.unite_by_group
            required = set(self.required_syms(True, True))
            if config.DOWNLOADDATAFORPROT:
                self._symbols_wanted = self._buysymbols.union(required)  # there are symbols to check...
            else:
                self._symbols_wanted = required.copy()
        else:
            self._symbols_wanted.update(
                partial_symbol_update)  # will try also the symbols wanted. That are generally only updated first..
        t = time.process_time()
        self.process_history(partial_symbol_update)
        # do some stuff
        elapsed_time = time.process_time() - t
        print('elasped : %s' % elapsed_time)
    #self._proccessing_mutex.unlock()


