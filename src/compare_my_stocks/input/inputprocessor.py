from common.common import c, ass
from common.composition import C
from memoization import cached

from common.refvar import RefVar
from compare_my_stocks.common.common import neverthrow
from compare_my_stocks.common.dolongprocess import DoLongProcessSlots, TaskParams
from input.inputdata import InputDataImpl
from input.inputdatainterface import InputDataImplInterface
from input.inputprocessorinterface import InputProcessorInterface
from transactions.transactioninterface import BuyDictItem,TransactionSource
import collections
import logging
import math
import time
from collections import defaultdict
# from datetime import datetime
import datetime
from copy import copy
from functools import reduce, partial

import matplotlib
import numpy
import pandas
import pandas as pd
import pytz
from PySide6.QtCore import QRecursiveMutex

from common.loghandler import TRACELEVEL
from config import config
from common.common import UseCache, addAttrs, dictfilt, ifnn, log_conv, \
    localize_it, unlocalize_it, conv_date, tzawareness, ifnotnan, lmap, selfifnn, StandardColumns, subdates
from common.simpleexceptioncontext import simple_exception_handling, SimpleExceptionContext
from engine.parameters import copyit
from engine.symbols import SimpleSymbol
from input.earningsproc import EarningProcessor

from input.inputsource import InputSource, InputSourceInterface
from engine.symbolsinterface import SymbolsInterface
from transactions.transactionhandlermanager import TransactionHandlerManager
from typing import NamedTuple, Optional, Union

#import input.earningsinp
BuyOp= NamedTuple("BuyOp", [('date', datetime.datetime), ('buydic', BuyDictItem), ('currency',Union[Optional[float],str])])

class SymbolError(Exception):
    pass


@addAttrs(['tot_profit_by_stock', 'value', 'alldates', 'holding_by_stock', 'rel_profit_by_stock', 'unrel_profit',
           'avg_cost_by_stock'])
