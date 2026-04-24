import logging
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
        """Yield (datetime, ratio) for each stock split on `symbol`, via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            logging.warning("yfinance not installed; cannot fetch stock splits")
            return

        series = yf.Ticker(symbol).splits
        if series is None or series.empty:
            return
        for ts, ratio in series.items():
            dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
            yield localize_me(dt), float(ratio)
