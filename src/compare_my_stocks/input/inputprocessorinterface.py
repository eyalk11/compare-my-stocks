from abc import ABCMeta, abstractmethod


class InputProcessorInterface():
    @abstractmethod
    def complete_status(self):
        pass

    @abstractmethod
    def get_currency_hist(self, currency, fromdate, enddate):
        pass

    @abstractmethod
    def process(self, partial_symbol_update, params, buy_filter):
        pass
