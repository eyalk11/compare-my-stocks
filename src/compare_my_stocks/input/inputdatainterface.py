from pandas import DataFrame
from common.better_abc import ABCMeta, abstract_attribute 
from abc import abstractmethod


class InputDataImplInterface(metaclass=ABCMeta):
    @abstract_attribute
    def _reg_panel(self) -> DataFrame:
        pass
    @abstract_attribute
    def _adjusted_panel(self) -> DataFrame:
        pass
    @abstract_attribute
    def _bad_symbols(self):
        pass
    @abstract_attribute
    def mindate(self):
        pass
    @abstract_attribute
    def maxdate(self):
        pass
    @abstract_attribute
    def _usable_symbols(self):
        pass
    @abstract_attribute
    def _symbols_wanted(self):
        pass
    @abstract_attribute
    def symbol_info(self):
        pass
    @abstract_attribute
    def cached_used(self):
        pass
    @abstract_attribute
    def _current_status(self) -> DataFrame:
        pass
    @abstract_attribute
    def _no_adjusted_for(self):
        pass
    @abstract_attribute
    def fullcachedate(self):
        pass
    @abstract_attribute
    def _fset(self):
        pass
    @abstract_attribute
    def currency_hist(self) -> DataFrame:
        pass
    @abstract_attribute
    def _err_transactions(self):
        pass

    @abstract_attribute
    def _hist_by_date(self):
        pass


    @classmethod
    @abstractmethod
    def full_data_load(self):
        pass

    @abstractmethod
    def load_cache(self, minimal, process_params):
        pass

    @abstractmethod
    def get_currency_factor_for_sym(self, sym):
        pass

    @abstractmethod
    def get_currency_for_sym(self, sym, real_one=False):
        pass

    @abstractmethod
    def save_data(self):
        pass
def might_change_big(func):
    def internal(self,*args,**kwargs):
        self._semaphore.acquire(100)
        try:
            return func(self,*args,**kwargs)
        finally:
            self._semaphore.release(100)
    return internal



def might_change(func):
    def internal(self,*args,**kwargs):
        self._semaphore.acquire()
        try:
            return func(self,*args,**kwargs)
        finally:
            self._semaphore.release()
    return internal