class InputProcessor(InputProcessorInterface):
    dicts_names = ['alldates', 'unrel_profit', 'value', 'avg_cost_by_stock', 'rel_profit_by_stock',
                   'tot_profit_by_stock', 'holding_by_stock']

    @property
    def _data(self) -> InputDataImplInterface:
        return ass(self.data)

    def __getattr__(self, item): #for external access mainly
        if 'ipython' in item:
            raise AttributeError(item)
        if 'getattr' in item:
            raise AttributeError(item)
        # logging.debug(item)
        if hasattr(self.data,item):
            return getattr(self.data,item)

    def complete_status(self):
        def get_stat(filter_str):
            tmpinp = InputProcessor(self._eng, None)  # we already got our relevant history.
            transaction_handler = TransactionHandlerManager(tmpinp)  # a bit redundant. Just to be on the safe side..
            tmpinp._transaction_handler = transaction_handler
            x = copy(self._eng.params)
            x.use_cache = UseCache.FORCEUSE
            tmpinp.process(params=x, buy_filter=lambda x: (filter_str in x[1].Notes))
            status = tmpinp._data._current_status
            return status

        return  get_stat("IB"), get_stat("MYSTOCK")

    @property
    def usable_symbols(self):
        return self._data._usable_symbols


    @property
    def reg_panel(self):
        self._proccessing_mutex.lock()
        x= self._data._reg_panel
        self._proccessing_mutex.unlock()
        return x

    @reg_panel.setter
    def reg_panel(self, value):
        self._data._reg_panel=value
        pass

    @property
    def adjusted_panel(self):
        self._proccessing_mutex.lock()
        x= self._data._adjusted_panel
        self._proccessing_mutex.unlock()
        return x

    @adjusted_panel.setter
    def adjusted_panel(self, value):
        self._data._adjusted_panel=value #we are under lock
        pass

    @property
    def InputSource(self) -> InputSourceInterface:
        return self._InputSource

    @property
    def transaction_handler(self) -> TransactionHandlerManager:
        return self._transaction_handler

    def __init__(self, symb, transaction_handler, InputSource=None):
        self.to_save_data = False 
        self._force_upd_all_range = None

        self._InputSource: InputSource = InputSource
        if self._InputSource is None:
            logging.warn("not using any source")
        self._eng : SymbolsInterface  =symb
        self._transaction_handler= transaction_handler
        self._income, self._revenue, = None,None


        self.data : Optional[InputDataImpl]=None # type: InputDataImpl


        self._initial_process_done=False

        self._relevant_currencies_rates={}
        self._relevant_currencies_time = None

        self._proccessing_mutex = QRecursiveMutex()
        self._earningProc=EarningProcessor.generate_or_make()


        self.failed_to_get_new_data=None

        self._save_data_proc=DoLongProcessSlots(self._save_data)
        # self.currency_on_date = c(self.get_currency_on_certain_time,lambda t,sym,cache_only: (t,self._data.get_currency_for_sym(sym),cache_only) )
        self.currency_on_date = C// self.get_currency_on_certain_time % { 'curr':  (lambda sym : self._data.get_currency_for_sym(sym)) } #@ (lambda t,sym,cache_only: (t,sym,cache_only))
        a=1

    @property
    def initialized(self):
        return self.data is not None
    @cached
    def trivial_currency(self,sym):
        return (self._data.get_currency_for_sym(sym) in [config.Symbols.Basecur, 'unk'])


    def resolve_currency(self, sym, l, hist):
        #very inefficient . but for few..
        if 'Currency' in hist:
            currency = hist['Currency'][0]
        else:
            logging.debug(('no currency '))
            currency = 'unk'

        if currency == 'unk':
            logging.debug((f'resolving currency for {sym}'))
            currency = config.Symbols.StockCurrency.get(sym, 'unk')
        if currency == 'unk':
            currency = config.Symbols.ExchangeCurrency.get(l.get('exchange', 'unk'), 'unk')
        if currency == 'unk':
            logging.debug((f'unk currency for {sym}'))
        return currency

    @simple_exception_handling(err_description="error in adjusting sym for currency")
    def get_adjusted_df_for_currency(self, currency, enddate, fromdate, hist, sym):
        fromdate=unlocalize_it(fromdate)
        enddate=unlocalize_it(enddate)
        logging.debug(('adjusting for currency %s %s ' % (sym, currency)))



        currency_df = self.get_currency_hist(currency, fromdate, enddate)
        factor=self._data.get_currency_factor_for_sym(sym)
        currency_df=currency_df.apply(lambda x: 1 / x / factor) #notice that this should be in the hist not here, but same same
        currency_df = currency_df[StandardColumns]
        hh = hist[StandardColumns].mul(currency_df, fill_value=numpy.NaN)
        if len(set(hist.index) - set(currency_df.index)) > 0:
            logging.debug((log_conv('Not all entiries could be adjusted ', set(hist.index) - (set(currency_df.index)))))

        return hh

    def update_currency_hist(self,currency,df):
        df=df[StandardColumns]
        mi = pd.MultiIndex.from_product([[currency], list(StandardColumns)])
        df.columns = mi
        if self._data.currency_hist is None:
            self._data.currency_hist = df
        elif currency not in self._data.currency_hist:
            self._data.currency_hist = self._data.currency_hist.join(df)
        else: #merging
            #old=self._data.currency_hist[currency]
            #updated= old.combine_first(df)
            #self._data.currency_hist.reindex(index=updated.index)
            #self._data.currency_hist[currency] = updated
            self._data.currency_hist=self._data.currency_hist.combine_first(df)


    def get_currency_hist(self, currency, fromdate, enddate,minimal=False,queried: Optional[RefVar]=None,cache_only=False):
        fromdate=localize_it(conv_date(fromdate,premissive=False))
        enddate=localize_it(conv_date(enddate))
        pair = ( currency,config.Symbols.Basecur)
        def get_good_keys():
            zz = self._data.currency_hist[currency].isna().any(axis=1)

            zz= list(self._data.currency_hist[currency].index[~zz])
            return lmap(partial(tzawareness, d2=fromdate),zz)

        # if isinstance(self._data.currency_hist,dict):
        #     self._data.currency_hist=None

        fromdateaware = pd.to_datetime(unlocalize_it(fromdate))
        enddateaware =  pd.to_datetime(unlocalize_it(enddate))
        didquery=False

        df=None

        try:
            df = self._data.currency_hist[currency]
            tmpdf=df.loc[pd.to_datetime(fromdate.date()):pd.to_datetime( (enddate+datetime.timedelta(days=1)).date() )]
            if tmpdf.empty:
                raise KeyError("empty")
            if not minimal:
                raise KeyError("not minimal")#lets avoid checks here and let get_range_gap handle it
        except: 
            if cache_only:
                raise ValueError("cant get currency to adjust")
            ls = (self.get_range_gap(get_good_keys(), fromdate, enddate) if self._data.currency_hist is not None  and currency in self._data.currency_hist else [(fromdate,enddate)])
            ls =list(ls)
            if len(ls) == 0:
                logging.debug("have all data")
                return df


            for (mindate, maxdate) in ls:
                try:
                    tmpdf= self._InputSource.get_currency_history(pair, mindate, maxdate)
                except AssertionError:
                    raise ValueError("Bad currency")
                didquery=True
                logging.debug("get currency history %s %s %s %s" % (pair, mindate, maxdate,len(selfifnn(tmpdf,[]))))
                if tmpdf is not None:
                    self.update_currency_hist(currency,tmpdf)
                    self.save_data_at_end()
            if not currency in self._data.currency_hist:
                raise ValueError("cant get currency to adjust")
        if queried is not None:
            queried.value= didquery

        if not minimal:
            if df is None:
                return tmpdf
            return df #whatever we get is ok
        else: 
            return tmpdf #we need to get the exact range




        #goodind=  list(set([x for x in  self._data.currency_hist[currency].index if x>=(fromdate - datetime.timedelta(days=1)).date() and x<=enddate.date()  ]).intersection(set(get_good_keys())))
        #return df.loc[ goodind ]
    
    def get_currency_on_certain_time(self, curr,  t,cache_only=False ):

        for i in range(1,3):
            queried=RefVar(False)
            df= self.get_currency_hist(curr, t - datetime.timedelta(days=i),
                                       t + datetime.timedelta(days=i),
                                       minimal=True,queried=queried, cache_only=cache_only)  #To do : account for base currency different than USD, such as EUR.ILS
            if df is None or len(df)==0:
                continue
            else:
                #df.where(lambda x: df.index == t).dropna().iloc[0]
                try:
                    row= list(filter(lambda x: x[0].day == t.day, df.iterrows()))[0][1]
                except:
                    row= df.iloc[0]
                    logging.warn(f"could not find exact date for currency {t} {curr} got {row.name}")

                curval= (row['Open']+row['Close']) /2

                return (curval,queried.value)
        else:
           logging.error(f"no currency {curr} {t}")
           return (None,False)

    def save_data_at_end(self):
        self.to_save_data=True 

            



    def get_buy_operations_with_adjusted(self,items):
        logging.debug("st get_buy")
        self._data._no_adjusted_for = set()
        gok=False
        for t,v in items:
            v: BuyDictItem
            curr=self._data.get_currency_for_sym(v.Symbol)
            if curr in set(['unk', config.Symbols.Basecur]):
                self._data._no_adjusted_for.add(v.Symbol) #TODO reverse the logic
                yield BuyOp(date=localize_it(t),currency=None,buydic=v)
            else:
                try:
                    with SimpleExceptionContext(err_description= f"error getting currency for transaction {v.Symbol}", detailed=False):
                        val, queried = self.get_currency_on_certain_time(curr, t)
                        if queried:
                            gok=True
                        if val == 'err':
                            self._data._err_transactions.add(v.Symbol)
                        
                        yield BuyOp(date=localize_it(t),currency=val ,buydic=v)

                except KeyError as e:
                    logging.error(str(e))
        if gok:
            self.save_data_at_end()
        logging.debug("end get_buy")

            
        

    def process_history(self, partial_symbols_update=set()):
        self.to_save_data=False # unless we get new data 

        if not partial_symbols_update:
            self._data.init_input()
        #else:
        #    self.filter_input(partial_symbols_update) #seems to do nothing. Will leave it here for now
        query_source = True
        if self.process_params.use_cache != UseCache.DONT and not partial_symbols_update:
            query_source = self._data.load_cache(process_params=self.process_params)

        items= self._transaction_handler.buydic.items()
        if self._buy_filter:
            items = filter(self._buy_filter,items)
        if partial_symbols_update:
            items = filter(lambda x: x[1].Symbol in partial_symbols_update,items)


        #items= map(lambda x: (x[0],x[1]._replace(Symbol=config.Symbols.ReplaceSymInInput.get(x[1].Symbol,x[1].Symbol)))  ,items)



        from common.common import c
        buyoperations = c(collections.OrderedDict, map)(lambda x: ((x[0]),x), c(self.get_buy_operations_with_adjusted,sorted)(items)) 
        
        

        if self._transaction_handler._StockPrices:
            self._transaction_handler._StockPrices.filter_bad()
            splits = self._transaction_handler._StockPrices.buydic
        else:
            splits = {}

        #round number to nearest integer
        l =lambda v: collections.OrderedDict({k1:(round(v1) if v1>0.97 else v1)  for (k1, v1) in v.items()})
        splits={k:l(v)  for k,v in splits.items()}
        mm = lambda v: reduce(lambda x,y: x*y , [1]+list(v.values()))
        maxsplit =defaultdict(lambda: 1,{k:mm(v)  for k,v in splits.items()})




        _ , cur_action = buyoperations.popitem(False) if len(buyoperations)!=0 else (1,None)


        if self.process_params.transactions_fromdate == None:
            if not cur_action:
                self.process_params.transactions_fromdate = config.Input.DefaultFromDate
                logging.warn(('Trasactions are empty.Strarting from default date. '))
            else:
                self.process_params.transactions_fromdate = cur_action[0] #start from first buy

        if  partial_symbols_update:
            todate=self.process_params.todate
            fromdate=self.process_params.fromdate
        else:
            fromdate=self.process_params.transactions_fromdate
            todate=self.process_params.transactions_todate



        if query_source:
            succ=self.get_data_from_source(partial_symbols_update,fromdate,todate)
            if succ:
                self.save_data_at_end()
        else:
            succ=True
        self.failed_to_get_new_data = succ == False

        logging.debug(('finish initi'))
        self.simplify_hist(partial_symbols_update)
        logging.debug(('finish simpl'))
        self.process_hist_internal(buyoperations, cur_action, partial_symbols_update,splits,maxsplit) #takes around 1 sec

        logging.debug(('finish internal'))
        try:
            logging.log(TRACELEVEL,('entering lock'))
            self._proccessing_mutex.lock()
            logging.log(TRACELEVEL,('entered'))
            self.convert_dicts_to_df_and_add_earnings(partial_symbols_update)
            logging.log(TRACELEVEL,('fin convert'))
            if config.Input.IgnoreAdjust:
                self.adjusted_panel=self._data._reg_panel.copy()
            else:
                if not self.adjust_for_currency():
                    self.adjusted_panel = self._data._reg_panel.copy()
            logging.log(TRACELEVEL,('last'))
            if self.to_save_data:
                self.save_data() 

        finally:
            self._proccessing_mutex.unlock()
            logging.log(TRACELEVEL,('exit proc lock'))
        return succ
    @staticmethod
    def log_info(x, t, stock, cur_holding, cur_avg_cost, cur_avg_cost_bystock_adjusted, cursplit, cur_relprofit, cur_unrelprofit, cur_unrelprofit_adjusted, cur_avg_cost_reflected, cur_avg_cost_reflected_adjusted, cur_stock_price, stock_price_adjusted,rate):
        logging.info('After applying action: ' + str(x))
        logging.info("Time is " + str(t))
        logging.info(f'Current price of stock {stock} is {cur_stock_price} ({stock_price_adjusted})')
        logging.info(f'current rate is {rate}')
        logging.info(f'Current holding of stock {stock} is {cur_holding}')
        logging.info(f'Current avg cost of stock {stock} is {cur_avg_cost} {cur_avg_cost_bystock_adjusted}')
        logging.info(f'Current splits of stock {stock} is {cursplit}')
        logging.info(f'Current relprofit of stock {stock} is {cur_relprofit}')
        logging.info(f'Current avg cost reflected of stock {stock} is {cur_avg_cost_reflected} ({cur_avg_cost_reflected_adjusted})')
        logging.info( ('Previous' if x else 'Current') +        f' unrelprofit of stock {stock} is {cur_unrelprofit} ({cur_unrelprofit_adjusted})')

    def process_hist_internal(self, buyoperations, cur_action, partial_symbols_update, splits, maxsplit):
        def calc_splited(sym,last_time, time):
            def upd_spl():
                #we want to progress splits if we can here 
                try:
                    next_one = next(iter(splits[sym]))
                    if next_one > time:
                        return False
                except StopIteration:
                    cur_split[sym] = None
                    return False

                cur_split[sym] = splits[sym].popitem(False) if len(splits[sym]) != 0 else None
                _cur_split_updated_for_stock[sym] = False 
                if cur_split[sym] is not None:
                    _cur_splited_bystock[sym] *= cur_split[sym][1]
                    return True
                return False
            #we want to be after last_time and before time but it is NOT! ok to go past time
            # cur_split[sym] represent the last split that happened before time. 
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



            while cur_split[sym] and (cur_split[sym][0] > last_time)  and cur_split[sym][0] <= time and not _cur_split_updated_for_stock[sym]:
                logging.debug((f"{sym} splited between {last_time} and {time} updating {cur_split[sym]}"))
                if not config.TransactionHandlers.ReadjustJustIB:
                    _cur_holding_bystock[sym] = _cur_holding_bystock[sym] * cur_split[sym][1]
                    _cur_avg_cost_bystock[sym] = _cur_avg_cost_bystock[sym] / cur_split[sym][1]
                    _cur_split_updated_for_stock[sym]=True
                    
                if not upd_spl():
                    break
                logging.debug(f"new avg cost {sym} {_cur_avg_cost_bystock[sym]}  cur_hold {_cur_holding_bystock[sym]}")
            #here we passed time and updated splits.


        def update_curholding():
            nonlocal  _cur_avg_cost_bystock_adjusted
            x: BuyDictItem = cur_action[1]

            stock = x.Symbol
            currency_val = 1/cur_action[2] if cur_action[2] is not None else 1 #adjusted is in usd. so we cancel out the currency
            #if stock is in TrackStockList , write to log state in terms of holding before and after transaction is applied


            if partial_symbols_update and stock not in partial_symbols_update:
                return


            cursplit = maxsplit[stock] / _cur_splited_bystock[stock]

            old_cost = _cur_avg_cost_bystock[stock]
            old_cost_adjusted = _cur_avg_cost_bystock_adjusted[stock]
            old_holding = _cur_holding_bystock[stock]
            old_holding_reflected = old_holding * cursplit

            old_cost_reflected= _cur_avg_cost_bystock_reflected_splits[stock]
            old_cost_reflected_adjusted= _cur_avg_cost_bystock_reflected_splits_adjusted[stock]
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
                    refnum= orgcost if config.Input.PricesAreAdjustedToToday else x.Cost
                    if _cur_stock_price[stock][0] and  abs(refnum/_cur_stock_price[stock][0] -1)>0.3:
                        logging.warn("Very different price")

                    self.transaction_handler.update_buydic(cur_action[0], val=x)
            if (cursplit !=1 ):
                self.transaction_handler.update_buydic(cur_action[0], val=x._replace(AdjustedPrice = x.Cost / cursplit ))

            #no more replaces from here 
            qty= x.Qty 
            cost= x.Cost

            currecncy_factor=self._data.get_currency_factor_for_sym(stock)


            costadj = x.Cost / currecncy_factor
                #Currencies such as ILS has their cost in agorot (1/100 of shekel) .

            if qty*old_holding >= 0: #we increase our holding.
                _cur_avg_cost_bystock[stock] = (old_holding * old_cost + qty * cost) / (
                            old_holding + qty)
                _cur_avg_cost_bystock_reflected_splits[stock] = (old_holding_reflected * old_cost_reflected + qty * cost / cursplit) / (
                            old_holding_reflected + qty)
                if x.Symbol not in self._data._no_adjusted_for and currency_val:
                    _cur_avg_cost_bystock_reflected_splits_adjusted[stock] = (old_holding_reflected * old_cost_reflected_adjusted + qty * costadj * currency_val / cursplit) / (
                                old_holding_reflected + qty)
                    _cur_avg_cost_bystock_adjusted[stock] = (old_holding * old_cost_adjusted + qty * costadj * currency_val) / (
                    old_holding + qty)


            else:
                if abs(int(x.Qty))>abs(int(old_holding)): #we switch to the other side. so we do selling of old_holding, and buying on the other
                    _cur_relprofit_bystock[stock] += old_holding * (
                            cost - _cur_avg_cost_bystock[stock]) / currecncy_factor #sell full

                    _cur_avg_cost_bystock[stock] = cost
                    _cur_avg_cost_bystock_reflected_splits[stock] = (cost/ cursplit)#* ( -1 if qty< 0 else 1) #-905 if neg
                    if x.Symbol not in self._data._no_adjusted_for and currency_val:
                        _cur_avg_cost_bystock_reflected_splits_adjusted[stock] = (cost/ cursplit)* currency_val #* ( -1 if qty< 0 else 1) #-905 if neg
                        _cur_avg_cost_bystock_adjusted[stock] = cost* currency_val



                else:
                    _cur_relprofit_bystock[stock] += ((-1)*int(x.Qty)) * (
                            cost - _cur_avg_cost_bystock[stock]) / currecncy_factor # We adjust relprofit at the end by the constant value of base currency
                    if int(x.Qty)== int(old_holding):
                        _cur_avg_cost_bystock[stock] = 0
                        _cur_avg_cost_bystock_adjusted[stock] = 0

            _cur_holding_bystock[stock] += qty
            _cur_accumative_holding_bystock[stock] += abs(qty)

            _last_action_time[stock]=cur_action[0]
            if _first_action_time[stock] is None:
                _first_action_time[stock]=cur_action[0]

            if _cur_holding_bystock[stock] < 0:
                logging.warn((log_conv(' sell below zero', stock, cur_action[0],cur_action[1])))
                if 0:
                    self._transaction_handler.try_fix_dic(cur_action.buydic,_last_action[stock], _cur_holding_bystock[stock] )
            if stock in config.TransactionHandlers.TrackStockDict:
                InputProcessor.log_info(
                x, 
                t, 
                stock, 
                _cur_holding_bystock[stock], 
                _cur_avg_cost_bystock[stock], 
                    _cur_avg_cost_bystock_adjusted[stock],
                cursplit, 
                _cur_relprofit_bystock[stock], 
                _cur_unrelprofit_bystock[stock], 
                _cur_unrelprofit_bystock_adjusted[stock], 
                _cur_avg_cost_bystock_reflected_splits[stock], 
                _cur_avg_cost_bystock_reflected_splits_adjusted[stock], 
                _cur_stock_price[stock][0], 
                _cur_stock_price[stock][1],currency_val
            )
        self._data.mindate = min(
            self._data._hist_by_date.keys())  # datetime.datetime.fromtimestamp(min(self._data._hist_by_date.keys())/1000,tz)
        self._data.maxdate = max(
            self._data._hist_by_date.keys())  # datetime.datetime.fromtimestamp(max(self._data._hist_by_date.keys())/1000,tz)

        _cur_splited_bystock = defaultdict(lambda:1)
        _cur_split_updated_for_stock = defaultdict(lambda:False ) # if we already updated holding for stock
        _cur_avg_cost_bystock = defaultdict(lambda: 0)
        _cur_avg_cost_bystock_adjusted = defaultdict(lambda: 0)
        _cur_avg_cost_bystock_reflected_splits = defaultdict(lambda: 0) #adjust the splits to today
        _cur_avg_cost_bystock_reflected_splits_adjusted = defaultdict(lambda: 0) #adjust the splits to today
        _cur_holding_bystock = defaultdict(lambda: 0)
        _cur_relprofit_bystock = defaultdict(lambda: 0)
        _cur_unrelprofit_bystock = defaultdict(lambda: 0)
        _cur_unrelprofit_bystock_adjusted = defaultdict(lambda: 0)
        _cur_stock_price = defaultdict(lambda: (numpy.NaN, numpy.NaN))
        _last_action_time = defaultdict(lambda: None)
        _first_action_time = defaultdict(lambda: None)
        cur_split = defaultdict(lambda: None)
        cursplit = 1
        _last_action = defaultdict(lambda: None)
        _cur_accumative_holding_bystock = defaultdict(lambda: 0) #just used to calculate the total holding involved
        if len(self._data._simp_hist_by_date)==0 and (not partial_symbols_update):
            logging.warn(("WARNING: No History at all!"))
            return
        hh = pytz.UTC  # timezone('Israel')
        #copy to temporary var and restore at the end
        from_date ,to_date = self.process_params.transactions_fromdate, self.process_params.transactions_todate

        self.process_params.transactions_todate = localize_it(self.process_params.transactions_todate)
        self.process_params.transactions_fromdate = localize_it(self.process_params.transactions_todate)
        try:
            if not partial_symbols_update:
                self._data._fset=set()
            simphist=iter(sorted(self._data._simp_hist_by_date.items()))
            t=1

            dic={}
            while cur_action or t:
                try:
                    t, dic = next(simphist)
                    t = localize_it(t)
                    mini=False
                    if self.process_params.transactions_todate and t > self.process_params.transactions_todate:
                        raise StopIteration()
                except StopIteration:
                    logging.log(TRACELEVEL,("stop iter"))
                    if len(buyoperations)>0:
                        _ , cur_action = buyoperations.popitem(False)
                        t=cur_action[0]
                        t = localize_it(t)
                        if t> self.process_params.transactions_todate:
                            break
                        mini=True
                    else:
                        break





                if partial_symbols_update:
                    dic = dictfilt(dic, partial_symbols_update)

                #t=tzawareness(t,self.process_params.transactions_todate)



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
                    _, cur_action = buyoperations.popitem(False)

                tim = matplotlib.dates.date2num(t)
                holdopt = set(_cur_holding_bystock.keys()).intersection(
                    partial_symbols_update) if partial_symbols_update else _cur_holding_bystock.keys()
                for sym in holdopt:
                    if partial_symbols_update and not sym in partial_symbols_update:
                        continue
                    self._data._holding_by_stock[sym][tim] = _cur_holding_bystock[sym]
                    self._data._rel_profit_by_stock[sym][tim] = _cur_relprofit_bystock[sym]
                    self._data._avg_cost_by_stock[sym][tim] = _cur_avg_cost_bystock[sym]
                    if sym not in self._data._no_adjusted_for:
                        self._data._avg_cost_by_stock_adjusted[sym][tim] = _cur_avg_cost_bystock_reflected_splits[
                            sym] if config.Input.AdjustUnrelProfitToReflectSplits else _cur_avg_cost_bystock_adjusted[sym]
                    elif self.trivial_currency(sym):
                        self._data._avg_cost_by_stock_adjusted[sym][tim] =_cur_avg_cost_bystock[sym]

                    self._data._split_by_stock[sym][tim] = _cur_splited_bystock[sym]
                if mini:
                    continue
                symopt = self._data._usable_symbols.intersection(
                    partial_symbols_update) if partial_symbols_update else self._data._usable_symbols
                for sym in symopt:
                    if partial_symbols_update and not sym in partial_symbols_update:
                        continue
                    if sym in dic:
                        v = dic[sym]
                    else:
                        v = _cur_stock_price[sym]  # actually, should fix for currency. but doesn't matter


                    currecncy_factor = self._data.get_currency_factor_for_sym(sym)

                    self._data._alldates[sym][tim] = v[0]
                    self._data._alldates_adjusted[sym][tim]=v[1]
                    _cur_stock_price[sym] = v
                    #v = v[0]
                    self._data._value[sym][tim] = v[0] * _cur_holding_bystock[sym] / currecncy_factor
                    self._data._adjusted_value[sym][tim] = v[1] * _cur_holding_bystock[sym]
                    if config.Input.AdjustUnrelProfitToReflectSplits:
                        cursplit = maxsplit[sym] / _cur_splited_bystock[sym]
                        _cur_unrelprofit_bystock[sym]= (v[0] - _cur_avg_cost_bystock_reflected_splits[sym]) * _cur_holding_bystock[sym]*cursplit / currecncy_factor
                        if sym not in self._data._no_adjusted_for:
                            _cur_unrelprofit_bystock_adjusted[sym] = (v[1] * _cur_holding_bystock[sym] - \
                                                                    _cur_holding_bystock[sym] * \
                                                                    _cur_avg_cost_bystock_reflected_splits_adjusted[sym])
                        elif self.trivial_currency(sym):
                            _cur_unrelprofit_bystock_adjusted[sym] = _cur_unrelprofit_bystock[sym]


                    else:
                        _cur_unrelprofit_bystock[sym]= (v[0] - _cur_avg_cost_bystock[sym]) * _cur_holding_bystock[sym] / currecncy_factor
                        if sym not in self._data._no_adjusted_for:
                            _cur_unrelprofit_bystock_adjusted[sym] = ((v[1] * _cur_holding_bystock[sym]) - \
                                                                      (_cur_holding_bystock[sym] * _cur_avg_cost_bystock_adjusted[sym]) )
                        elif self.trivial_currency(sym):
                            _cur_unrelprofit_bystock_adjusted[sym] = _cur_unrelprofit_bystock[sym]






                    self._data._unrel_profit[sym][tim] = _cur_unrelprofit_bystock[sym]
                    self._data._unrel_profit_adjusted[sym][tim] = _cur_unrelprofit_bystock_adjusted[sym]


                    self._data._tot_profit_by_stock[sym][tim] = self._data._rel_profit_by_stock[sym][tim] + self._data._unrel_profit[sym][tim]
                    if t.date() in  selfifnn(config.TransactionHandlers.TrackStockDict.get(sym),[]):
                        InputProcessor.log_info(
                            '', 
                            t, 
                            sym, 
                            _cur_holding_bystock[sym], 
                            _cur_avg_cost_bystock[sym], 
                            _cur_avg_cost_bystock_adjusted[sym],
                            cursplit, 
                            _cur_relprofit_bystock[sym], 
                            _cur_unrelprofit_bystock[sym], 
                            _cur_unrelprofit_bystock_adjusted[sym], 
                            _cur_avg_cost_bystock_reflected_splits[sym], 
                            _cur_avg_cost_bystock_reflected_splits_adjusted[sym], 
                            _cur_stock_price[sym][0], 
                            _cur_stock_price[sym][1],
                            neverthrow(lambda: self.currency_on_date(t,sym,True)[0]),
                        )
                    _last_action[sym] = cur_action
                self._data._fset.add(tim)
            if not partial_symbols_update:
                self.update_current_status(
                    {"Holding" : _cur_holding_bystock,
                     "Unrealized profit": _cur_unrelprofit_bystock,
                     "Unrealized profit in base": _cur_unrelprofit_bystock_adjusted,
                     "Realized  profit":  _cur_relprofit_bystock,
                     "AccumulatedHolding": _cur_accumative_holding_bystock,
                     "Average Cost": _cur_avg_cost_bystock,
                     'First Action': {x:  pd.to_datetime(y) for x,y in _first_action_time.items()},
                     'Last Action': {x: pd.to_datetime(y)  for x,y in  _last_action_time.items()}

                })
                self._cur_splits=_cur_splited_bystock
            a=1
            logging.debug(f"process ended at {t}")
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

        self._data._current_status= st

    def get_portfolio_stocks(self):
        if self._data._current_status is None:
            return set()
        return set(self._data._current_status[ self._data._current_status['Holding']!=0].index)








    def simplify_hist(self, partial_symbols_update):
        #very not efficient, can be rewritten. Still fast enough.
        self._data._simp_hist_by_date = collections.OrderedDict()
        for date, symdic in self._data._hist_by_date.items():
            for s, (dica, dicb) in symdic.items():
                if partial_symbols_update and s not in partial_symbols_update:
                    continue
                if not date in self._data._simp_hist_by_date:
                    self._data._simp_hist_by_date[date] = {}
                adjust = ifnn(dicb, lambda: (dicb['Close'] + dicb['Open']) / 2,
                              lambda: (dica['Close'] + dica['Open']) / 2)
                self._data._simp_hist_by_date[date][s] = ((dica['Close'] + dica['Open']) / 2, adjust)

    def get_status_for_cur(self,stock):
        dic= self._data._alldates

        def get_for(dic):
            fromdate = matplotlib.dates.num2date(min(dic.keys()) )
            todate = matplotlib.dates.num2date(max(dic.keys()) )
            range_gaps= list(self.get_range_gap( [  matplotlib.dates.num2date(k) for k,v in dic.items() if (( v is not None ) and (not math.isnan(v)))  ],fromdate,todate))
            yield fromdate, range_gaps[0][0]
            for a,b  in zip(range_gaps,range_gaps[1:]):
                yield a[1],b[0]
            yield range_gaps[-1][1],todate
        return list(get_for(dic[stock]))

    def get_stock_indate(self,stock,indate):
        indate= matplotlib.dates.date2num(indate)
        dic= self._data._alldates[stock]
        if indate in dic:
            return dic[indate]
        else:
            return None





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
    def _save_data(self):
        try:
            self._proccessing_mutex.lock() #only protects adjust. TODO: new mutex for save
            self._data.save_full_data()
        finally:
            self._proccessing_mutex.unlock()
    
    def save_data(self):
        if not config.Input.SaveData:
            logging.debug('not saving data because of config')
            return
        logging.debug('saving data')
        self._data.save_data()
        if config.Input.FullCacheUsage != UseCache.DONT or config.Input.AlwaysStoreFullCache:
            self._save_data_proc.command.emit(TaskParams(params=tuple()))



    def get_data_from_source(self, partial_symbols_update,fromdate,todate):
        if self._InputSource is None:
            return False





        self._data.symbol_info_tmp={}

        if not partial_symbols_update:
            self._data._usable_symbols = set()
            self._data._bad_symbols = set()
            self._data._hist_by_date = collections.OrderedDict()  # like all dates but by
        else:
            self._data._bad_symbols=self._data._bad_symbols - set(partial_symbols_update) #meaning we don't ignore symbols here , even if before they were bad

        todate = todate if todate is not None else datetime.datetime.now()

        todate = localize_it(todate)

        fromdate = localize_it(fromdate)

        successful_once=False
        if fromdate==todate:
            raise Exception("identical dates")
        for sym in list(self._data._symbols_wanted if not partial_symbols_update else partial_symbols_update):

            sym_corrected = self.process_params.resolve_hack.get(sym, None)
            if not sym_corrected:
                sym_corrected = config.Symbols.Translatedic.get(sym, sym)


            if not self._force_upd_all_range and sym in self._data._hist_by_date:
                init_keys=  filter (lambda x : ((y:=localize_it(x))>= fromdate and y<=todate) ,self._data._hist_by_date.keys() )
                if sym in self._data._no_adjusted_for:
                    cond= lambda x: not math.isnan(x[0].get('Open'))
                else:
                    cond = lambda x: not math.isnan(x[0].get('Open')) and not math.isnan(x[1].get('Open'))
                dates= (date for date in init_keys if ifnotnan(self._data._hist_by_date[date].get(sym),cond ))
                ls = self.get_range_gap(dates,fromdate,todate) #we have data for this symbol
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
            if okdays==0 or requireddays/okdays<0.5:
                logging.debug(f'mostly problematic {sym} {okdays}/{requireddays}')
        return successful_once


    def get_hist_sym(self,mindate, maxdate, sym, sym_corrected):
        if self._InputSource is None:
            return 0
        logging.debug((f'getting symbol hist for {sym} ({sym_corrected}) from {mindate} to {maxdate}'))
        #self._InputSource.ownership()
        l, hist = self._InputSource.get_symbol_history(sym_corrected, mindate, maxdate,
                                                       iscrypto= (str(sym_corrected) in config.Symbols.Crypto))  # should be rounded

        self._data.symbol_info[sym] = (l if l else {}) #just for debug I think
        if (cont := self._data.symbol_info[sym].get('contract')):
            logging.debug(f"resolved {sym} is {cont}")
        if hist is None:
            raise SymbolError("bad symbol")
        elif len(hist)==0:
                raise SymbolError("empty history")
        else:
            logging.debug(f"got history for {sym} {hist.index.min()} {hist.index.max()}")


        if l is None:
            logging.warn("no info for %s , using default " % sym)
            currency =  'unk'
        elif not (sym in self._data.symbol_info and ('currency' in self._data.symbol_info[sym] ) and self._data.get_currency_for_sym(sym)) :
            currency = self.resolve_currency(sym, l, hist)
            self._data.symbol_info[sym].update( {'currency': currency})
        else:
            currency= self._data.get_currency_for_sym(sym)

        if currency != config.Symbols.Basecur and currency != 'unk':
            adjusted =  self.get_adjusted_df_for_currency(currency, maxdate, mindate, hist, sym)
        else:
            adjusted=None

        hist = hist.to_dict('index')
        if adjusted is not None:
            adjusted = adjusted.to_dict('index')
        okdays = sum([1 for d in hist.values() if not math.isnan(d['Open'])])

        self._data._usable_symbols.add(sym)
        for date, dic in hist.items():
            from pandas import Timestamp 
            date=Timestamp(date.date())
            if not date in self._data._hist_by_date:
                self._data._hist_by_date[date] = {}

            self._data._hist_by_date[date][sym] = (dic, adjusted.get(date) if adjusted else None)  #We will fill it anyway in simp_hist
        return okdays

    def convert_dicts_to_df_and_add_earnings(self,partial_symbols_update):
        dataframes = []

        NONADJUSTEDDICTS= len(self._data.dicts) -2
        # no more dicts #we removed alldatesadjusted from dicts..
        seldict= self._data.dicts[:NONADJUSTEDDICTS]

        try:

            #income, revenue, cs =# get_earnings()
            raise Exception("no earnings for now")
            #income, revenue, cs = #EarningProcessor()
            hasearnings=True
            combinedindex = sorted(
                list(set(self._data._fset).union(set(cs.index)).union(set(income.index)).union(set(revenue.index))))
        except:
            logging.warn(('earning reading failed'))
            # import traceback
            # traceback.print_exc()
            hasearnings = False
            combinedindex=sorted(list(self._data._fset))


        for name, dic in zip(self.dicts_names,seldict):
            df = pd.DataFrame(dic, index=combinedindex)
            if name=='alldates':
                df = df.fillna(method='ffill', axis=0)
            #df = pd.DataFrame(dic,index=sorted(list(self._data._fset)))
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

        self._data._reg_panel = pd.concat(dataframes,axis=1)

    @staticmethod
    def return_df(df, cur,CommonStock_df,name):
        cur.sort_index(axis=0, inplace=True)
        cur=cur.reindex(sorted(list(df.index)),method='pad')
        CommonStock_df.sort_index(axis=0,inplace=True)
        CommonStock_df=CommonStock_df.reindex(df.index,method='pad')
        eps= cur.divide(CommonStock_df)
        cur= df[cur.columns].divide(eps) #pr ps / eps = price / earnings
        cur.columns = pd.MultiIndex.from_product([[name], list(cur.columns)], names=['Name', 'Symbols'])
        return cur





    def get_relevant_currency(self,x):
        if self._InputSource is None:
            return
        if x not in self._relevant_currencies_rates:
            self._relevant_currencies_rates[x] = self._InputSource.get_current_currency((config.Symbols.Basecur, x))
        return  self._relevant_currencies_rates[x]

    @simple_exception_handling("adjusting for currency", return_succ=0)
    def adjust_for_currency(self):
        a=1 #updates adjusted panel
        cursymdic={ config.Symbols.TranslateCurrency.get(curr:=v.get('currency', 'unk'),curr) :k for k,v in self._data.symbol_info.items() if not (v is None)}

        relevant_currencies = set(cursymdic.keys()) - \
                              set(['unk', config.Symbols.Basecur])

        if self._relevant_currencies_time is not None and (datetime.datetime.now() - self._relevant_currencies_time) < config.Input.MaxRelevantCurrencyTime:
            logging.debug('Using cached relevant currencies {}'.format(self._relevant_currencies_time))

        upd= False
        if self._InputSource is not None:
            for x in relevant_currencies:
                self._relevant_currencies_rates[x] = ifnotnan(self._InputSource.get_current_currency((config.Symbols.Basecur, x)),lambda t:1/t)
                upd = upd or (self._relevant_currencies_rates[x] is not None)




        if upd:
            self._relevant_currencies_time = datetime.datetime.now()

        for x,v in self._relevant_currencies_rates.items():
            if v is None:
                sym=cursymdic[x]

                with SimpleExceptionContext(f'getting currency {x} {sym} from heuristic',detailed=False,never_throw=True):
                    m= max(list(self._data._alldates_adjusted[sym].keys())) #can fail if empty
                    if (subdates(datetime.datetime.now(),matplotlib.dates.num2date(m))) < config.Input.MaxRelevantCurrencyTimeHeur:
                        logging.debug(f'Using heuristic for currency {x} {sym}')
                        self._relevant_currencies_rates[x]=self._data._alldates_adjusted[sym][m]/self._data._alldates[sym][m]







        #fix the following line for case 'currency' is not in dictonary of value v of _data.symbol_info
        dic={k: self._relevant_currencies_rates.get(curr) for k in self._data.symbol_info.keys()
             if (curr:=self._data.get_currency_for_sym(k) ) in self._relevant_currencies_rates \
             and self._relevant_currencies_rates[curr] is not None}
        #dic={k:self._relevant_currencies_rates[v['currency']] for k,v in self._data.symbol_info.items() if ifnn(v,lambda : v['currency']!=config.Symbols.Basecur  and (v['currency'] in self._relevant_currencies_rates))}
        if len(dic)==0:
            return False
        self._data._adjusted_panel=self.build_adjust_panel(dic)
        return True

    def build_adjust_panel(self, currency_dict):
        def return_subpanel(df_name, dic):
            ndf = pd.DataFrame.from_dict(dic)
            ndf.columns = pd.MultiIndex.from_product(
                [[df_name], list(ndf.columns)], names=['Name', 'Symbols'])
            return ndf

        relevant = set(lmap(lambda x: x[1], self._data._reg_panel.columns)).intersection(
            set(currency_dict.keys()))

        currency_symbols_multiIndex = pd.MultiIndex.from_product(
            [SymbolsInterface.TOADJUST, relevant], names=['Name', 'Symbols'])
        if len(currency_symbols_multiIndex) == 0:
            logging.debug('no symbols to adjust')
            return False

        adjusted_currency_df = pd.DataFrame(
            index=self._data._reg_panel.index, columns=currency_symbols_multiIndex)
        for x in SymbolsInterface.TOADJUST:
            for key, value in currency_dict.items():
                adjusted_currency_df.loc[:, (x, key)] = currency_dict[key]

        adjusted_reg_panel_df = pd.DataFrame(
            index=self._data._reg_panel.index, columns=self._data._reg_panel.columns)
        for x in SymbolsInterface.TOKEEP:
            if x in self._data._reg_panel:
                adjusted_reg_panel_df[x] = self._data._reg_panel[x].copy()

        df1 = self._data._reg_panel[currency_symbols_multiIndex]
        cols_to_multiply = df1.columns.intersection(adjusted_currency_df.columns)
        adjusted_reg_panel_df[cols_to_multiply] = df1[cols_to_multiply].mul(
            adjusted_currency_df[cols_to_multiply])

        adjusted_reg_panel_df = adjusted_reg_panel_df[[(
            c, d) for (c, d) in self._data._reg_panel.columns if c not in SymbolsInterface.TOADJUSTLONG]]
        value_panel = return_subpanel('value', self._data._adjusted_value)
        date_adjusted_panel = return_subpanel('alldates', self._data._alldates_adjusted)
        unrel_profit_panel = return_subpanel('unrel_profit', self._data._unrel_profit_adjusted)
        avg_cost_panel = return_subpanel('avg_cost_by_stock', self._data._avg_cost_by_stock_adjusted)

        adjusted_reg_panel_df['rel_profit_by_stock'] = adjusted_reg_panel_df['rel_profit_by_stock'].fillna(0)
        total_profit_df = adjusted_reg_panel_df['rel_profit_by_stock'] + unrel_profit_panel['unrel_profit']
        total_profit_df.columns = pd.MultiIndex.from_product(
            [['tot_profit_by_stock'], list(total_profit_df.columns)], names=['Name', 'Symbols'])
        concatenated_df = pd.concat(
            [adjusted_reg_panel_df, total_profit_df, value_panel, avg_cost_panel, date_adjusted_panel, unrel_profit_panel], axis=1)
        return concatenated_df #set(lmap(lambda x: x[0], adjusted_reg_panel_df.columns))


    def filter_input(self,keys):

        for x in self._data.dicts:
            for k in keys:
                x.pop(str(k),'')

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
        callback = lambda e: self._eng.statusChanges.emit(f'Exception in processing {e}')
        with SimpleExceptionContext('exception in processing',callback=callback):
            ret=self.process_internal(ls)
            logging.debug(f"process end {ret}")
            return ret




    def process_internal(self, partial_symbol_update):
        t = time.process_time()
        fastway = False
        firsttime=self.data is None
        if firsttime:
            self.data = InputDataImpl.full_data_load()
            if self._data.fullcachedate:
                self.process_transactions() #not strictly needed. Can be done in parallel
                if self.transaction_handler.need_to_save:
                    logging.debug("new transactions since last cache , not fast-way")
                    self.data = InputDataImpl()
                    fastway =False #We process transactions again. That can be done
                else:
                    self._initial_process_done = True
                    self.convert_dicts_to_df_and_add_earnings(False) #no need to lock
                    fastway = True
                    ret=True
                    logging.info("processed fast-way")


        if not self._initial_process_done:
            self._data.load_cache(True)

            self.process_transactions()
            self._initial_process_done = True
        if not fastway:
            elapsed_time = time.process_time() - t
            logging.debug(('elasped populating : %s' % elapsed_time))
            if not partial_symbol_update:
                self.used_unitetype = self.process_params.unite_by_group
                required = set(self._eng.required_syms(True, True))
                if config.Input.DownloadDataForProt:
                    self._data._symbols_wanted = self._transaction_handler.buysymbols.union(required)  # there are symbols to check...
                else:
                    self._data._symbols_wanted = required.copy()
            else:
                self._data._symbols_wanted.update(
                    partial_symbol_update)  # will try also the symbols wanted. That are generally only updated first..
                #so symbol_wanted is incremental list . Interesting.
            t = time.process_time()
            ret= self.process_history(partial_symbol_update)
            if firsttime:
                self.save_data()
        # do some stuff
        elapsed_time = time.process_time() - t
        logging.debug(('elasped : %s' % elapsed_time))


        return ret

    @simple_exception_handling(err_description="error in process transactions")
    def process_transactions(self):
        self._transaction_handler.process_transactions()
    #self._proccessing_mutex.unlock()



