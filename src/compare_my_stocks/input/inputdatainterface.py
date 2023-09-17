from pandas import DataFrame
from common.better_abc import ABCMeta, abstract_attribute 
from abc import abstractmethod


class InputDataImplInterface(metaclass=ABCMeta):
    @abstract_attribute
    def _reg_panel(self) -> DataFrame:
        ...
    @abstract_attribute
    def _adjusted_panel(self) -> DataFrame:
        ...
    @abstract_attribute
    def _bad_symbols(self):
        ...
    @abstract_attribute
    def mindate(self):
        ...
    @abstract_attribute
    def maxdate(self):
        ...
    @abstract_attribute
    def _usable_symbols(self):
        ...
    @abstract_attribute
    def _symbols_wanted(self):
        ...
    @abstract_attribute
    def symbol_info(self):
        ...
    @abstract_attribute
    def cached_used(self):
        ...
    @abstract_attribute
    def _current_status(self) -> DataFrame:
        ...
    @abstract_attribute
    def _no_adjusted_for(self):
        ...
    @abstract_attribute
    def fullcachedate(self):
        ...
    @abstract_attribute
    def _fset(self):
        ...
    @abstract_attribute
    def currency_hist(self) -> DataFrame:
        ...
    @abstract_attribute
    def _err_transactions(self):
        ...



    @classmethod
    @abstractmethod
    def full_data_load(self):
        ...

    @abstractmethod
    def load_cache(self, minimal, process_params):
        ...

    @abstractmethod
    def get_currency_factor_for_sym(self, sym):
        ...

    @abstractmethod
    def get_currency_for_sym(self, sym, real_one=False):
        ...

    @abstractmethod
    def save_data(self):
        ...
