from common.better_abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

from input.inputdatainterface import InputDataImplInterface

@dataclass 
class InputPosition:
    symbol : str
    position : float
    avgCost : float
    contract : Optional[Dict]
    currency: str


class InputProcessorInterface(metaclass=ABCMeta):

    @abstractmethod
    def complete_status(self):
        pass

    @abstractmethod
    def get_currency_hist(self, currency, fromdate, enddate):
        pass

    @abstractmethod
    def process(self, partial_symbol_update, params, buy_filter):
        pass

    @abstractmethod
    def trivial_currency(self, sym):
        pass

    @abstractmethod
    def resolve_currency(self, sym, l, hist):
        pass

    @abstractmethod
    def get_currency_hist(self, currency, fromdate, enddate, minimal, queried):
        pass

    @abstractmethod
    def get_portfolio_stocks(self):
        pass

    @abstractmethod
    def get_relevant_currency(self, x):
        pass

    @abstractmethod
    def adjust_for_currency(self):
        pass

    @abstractmethod
    def process(self, partial_symbol_update, params, buy_filter, force_upd_all_range):
        pass

    @property
    @abstractmethod
    def _data(self) -> InputDataImplInterface:
        pass
