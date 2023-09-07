from transactions.transactioninterface import BuyDictItem,TransactionSource 
import collections
import logging
import math
import os
import pickle
import time
from collections import defaultdict
# from datetime import datetime
import datetime
from copy import copy
from functools import lru_cache, reduce, partial

import matplotlib
import numpy
import pandas
import pandas as pd
import pytz
from PySide6.QtCore import QRecursiveMutex

from common.loghandler import TRACELEVEL
from config import config
from common.common import UseCache, addAttrs, dictfilt, ifnn, print_formatted_traceback, log_conv, \
    localize_it, unlocalize_it, VerifySave, conv_date, tzawareness, ifnotnan, lmap
from common.simpleexceptioncontext import simple_exception_handling
from engine.parameters import copyit
from engine.symbols import SimpleSymbol
from input.earningscommon import localize_me
from input.earningsproc import EarningProcessor
from input.inputprocessorinterface import InputProcessorInterface

from input.inputsource import InputSource, InputSourceInterface
from engine.symbolsinterface import SymbolsInterface
from transactions.transactionhandlermanager import TransactionHandlerManager
#import input.earningsinp
StandardColumns = ['Open', 'High', 'Low', 'Close']


class SymbolError(Exception):
    pass


@addAttrs(['tot_profit_by_stock', 'value', 'alldates', 'holding_by_stock', 'rel_profit_by_stock', 'unrel_profit',
           'avg_cost_by_stock'])
