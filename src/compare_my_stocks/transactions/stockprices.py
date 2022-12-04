import logging
from collections import OrderedDict
from datetime import time

import dateutil

from config import config
from input.earningscommon import RapidApi, localize_me
from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator


class StockPrices(TrasnasctionHandler,RapidApi,TransactionHandlerImplementator):
    NAME="StockPrices"
    def set_vars_for_cache(self, v):
        self._buydic = v[0]


    def get_vars_for_cache(self):
        return (self._buydic,)

    def populate_buydic(self):
        for x in self._tickers:
            if x in self.IgnoreSymbols:
                continue
            if x in self._buydic:
                continue
            try:
                s=list(self.get_hist_split(x))
                if not x in self._buydic:
                    self._buydic[x] = OrderedDict()
            except Exception as e :
                logging.debug((f"failed getting hist {x} {e}"))
            s.sort(key= lambda x: x[0])

            for dt,v in s:
                self._buydic[x][dt]=v
        self.filter_bad()

    def filter_bad(self):
        for x in self.IgnoreSymbols:
            logging.debug((f"skipping over {x}"))
            if x in self._buydic:
                self._buydic.pop(x)
            continue

    def __init__(self,man,tickers):
        super(StockPrices, self).__init__(man)
        RapidApi.__init__(self)

        self._tickers=tickers




    def get_hist_split(self,symbol):
        import requests

        url = "https://stock-prices2.p.rapidapi.com/api/v1/resources/stock-prices/10y-3mo-interval"

        querystring = {"ticker": symbol}

        import time
        time.sleep(7)
        js=self.get_json(querystring,url )
        if 'message' in js:
            raise Exception(js['message'])
        for dat,l in js.items():
            for k,v in l.items():
                if k=='Stock Splits':
                    if v!=0:
                        yield localize_me(dateutil.parser.parse(dat)),v
