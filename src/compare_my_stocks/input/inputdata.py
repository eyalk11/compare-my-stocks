import collections
import datetime
import logging
import pickle
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List

import numpy
import pandas

from common.common import UseCache, log_conv, VerifySave
from common.simpleexceptioncontext import print_formatted_traceback
from compare_my_stocks.common.common import ifnn
from compare_my_stocks.common.simpleexceptioncontext import SimpleExceptionContext
from config import config


class InputData(ABC):
        @property
        @abstractmethod
        def tot_profit_by_stock(self):
            ...
        def value(self):
            ...
        @property
        @abstractmethod
        def alldates(self):
            ...
        @property
        @abstractmethod
        def holding_by_stock(self):
            ...
        @property
        @abstractmethod
        def rel_profit_by_stock(self):
            ...
        @property
        @abstractmethod
        def unrel_profit(self):
            ...
        @property
        @abstractmethod
        def avg_cost_by_stock(self):
            ...


class InputDataImpl:
    def __init__(self):
        self._reg_panel=None
        self._adjusted_panel=None
        self._bad_symbols = set()
        self.mindate = None
        self.maxdate = None
        self._usable_symbols = set()
        self._symbols_wanted = set()
        self.symbol_info = collections.defaultdict(lambda:dict())
        self.cached_used = None
        self._current_status = None
        self._no_adjusted_for=set()
        self.init_input()
        self.fullcachedate =None
        self._fset = set()
        self.currency_hist = None
    @staticmethod
    def init_func():
        return defaultdict(InputDataImpl.returnNan)
    @staticmethod
    def returnNan():
        return numpy.NaN

    @staticmethod
    def init2():
        return defaultdict(InputDataImpl.retone)
    @staticmethod
    def retone():
        return 1

    def init_input(self):
        #todo: make dataframe... but it is 3d...
        self._alldates = defaultdict(InputDataImpl.init_func)
        self._alldates_adjusted= defaultdict(InputDataImpl.init_func)
        self._adjusted_value = defaultdict(InputDataImpl.init_func)
        self._unrel_profit = defaultdict(InputDataImpl.init_func)
        self._value = defaultdict(InputDataImpl.init_func)  # how much we hold
        self._avg_cost_by_stock = defaultdict(InputDataImpl.init_func)  # cost per unit
        self._rel_profit_by_stock = defaultdict(InputDataImpl.init_func)  # re
        self._tot_profit_by_stock = defaultdict(InputDataImpl.init_func)
        self._holding_by_stock = defaultdict(InputDataImpl.init_func)
        self._unrel_profit_adjusted = defaultdict(InputDataImpl.init_func)
        self._split_by_stock = defaultdict(InputDataImpl.init2)
        self._avg_cost_by_stock_adjusted = defaultdict(InputDataImpl.init_func)
    @property
    def dicts(self) -> List:
        """doc"""
        return [self._alldates, self._unrel_profit, self._value, self._avg_cost_by_stock,
                      self._rel_profit_by_stock, self._tot_profit_by_stock, self._holding_by_stock,
                      self._alldates_adjusted,self._unrel_profit_adjusted]


    @classmethod
    def full_data_load(self):
        if config.Input.FULLCACHEUSAGE == UseCache.DONT:
            return InputDataImpl()  
        try: 
            cache_date , cls =  pickle.load(open( config.File.FULLDATA ,'rb'))
            if ((cache_date - datetime.datetime.now() > config.Input.MAXFULLCACHETIMESPAN) and config.Input.FULLCACHEUSAGE == UseCache.USEIFAVALIABLE):
                logging.info('Full data cache too old') 
                return InputDataImpl() 

            logging.info(f"Loaded and used fulldata cache: {cache_date}")
            cls.fullcachedate = cache_date 
            return cls
             

        except Exception as e:
            logging.warn((f'failed to use fulldata  cache {e}'))
            return InputDataImpl()

        
    def save_full_data(self):
        #add elapsed time
        import time
        t= time.process_time()

        with SimpleExceptionContext(err_description="save full data",detailed=False):  
            pickle.dump((datetime.datetime.now(),self),open(config.File.FULLDATA,'wb'))
            elapsed_time = time.process_time() - t
            logging.info(f"Saved fulldata cache: {datetime.datetime.now()} Took {elapsed_time}")

            self.fullcachedate = datetime.datetime.now()

    def load_cache(self,minimal=False,process_params=None):
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

            # not minimal

            hist_by_date, _ , self._cache_date,self.currency_hist,_ = pickle.load(open(config.File.HIST_F, 'rb'))

            if type(self.currency_hist) == dict: # backward compatability
                self.currency_hist = pandas.DataFrame(self.currency_hist)

            if self._cache_date - datetime.datetime.now() < config.Input.MAXCACHETIMESPAN or process_params.use_cache == UseCache.FORCEUSE:
                logging.info(f"Loaded and used cache: {self._cache_date}")
                self._hist_by_date = hist_by_date
                self.cached_used = True
            else:
                logging.info(f"Cache not used {self._cache_date}  {process_params.use_cache}")
                self.cached_used = False
            #log the current hist_by_date status, include max date,min date,num of entries
            logging.debug((f'hist_by_date status: max date {max(self._hist_by_date.keys())}, min date {min(self._hist_by_date.keys())}, num of entries {len(self._hist_by_date)}'))



            self.update_usable_symbols()
            logging.debug((f'cache symbols used {sorted(list(self._usable_symbols))}'))
            if not process_params.use_cache == UseCache.FORCEUSE:
                query_source = not (set(self._symbols_wanted) <= set(
                    self._usable_symbols))  # all the buy and required are in there
            else:
                logging.debug((log_conv('using cache anyway', not (set(self._symbols_wanted) <= set(self._usable_symbols)))))
                query_source = False
        except FileNotFoundError:
            logging.warn('No cache file found')
            query_source = True
            self.cached_used=True #lets lie because we don't want verifysave
        except Exception as e:
            e = e
            logging.warn((f'failed to use cache {e}'))
            import traceback;traceback.print_exc()
            if not minimal:
                self.cached_used = False
        return query_source

    def get_currency_factor_for_sym(self,sym):
        currency = self.get_currency_for_sym(sym)
        if currency is None:
            return 1
        currecncy_factor = config.Symbols.CURRENCY_FACTOR.get(currency, 1.0)
        return currecncy_factor
    def get_currency_for_sym(self,sym):
        cur = self.symbol_info[sym].get('currency')
        
        return ifnn(cur, lambda: config.Symbols.TRANSLATE_CURRENCY.get(cur,cur))

    def save_data(self):
        #The difference between the regular cache and fullcache is that fullcache doesn't know how to handle transactions diffs .

        if not self.cached_used:
            logging.warn("Cache wasnt used! (possibly first time)")
            if config.Running.VERIFY_SAVING == VerifySave.DONT:
                logging.warn("Not saving data because not using cache")
                return
            logging.warn("Saving data without using cache! Can earse data!")
            if config.Running.VERIFY_SAVING == VerifySave.Ask :

                x=input('Are you sure you want to? (y to accept)') #TODO: msgbox
                if x.lower()!='y':
                    return


        import shutil
        try:
            shutil.copy(config.File.HIST_F, config.File.HIST_F_BACKUP)
        except:
            logging.debug(('error in backuping hist file'))
        try:
            pickle.dump((self._hist_by_date, dict(self.symbol_info), datetime.datetime.now(), self.currency_hist.to_dict(),
                         None), open(config.File.HIST_F, 'wb'))
            logging.debug(('hist saved'))
        except:
            logging.error(("error in dumping hist"))
            print_formatted_traceback()
        if config.Input.FULLCACHEUSAGE != UseCache.DONT:
            self.save_full_data()

    def update_usable_symbols(self):
        self._usable_symbols = set()
        for t, dic in self._hist_by_date.items():
            self._usable_symbols.update(set(dic.keys()))