class InputProcessor(InputProcessorInterface):

    def complete_status(self):
        def get_stat(filter_str):
            tmpinp = InputProcessor(self._eng, None)  # we already got our relevant history.
            transaction_handler = TransactionHandlerManager(tmpinp)  # a bit redundant. Just to be on the safe side..
            tmpinp._transaction_handler = transaction_handler
            x = copy(self._eng.params)
            x.use_cache = UseCache.FORCEUSE
            tmpinp.process(params=x, buy_filter=lambda x: (filter_str in x[1].Notes))
            status = tmpinp._current_status
            return status

        return  get_stat("IB"), get_stat("MYSTOCK")

    @property
    def usable_symbols(self):
        return self._usable_symbols


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
    def inputsource(self) -> InputSourceInterface:
        return self._inputsource

    @property
    def transaction_handler(self) -> TransactionHandlerManager:
        return self._transaction_handler

    def __init__(self, symb, transaction_handler, input_source=None):
        self._force_upd_all_range = None

        self._inputsource: InputSource = input_source
        if self._inputsource is None:
            logging.warn("not using any source")
        self._eng : SymbolsInterface  =symb
        self._transaction_handler= transaction_handler
        self._income, self._revenue, = None,None
        self.cached_used = None
        self._symbols_wanted = set()
        self.symbol_info = collections.defaultdict(lambda:dict())
        self._usable_symbols = set()
        self._bad_symbols = set()
        self.currency_hist= None



        self.init_input()
        self._initial_process_done=False

        self.dicts_names = ['alldates', 'unrel_profit', 'value', 'avg_cost_by_stock','rel_profit_by_stock', 'tot_profit_by_stock', 'holding_by_stock']
        self._relevant_currencies_rates={}
        self.currencyrange=None
        self._proccessing_mutex = QRecursiveMutex()
        self._reg_panel=None
        self._adjusted_panel=None
        self._earningProc=EarningProcessor.generate_or_make()

        self.mindate=None
        self.maxdate=None
        self.failed_to_get_new_data=None


    def resolve_currency(self, sym, l, hist):
        #very inefficient . but for few..
        if 'Currency' in hist:
            currency = hist['Currency'][0]
        else:
            logging.debug(('no currency '))
            currency = 'unk'

        if currency == 'unk':
            logging.debug((f'resolving currency for {sym}'))
            currency = config.Symbols.STOCK_CURRENCY.get(sym, 'unk')
        if currency == 'unk':
            currency = config.Symbols.EXCHANGE_CURRENCY.get(l.get('exchange', 'unk'), 'unk')
        if currency == 'unk':
            logging.debug((f'unk currency for {sym}'))
        return currency

    @simple_exception_handling(err_description="error in adjusting sym for currency")
    def adjust_sym_for_currency(self, currency, enddate, fromdate, hist, sym):
        fromdate=unlocalize_it(fromdate)
        enddate=unlocalize_it(enddate)
        logging.debug(('adjusting for currency %s %s ' % (sym, currency)))



        currency_df = self.get_currency_hist(currency, fromdate, enddate)
        currency_df=currency_df.apply(lambda x: 1 / x)
        currency_df = currency_df[StandardColumns]
        hh = hist[StandardColumns].mul(currency_df, fill_value=numpy.NaN)
        if len(set(hist.index) - set(currency_df.index)) > 0:
            logging.debug((log_conv(' missing ', set(hist.index) - (set(currency_df.index)))))
        return hh

    def update_currency_hist(self,currency,df):
        df=df[StandardColumns]
        mi = pd.MultiIndex.from_product([[currency], list(StandardColumns)])
        df.columns = mi
        if self.currency_hist is None:
            self.currency_hist = df
        elif currency not in self.currency_hist:
            self.currency_hist = self.currency_hist.join(df)
        else: #merging
            #old=self.currency_hist[currency]
            #updated= old.combine_first(df)
            #self.currency_hist.reindex(index=updated.index)
            #self.currency_hist[currency] = updated
            self.currency_hist=self.currency_hist.combine_first(df)


    @lru_cache
    def get_currency_hist(self, currency, fromdate, enddate):
        fromdate=localize_it(conv_date(fromdate,premissive=False))
        enddate=localize_it(conv_date(enddate))
        pair = ( currency,config.Symbols.BASECUR)
        def get_good_keys():
            zz = self.currency_hist[currency].isna().any(axis=1)

            zz= list(self.currency_hist[currency].index[~zz])
            return lmap(partial(tzawareness, d2=fromdate),zz)

        # if isinstance(self.currency_hist,dict):
        #     self.currency_hist=None
        ls = (self.get_range_gap(get_good_keys(), fromdate, enddate) if self.currency_hist is not None  and currency in self.currency_hist else [(fromdate,enddate)])
        ls =list(ls)

        for (mindate, maxdate) in ls:
            tmpdf= self._inputsource.get_currency_history(pair, mindate, maxdate)
            if tmpdf is not None:
                self.update_currency_hist(currency,tmpdf)
        if not currency in self.currency_hist:
            raise ValueError("cant get currency to adjust")
        df = self.currency_hist[currency]
        return df #whatever we get is ok
        #goodind=  list(set([x for x in  self.currency_hist[currency].index if x>=(fromdate - datetime.timedelta(days=1)).date() and x<=enddate.date()  ]).intersection(set(get_good_keys())))
        #return df.loc[ goodind ]

    def process_history(self, partial_symbols_update=set()):

        if not partial_symbols_update:
            self.init_input()
        else:
            self.filter_input(partial_symbols_update)


        items= self._transaction_handler.buydic.items()
        if self._buy_filter:
            items = filter(self._buy_filter,items)

        buyoperations = collections.OrderedDict(sorted(items))  # ordered

        if self._transaction_handler._stockprices:
            self._transaction_handler._stockprices.filter_bad()
            splits = self._transaction_handler._stockprices.buydic
        else:
            splits = {}

        #round number to nearest integer
        l =lambda v: collections.OrderedDict({k1:(round(v1) if v1>0.97 else v1)  for (k1, v1) in v.items()})
        splits={k:l(v)  for k,v in splits.items()}
        mm = lambda v: reduce(lambda x,y: x*y , [1]+list(v.values()))
        maxsplit =defaultdict(lambda: 1,{k:mm(v)  for k,v in splits.items()})




        cur_action = buyoperations.popitem(False) if len(buyoperations)!=0 else None


        if self.process_params.transactions_fromdate == None:
            if not cur_action:
                self.process_params.transactions_fromdate = config.Input.DEFAULTFROMDATE
                logging.warn(('Trasactions are empty.Strarting from default date. '))
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

        if query_source:
            succ=self.get_data_from_source(partial_symbols_update,fromdate,todate)
            self.save_data()
        else:
            succ=True
        self.failed_to_get_new_data = succ == False

        logging.debug(('finish initi'))
        self.simplify_hist(partial_symbols_update)
        logging.debug(('finish simpl'))
        self.process_hist_internal(buyoperations, cur_action, partial_symbols_update,splits,maxsplit)

        logging.debug(('finish internal'))
        try:
            logging.log(TRACELEVEL,('entering lock'))
            self._proccessing_mutex.lock()
            logging.log(TRACELEVEL,('entered'))
            self.convert_dicts_to_df_and_add_earnings(partial_symbols_update)
            logging.log(TRACELEVEL,('fin convert'))
            if config.Input.IGNORE_ADJUST:
                self.adjusted_panel=self.reg_panel.copy()
            else:
                if not self.adjust_for_currency():
                    self.adjusted_panel = self.reg_panel.copy()
            logging.log(TRACELEVEL,('last'))
        finally:
            self._proccessing_mutex.unlock()
            logging.log(TRACELEVEL,('exit proc lock'))
        return succ

    def load_cache(self,minimal=False):
        query_source = True
        try:
            if minimal: # Symbol info is needed by TransactionHandler . So we load just this...
                _, symbinfo, _, _, _ = pickle.load(open(config.File.HIST_F, 'rb'))
                self.symbol_info = collections.defaultdict(dict)
                self.symbol_info.update(symbinfo)
                #patch
                for x in self.symbol_info:
                    if self.symbol_info[x]==None:
                        self.symbol_info[x]={}


                return
            else:
                hist_by_date, _ , self._cache_date,self.currency_hist,self.currencyrange = pickle.load(open(config.File.HIST_F, 'rb'))

            #self.currency_hist = None
            if self._cache_date - datetime.datetime.now() < config.Input.MAXCACHETIMESPAN or self.process_params.use_cache == UseCache.FORCEUSE:
                self._hist_by_date = hist_by_date
            #log the current hist_by_date status, include max date,min date,num of entries
            logging.debug((f'hist_by_date status: max date {max(self._hist_by_date.keys())}, min date {min(self._hist_by_date.keys())}, num of entries {len(self._hist_by_date)}'))



            self.update_usable_symbols()
            logging.debug((f'cache symbols used {sorted(list(self._usable_symbols))}'))
            if not self.process_params.use_cache == UseCache.FORCEUSE:
                query_source = not (set(self._symbols_wanted) <= set(
                    self._usable_symbols))  # all the buy and required are in there
            else:
                logging.debug((log_conv('using cache anyway', not (set(self._symbols_wanted) <= set(self._usable_symbols)))))
                query_source = False
                self.cached_used=True
        except Exception as e:
            e = e
            logging.warn((f'failed to use cache {e}'))
            import traceback;traceback.print_exc()
            if not minimal:
                self.cached_used = False
        return query_source

    def process_hist_internal(self, buyoperations, cur_action, partial_symbols_update, splits, maxsplit):
        def calc_splited(sym,last_time, time):
            def upd_spl():
                try:
                    next_one = next(iter(splits[sym]))
                    if next_one > time:
                        return False
                except StopIteration:
                    cur_split[sym] = None
                    return False

                cur_split[sym] = splits[sym].popitem(False) if len(splits[sym]) != 0 else None
                if cur_split[sym] is not None:
                    _cur_splited_bystock[sym] *= cur_split[sym][1]
                    return True
                return False
            #we want to be after last_time and before time but it is NOT! ok to go past time
            if cur_split[sym] is None and sym in splits:
                upd_spl()
                if last_time is None:
                    while cur_split[sym]:
                        if not upd_spl():
                            break

            if not last_time or cur_split[sym] is None:
                return

            while cur_split[sym] and cur_split[sym][0] < last_time:
                if not upd_spl():
                    break



            while cur_split[sym] and (cur_split[sym][0] > last_time)  and cur_split[sym][0] <= time:
                logging.debug((f"{sym} splited between {last_time} and {time} updating {cur_split[sym]}"))
                if not config.TransactionHandlers.ReadjustJustIB:
                    _cur_holding_bystock[sym] = _cur_holding_bystock[sym] * cur_split[sym][1]
                    _cur_avg_cost_bystock[sym] = _cur_avg_cost_bystock[sym] / cur_split[sym][1]
                if not upd_spl():
                    break
                logging.debug(f"new avg cost {sym} {_cur_avg_cost_bystock[sym]}  cur_hold {_cur_holding_bystock[sym]}")
            #here we passed time and updated splits.

        def update_curholding():
            x: BuyDictItem = cur_action[1]
            stock = x.Symbol
            #if stock is in TrackStockList , write to log state in terms of holding before and after transaction is applied


            if partial_symbols_update and stock not in partial_symbols_update:
                return


            cursplit = maxsplit[stock] / _cur_splited_bystock[stock]

            old_cost = _cur_avg_cost_bystock[stock]
            old_holding = _cur_holding_bystock[stock]
            old_holding_reflected = old_holding * cursplit

            old_cost_reflected= _cur_avg_cost_bystock_reflected_splits[stock]
            if (x.Source == TransactionSource.IB or x.Source == TransactionSource.CACHEDIBINSTOCK) and config.TransactionHandlers.ReadjustJustIB:
                if cursplit not in [0,1]:
                    orgcost = x.Cost
                    x = x._replace(Qty=x.Qty * cursplit, Cost=x.Cost / cursplit) #lets not update buy dic

                    logging.warn(log_conv(('readjusting transaction IB', x, 'price', _cur_stock_price[stock][0],
                                       'by split', cursplit, 'before cost ', orgcost, 'date:', cur_action[0])))

            elif x.Source == TransactionSource.STOCK and config.TransactionHandlers.DontAdjustSplitsMyStock and stock in _cur_splited_bystock:
                if cursplit ==0:
                    logging.warn((f'zero split {x} {cursplit}'))
                #if x.Qty==round(x.Qty) and  int(round(x.Qty)) and int(round(x.Qty)) % int(roind(_cur_splited_bystock[stock][1])  != 0:
                #    logging.warn((f'not integer split {x} {_cur_splited_bystock[stock]}'))
                #elif x.Qty!=round(x.Qty):
                #    logging.warn(("not integer qty" ,x))
                elif cursplit!=1 and stock not in config.TransactionHandlers.DontReadjust:
                    orgcost=x.Cost
                    x=x._replace(Qty=x.Qty / cursplit, Cost=x.Cost * cursplit)
                    logging.warn(log_conv(('readjusting transaction mystock' , x, 'price',_cur_stock_price[stock][0]  ,'by split', cursplit, 'before cost ', orgcost ,  'date:', cur_action[0] )))
                    refnum= orgcost if config.Input.PRICES_ARE_ADJUSTED_TO_TODAY else x.Cost
                    if _cur_stock_price[stock][0] and  abs(refnum/_cur_stock_price[stock][0] -1)>0.3:
                        logging.warn("Very different price")

                    self.transaction_handler.update_buydic(cur_action[0], val=x)
            if (cursplit !=1 ):
                self.transaction_handler.update_buydic(cur_action[0], val=x._replace(AdjustedPrice = x.Cost / cursplit ))


            if x[0]*old_holding >= 0: #we increase our holding.
                _cur_avg_cost_bystock[stock] = (old_holding * old_cost + x[0] * x[1]) / (
                            old_holding + x[0])
                _cur_avg_cost_bystock_reflected_splits[stock] = (old_holding_reflected * old_cost_reflected + x[0] * x[1] / cursplit) / (
                            old_holding_reflected + x[0])

                # self._avg_cost_by_stock[stock][cur_action[0]] = nv
            else:
                if abs(int(x.Qty))>abs(int(old_holding)): #we switch to the other side. so we do selling of old_holding, and buying on the other
                    _cur_relprofit_bystock[stock] += old_holding * (
                            x[1] - _cur_avg_cost_bystock[stock])
                    _cur_avg_cost_bystock[stock] = (x[1])
                    _cur_avg_cost_bystock_reflected_splits[stock] = (x[1]/ cursplit)#* ( -1 if x[0]< 0 else 1) #-905 if neg

                else:
                    _cur_relprofit_bystock[stock] += old_holding * (
                            x[1] - _cur_avg_cost_bystock[stock])
                    if int(x.Qty)== int(old_holding):
                        _cur_avg_cost_bystock[stock] = 0
                    #_cur_relprofit_bystock[stock] += (-1) * ( x[0] * (
                    #            x[1]  - _cur_avg_cost_bystock[stock]))

                 #_cur_relprofit_bystock[stock] += x[0] * (
                 #                        x[1] * (-1) - _cur_avg_cost_bystock[stock])
                # self.rel_profit_by_stock[stock][cur_action[0]] =  _cur_relprofit_bystock[stock]

            _cur_holding_bystock[stock] += x[0]
            _cur_accumative_holding_bystock[stock] += abs(x[0])

            _last_action_time[stock]=cur_action[0]
            if _first_action_time[stock] is None:
                _first_action_time[stock]=cur_action[0]

            if _cur_holding_bystock[stock] < 0:
                logging.warn((log_conv(' sell below zero', stock, cur_action[0])))
                if 0:
                    self._transaction_handler.try_fix_dic(cur_action,_last_action[stock], _cur_holding_bystock[stock] )
            if stock in config.TransactionHandlers.TrackStockList:
                logging.debug('after applying action ' + str(x) +" time is "+ str(t))
                logging.debug('current holding of stock %s is %f' % (stock, _cur_holding_bystock[stock])) 
                logging.debug('current avg cost of stock %s is %f' % (stock, _cur_avg_cost_bystock[stock]))
                logging.debug('current splits of stock %s is %f' % (stock, cursplit))
                #relprofit
                logging.debug('current relprofit of stock %s is %f' % (stock, _cur_relprofit_bystock[stock]))
                logging.debug('current unrelprofit of stock %s is %f' % (stock, _cur_unrelprofit_bystock[stock]))
                logging.debug('current avg cost reflected of stock %s is %f' % (stock, _cur_avg_cost_bystock_reflected_splits[stock]))
                logging.debug('current price of stock %s is %f' % (stock, _cur_stock_price[stock][0]))
        self.mindate = min(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(min(self._hist_by_date.keys())/1000,tz)
        self.maxdate = max(
            self._hist_by_date.keys())  # datetime.datetime.fromtimestamp(max(self._hist_by_date.keys())/1000,tz)
        _cur_splited_bystock = defaultdict(lambda:1)
        _cur_avg_cost_bystock = defaultdict(lambda: 0)
        _cur_avg_cost_bystock_reflected_splits = defaultdict(lambda: 0) #adjust the splits to today
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock = defaultdict(lambda: 0)
        _cur_unrelprofit_bystock = defaultdict(lambda: 0)
        _cur_stock_price = defaultdict(lambda: (numpy.NaN, numpy.NaN))
        _last_action_time = defaultdict(lambda: None)
        _first_action_time = defaultdict(lambda: None)
        cur_split = defaultdict(lambda: None)
        _last_action = defaultdict(lambda: None)
        _cur_accumative_holding_bystock = defaultdict(lambda: 0) #just used to calculate the total holding involved
        if len(self._simp_hist_by_date)==0 and (not partial_symbols_update):
            logging.warn(("WARNING: No History at all!"))
            return
        hh = pytz.UTC  # timezone('Israel')
        #copy to temporary var and restore at the end
        from_date ,to_date = self.process_params.transactions_fromdate, self.process_params.transactions_todate

        self.process_params.transactions_todate = localize_it(self.process_params.transactions_todate)
        self.process_params.transactions_fromdate = localize_it(self.process_params.transactions_todate)
        try:
            if not partial_symbols_update:
                self._fset=set()
            simphist=iter(sorted(self._simp_hist_by_date.items()))
            t=1

            dic={}
            while cur_action or t:
                try:
                    t, dic = next(simphist)
                    mini=False
                except StopIteration:
                    logging.log(TRACELEVEL,("stop iter"))
                    if len(buyoperations)>0:
                        cur_action = buyoperations.popitem(False)
                        t=cur_action[0]
                        mini=True
                    else:
                        break





                if partial_symbols_update:
                    dic = dictfilt(dic, partial_symbols_update)

                #t=tzawareness(t,self.process_params.transactions_todate)
                t=localize_it(t)

                if self.process_params.transactions_todate and t > self.process_params.transactions_todate:
                    break
                holdopt = set(_cur_holding_bystock.keys()).intersection(
                    partial_symbols_update) if partial_symbols_update else _cur_holding_bystock.keys()

                for sym in holdopt:
                    calc_splited(sym,_last_action_time.get(sym), t)

                while cur_action and (t >= cur_action[0]):
                    calc_splited(cur_action[1][2], _last_action_time.get(cur_action[1][2]),cur_action[0])
                    update_curholding()
                    if len(buyoperations) == 0:
                        cur_action = None
                        break
                    cur_action = buyoperations.popitem(False)

                tim = matplotlib.dates.date2num(t)
                holdopt = set(_cur_holding_bystock.keys()).intersection(
                    partial_symbols_update) if partial_symbols_update else _cur_holding_bystock.keys()
                for sym in holdopt:
                    if partial_symbols_update and not sym in partial_symbols_update:
                        continue
                    self._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                    self._rel_profit_by_stock[sym][tim] = _cur_relprofit_bystock[sym]
                    self._avg_cost_by_stock[sym][tim] = _cur_avg_cost_bystock[sym]
                    self._split_by_stock[sym][tim] = _cur_splited_bystock[sym]
                if mini:
                    continue
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

                    if config.Input.AdjustUnrelProfitToReflectSplits:
                        cursplit = maxsplit[sym] / _cur_splited_bystock[sym]
                        _cur_unrelprofit_bystock[sym]= (v[0] - _cur_avg_cost_bystock_reflected_splits[sym]) * _cur_holding_bystock[sym]*cursplit
                    else:
                        _cur_unrelprofit_bystock[sym]= (v[0] - _cur_avg_cost_bystock[sym]) * _cur_holding_bystock[sym]




                    self._unrel_profit[sym][tim] = _cur_unrelprofit_bystock[sym]
                    self._unrel_profit_adjusted[sym][tim] = v[1] * _cur_holding_bystock[sym] - _cur_holding_bystock[sym] * \
                                                   _cur_avg_cost_bystock[sym]
                    self._tot_profit_by_stock[sym][tim] = self._rel_profit_by_stock[sym][tim] + self._unrel_profit[sym][tim]
                    _last_action[sym] = cur_action
                self._fset.add(tim)
            if not partial_symbols_update:
                self.update_current_status(
                    {"Holding" : _cur_holding_bystock,
                     "Unrealized profit": _cur_unrelprofit_bystock,
                     "Realized  profit":  _cur_relprofit_bystock,
                     "AccumulatedHolding": _cur_accumative_holding_bystock,
                     "Average Cost": _cur_avg_cost_bystock,
                     'First Action': {x:  pd.to_datetime(y) for x,y in _first_action_time.items()},
                     'Last Action': {x: pd.to_datetime(y)  for x,y in  _last_action_time.items()}

                })
                self._cur_splits=_cur_splited_bystock
        finally:
            pass#self.process_params.transactions_todate=to_date
            #self.process_params.transactions_fromdate=from_date

        #self._cur_holding_bystock=_cur_holding_bystock

        
    
    def update_current_status(self, dicdics):
        def get_DF(dic,name):
            df=pd.DataFrame.from_dict(dict(dic).items())
            if len(df)==0:
                return df
            df.columns=["stock",name]
            df=df.set_index("stock")
            return df

        dfs = [get_DF(dic,name) for name,dic in dicdics.items()]
        st= dfs[0]
        for k in dfs[1:]:
            st=st.join(k,on='stock',how='left')

        self._current_status= st

    def get_portfolio_stocks(self):
        if self._current_status is None:
            return set()
        return set(self._current_status[ self._current_status['Holding']!=0].index)








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

    @staticmethod
    def get_range_gap(dates,fromdate,todate):
        TOLLERENCE = 5  # config
        if (todate-fromdate).days<TOLLERENCE*5:
            TOLLERENCE=0
        #yields the gaps in data between dates ..
        dates= sorted(lmap(conv_date,dates))
        #dates = sorted(lmap(partial( tzawareness,d2=fromdate) , dates ))

        if len(dates)<2 or dates[-1]<=fromdate:
            yield  fromdate,todate
        reachedfrom=False
        fromdate,todate = fromdate.date(),todate.date()
        af=None
        for da,af  in zip( dates[:-1],dates[1:]):
            da,af=da.date(),af.date()
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
            if (af-da).days>TOLLERENCE and (af-da).days>1: #gap
                yield da,min(af,todate) #we miss all the days inbetween

        if af and af<todate and (todate-af).days>TOLLERENCE:
            yield af,  todate

    def get_data_from_source(self, partial_symbols_update,fromdate,todate):
        if self._inputsource is None:
            return False





        self.symbol_info_tmp={}

        if not partial_symbols_update:
            self._usable_symbols = set()
            self._bad_symbols = set()
            self._hist_by_date = collections.OrderedDict()  # like all dates but by
        else:
            self._bad_symbols=self._bad_symbols - set(partial_symbols_update) #meaning we don't ignore symbols here , even if before they were bad
        todate = todate if todate is not None else datetime.datetime.now()

        todate = localize_it(todate)

        fromdate = localize_it(fromdate)

        successful_once=False
        if fromdate==todate:
            raise Exception("identical dates")
        for sym in list(self._symbols_wanted if not partial_symbols_update else partial_symbols_update):

            sym_corrected = self.process_params.resolve_hack.get(sym, None)
            if not sym_corrected:
                sym_corrected = config.Symbols.TRANSLATEDIC.get(sym, sym)


            if not self._force_upd_all_range and sym in self._hist_by_date:
                ls = self.get_range_gap(list(self._hist_by_date[str(sym)].keys()),fromdate,todate) #we have data for this symbol
            else:
                ls = [(fromdate,todate)]
            okdays=0
            requireddays=0
            try:
                for (mindate,maxdate) in  ls:
                    okdays+=self.get_hist_sym(mindate, maxdate, sym, sym_corrected)
                    requireddays+=(maxdate-mindate).days

            except SymbolError:
                logging.debug(('bad %s' % sym))
                self._bad_symbols.add(sym) #we will not try again. But every run we do try once...
                continue
            successful_once=True
            if requireddays/okdays<0.5:
                logging.debug((f'mostly problematic {sym}'))
        return successful_once


    def get_hist_sym(self,mindate, maxdate, sym, sym_corrected):
        if self._inputsource is None:
            return 0
        logging.debug((f'getting symbol hist for {sym} ({sym_corrected}) from {mindate} to {maxdate}'))
        #self._inputsource.ownership()
        l, hist = self._inputsource.get_symbol_history(sym_corrected, mindate, maxdate,
                                                       iscrypto= (str(sym_corrected) in config.Symbols.CRYPTO))  # should be rounded

        self.symbol_info[sym] = (l if l else {}) #just for debug I think
        if (cont := self.symbol_info[sym].get('contract')):
            logging.debug(f"resolved {sym} is {cont}")
        if hist is None:
            raise SymbolError("bad symbol")
        else:
            logging.debug(f"got history for {sym}")
        if l is None:
            logging.warn("no info for %s , using default " % sym)
            currency =  'unk'
        elif not (sym in self.symbol_info and ('currency' in self.symbol_info[sym] ) and self.symbol_info[sym]['currency']) :
            currency = self.resolve_currency(sym, l, hist)
            self.symbol_info[sym].update( {'currency': currency})
        else:
            currency= self.symbol_info[sym]['currency']

        if currency != config.Symbols.BASECUR and currency != 'unk':
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
        if self.process_params.use_cache == UseCache.DONT:
            if config.Running.VERIFY_SAVING == VerifySave.DONT:
                logging.warn("Not saving data because not using cache")
                return
            logging.warn("Saving data without using cache! Can earse data!")
            if config.Running.VERIFY_SAVING == VerifySave.Ask :

                x=input('Are you sure you want to? (y to accept)')
                if x.lower()!='y':
                    return


        import shutil
        try:
            shutil.copy(config.File.HIST_F, config.File.HIST_F_BACKUP)
        except:
            logging.debug(('error in backuping hist file'))
        try:
            pickle.dump((self._hist_by_date, dict(self.symbol_info), datetime.datetime.now(), self.currency_hist,
                         self.currencyrange), open(config.File.HIST_F, 'wb'))
            logging.debug(('hist saved'))
        except:
            logging.error(("error in dumping hist"))
            print_formatted_traceback()


    def convert_dicts_to_df_and_add_earnings(self,partial_symbols_update):
        dataframes = []
        self.dicts = [self._alldates, self._unrel_profit, self._value, self._avg_cost_by_stock,
                      self._rel_profit_by_stock, self._tot_profit_by_stock, self._holding_by_stock,
                      self._alldates_adjusted,self._unrel_profit_adjusted]
        NONADJUSTEDDICTS= len(self.dicts) -2
        # no more dicts #we removed alldatesadjusted from dicts..
        seldict= self.dicts[:NONADJUSTEDDICTS]

        try:

            #income, revenue, cs =# get_earnings()
            raise Exception("no earnings for now")
            #income, revenue, cs = #EarningProcessor()
            hasearnings=True
            combinedindex = sorted(
                list(set(self._fset).union(set(cs.index)).union(set(income.index)).union(set(revenue.index))))
        except:
            logging.warn(('earning reading failed'))
            # import traceback
            # traceback.print_exc()
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
            logging.debug(('earnings calc failed '))

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
        if self._inputsource is None:
            return
        if x not in self._relevant_currencies_rates:
            self._relevant_currencies_rates[x] = self._inputsource.get_current_currency((config.Symbols.BASECUR, x))
        return  self._relevant_currencies_rates[x]

    @simple_exception_handling("adjusting for currency", return_succ=0)
    def adjust_for_currency(self):
        a=1
        relevant_currencies = set([v.get('currency','unk') for v in self.symbol_info.values() if not (v is None)]) - \
                              set(['unk', config.Symbols.BASECUR])
        if self._inputsource is None:
            logging.warn("Could not adjust for currency because no input source. Ignoring adjustment.")
            return False
        for x in relevant_currencies:
            self._relevant_currencies_rates[x] = ifnotnan(self._inputsource.get_current_currency((config.Symbols.BASECUR, x)),lambda t:1/t)
        #fix the following line for case 'currency' is not in dictonary of value v of symbol_info
        dic={k: self._relevant_currencies_rates.get(curr) for k,v in self.symbol_info.items() if (curr:=v.get('currency', 'unk')) in self._relevant_currencies_rates and self._relevant_currencies_rates[curr] is not None}
        #dic={k:self._relevant_currencies_rates[v['currency']] for k,v in self.symbol_info.items() if ifnn(v,lambda : v['currency']!=config.Symbols.BASECUR  and (v['currency'] in self._relevant_currencies_rates))}

        self._adjusted_panel=self.get_adjusted_df_for_currency(dic)
        return True

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
        self._split_by_stock = defaultdict(lambda: defaultdict(lambda: 1))

    def get_adjusted_df_for_currency(self, dic):
        def return_subpanel(s,dic):
            t=pd.DataFrame.from_dict(dic)
            t.columns=pd.MultiIndex.from_product([[s], list(t.columns)], names=['Name', 'Symbols'])
            return t

        relevant=set(lmap(lambda x: x[1], self._reg_panel.columns)).intersection(set(dic.keys()))
        #list(dic.keys())

        multiIndex = pd.MultiIndex.from_product([SymbolsInterface.TOADJUST,relevant ], names=['Name', 'Symbols'])
        if len(multiIndex)==0:
            logging.debug('no symbols to adjust')
            return False
        df = pd.DataFrame(index=self._reg_panel.index, columns=multiIndex)
        for x in SymbolsInterface.TOADJUST:
            for k, v in dic.items():
                df.loc[:, (x, k)] = dic[k]

        nn=pd.DataFrame(index=self._reg_panel.index, columns=self._reg_panel.columns)#[ (c,d)  for (c,d) in   self.reg_panel.columns if c!='tot_profit_by_stock']  )
        for x in SymbolsInterface.TOKEEP:
            if x in self._reg_panel:
                nn[x] = self._reg_panel[x].copy() #nn.merge( self.reg_panel[x],on=nn.index, suffixes=None)

        df1 = self._reg_panel[multiIndex]
        cols_to_multiply = df1.columns.intersection(df.columns)
        nn[cols_to_multiply] = df1[cols_to_multiply].mul(df[cols_to_multiply])

       # nn['alldates'] = pd.DataFrame.from_dict(self._alldates_adjusted)
        #nn['unrel_profit'] = pd.DataFrame.from_dict(self._unrel_profit_adjusted)
        #nn['value']  = pd.DataFrame.from_dict(self._adjusted_value)






        nn = nn[[(c, d) for (c, d) in self._reg_panel.columns if c not in SymbolsInterface.TOADJUSTLONG]]
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
                x.pop(str(k),'')



    def update_usable_symbols(self):
        self._usable_symbols = set()
        for t, dic in self._hist_by_date.items():
            self._usable_symbols.update(set(dic.keys()))

    def process(self, partial_symbol_update=set(),params=None,buy_filter=None,force_upd_all_range=False):

        logging.debug("process start")

        if params==None:
            params= copyit(self._eng.params) #For now on , under lock.. #Only time we need access to compareengine.

        self.process_params = params
        self._buy_filter=buy_filter
        self._force_upd_all_range=force_upd_all_range
        #This would return text for each symbol. see comment about resolve_hack in parameters.
        #From this point, symbols are textual!
        ls=set(self.process_params.helper([SimpleSymbol(s) for s in  partial_symbol_update]))
        try:
            ret=self.process_internal(ls)

        except Exception as e:
            if os.environ.get('PYCHARM_HOSTED') == '1' and config.Running.STOP_EXCEPTION_IN_DEBUG:
                raise #will try
            import traceback
            logging.error(('exception in processing' ))
            print_formatted_traceback()
            try:
                import Pyro5
                logging.error(("".join(Pyro5.errors.get_pyro_traceback())))
            except:
                pass
            self._eng.statusChanges.emit(f'Exception in processing {e}')


    def process_internal(self, partial_symbol_update):
        t = time.process_time()
        if not self._initial_process_done:
            self.load_cache(True)

            self.process_transactions()
            self._initial_process_done = True
        elapsed_time = time.process_time() - t
        logging.debug(('elasped populating : %s' % elapsed_time))
        if not partial_symbol_update:
            self.used_unitetype = self.process_params.unite_by_group
            required = set(self._eng.required_syms(True, True))
            if config.Input.DOWNLOADDATAFORPROT:
                self._symbols_wanted = self._transaction_handler.buysymbols.union(required)  # there are symbols to check...
            else:
                self._symbols_wanted = required.copy()
        else:
            self._symbols_wanted.update(
                partial_symbol_update)  # will try also the symbols wanted. That are generally only updated first..
        t = time.process_time()
        ret= self.process_history(partial_symbol_update)
        # do some stuff
        elapsed_time = time.process_time() - t
        logging.debug(('elasped : %s' % elapsed_time))
        return ret

    @simple_exception_handling(err_description="error in process transactions")
    def process_transactions(self):
        self._transaction_handler.process_transactions()
    #self._proccessing_mutex.unlock()

    
