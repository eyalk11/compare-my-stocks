import datetime
import http.client
import json
import logging
import time
import urllib.parse
from collections import OrderedDict

from transactions.earningscommon import localize_me
from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator


class StockPrices(TrasnasctionHandler, TransactionHandlerImplementator):
    NAME = "StockPrices"

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
                s = list(self.get_hist_split(x))
                if x not in self._buydic:
                    self._buydic[x] = OrderedDict()
            except Exception as e:
                logging.debug(f"failed getting hist {x} {e}")
                continue
            s.sort(key=lambda x: x[0])

            for dt, v in s:
                self._buydic[x][dt] = v
        self.filter_bad()

    def filter_bad(self):
        for x in self.IgnoreSymbols:
            logging.debug(f"skipping over {x}")
            if x in self._buydic:
                self._buydic.pop(x)

    def __init__(self, man, tickers):
        super(StockPrices, self).__init__(man)
        self._tickers = tickers

    def get_hist_split(self, symbol):
        """Yield (datetime, ratio) for each stock split on `symbol` via the
        yfinance-stock-market-data RapidAPI endpoint.

        Replaces the old `yfinance` PyPI package, which can no longer reach
        Yahoo's API. Endpoint: POST /splits, form-encoded {symbol}, returns
        {"data":[{"date":<epoch_ms>, "stockSplits":<ratio>}, ...]}.
        """
        from config import config
        if not getattr(config.Running, "UseYFinance", True):
            return
        key = config.Jupyter.RapidYFinanaceKey
        host = config.Jupyter.RapidYFinanaceHost
        if not key:
            return  # absence already warned at startup
        headers = {
            'x-rapidapi-key': key,
            'x-rapidapi-host': host,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        body = b''
        # BASIC plan is 1 req/sec; retry once on 429.
        for attempt in range(2):
            conn = http.client.HTTPSConnection(host)
            conn.request('POST', '/splits', urllib.parse.urlencode({'symbol': symbol}), headers)
            res = conn.getresponse()
            body = res.read()
            if res.status == 429 and attempt == 0:
                time.sleep(1.2)
                continue
            if res.status != 200:
                logging.warning("RapidYFinance /splits %s: HTTP %s %s", symbol, res.status, body[:200])
                return
            break
        else:
            return
        for entry in json.loads(body).get('data', []):
            dt = datetime.datetime.utcfromtimestamp(entry['date'] / 1000.0)
            yield localize_me(dt), float(entry['stockSplits'])
