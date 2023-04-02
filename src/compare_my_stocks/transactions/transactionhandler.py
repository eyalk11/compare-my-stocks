import logging

import math
import pickle
from datetime import datetime

import numpy

from common.common import UseCache, simple_exception_handling
from common.loghandler import TRACELEVEL
from config import config,resolvefile
from transactions.transactioninterface import TransactionHandlerInterface,TransactionHandlerImplementator

import dataclasses

class TrasnasctionHandler(TransactionHandlerInterface,TransactionHandlerImplementator):

    def __init__(self,manager):
        self._manager  =manager
        self._buydic = {}
        self._buysymbols = set()
        self._cache_date=None
        self.File=None
        self.Use=None
        self.CacheSpan=None
        self.__dict__.update(dataclasses.asdict(getattr(config.TransactionHandlers,self.NAME)))
        ok,path = resolvefile(self.File)
        if not ok:
            logging.info((f'Cache not found for {self.NAME}'))
        self.File=path


    def get_vars_for_cache(self):
        return []
    def set_vars_for_cache(self,v):
        pass

    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic

    def get_portfolio_stocks(self):  # TODO:: to fix
        return self._buysymbols #[config.TRANSLATEDIC.get(s,s) for s in  self._buysymbols] #get_options_from_groups(self.Groups)

    def update_sym_property(self, symbol, value, prop='currency', updateanyway=True):
        def nanch(x):
            try:
                return math.isnan(x)
            except:
                return False

        if value is numpy.nan:
            value=""
        current=  self._manager.symbol_info.get(symbol)
        if current:

            current=current.get(prop)
        if not current or nanch(current):
            self._manager.symbol_info[symbol][prop] = value
        elif current!=value:
            logging.log(TRACELEVEL,(f'diff {prop} for {symbol} {current} {value}'))
            if updateanyway:
                self._manager.symbol_info[symbol][prop] = value

    @simple_exception_handling("try_to_use_cache",return_succ=True)
    def try_to_use_cache(self):
        v=list(pickle.load(open(self.File, 'rb')))
        if self.save_cache_date():
            self._cache_date=v[0]
            if type(v[0]) is not datetime:
                logging.error("bad cache - not datetime")
                return 0
            if self.Use == UseCache.USEIFAVALIABLE and self.CacheSpan and self._cache_date and datetime.now() - self._cache_date > self.CacheSpan:
                logging.info(("not using after all"))
                return  0
        else:
            return self.set_vars_for_cache(v)
        return self.set_vars_for_cache(tuple(v[1:]))


    def save_cache_date(self):
        return 1

    @simple_exception_handling("save_cache")
    def save_cache(self):
        if not self.File:
            return

        if self.save_cache_date():
            self._cache_date = datetime.now()
            pickle.dump(tuple([self._cache_date] + list(self.get_vars_for_cache())), open(self.File, 'wb'))
        else:
            pickle.dump((self.get_vars_for_cache()), open(self.File, 'wb'))
        logging.debug((f'cache saved {self.NAME}'))

    def process_transactions(self):

        self._buydic = {}
        self._buysymbols = set()

        if  (self.Use is None) or (self.Use and self.Use!=UseCache.DONT):
            if  self.try_to_use_cache():
                logging.debug((f'using buydict cache for {self.NAME}'))
                return


        self.populate_buydic()


        self.save_cache()

