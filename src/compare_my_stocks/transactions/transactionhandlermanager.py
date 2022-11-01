import collections
import math

import pytz

from config import config
from transactions.IBtransactionhandler import get_ib_handler
from transactions.mystockstransactionhandler import get_stock_handler
from transactions.transactioninterface import TransactionHandlerInterface, TransactionSourceType


class TransactionHandlerManager(TransactionHandlerInterface):
    def process_transactions(self): #from all sources
        self._buydic = {}
        self._buysymbols= set()
        handlers= []
        self._ib : TransactionHandlerInterface
        self._stock : TransactionHandlerInterface
        (self._ib,self._stock)= tuple(self.get_handlers())

        if self._ib and self._stock:
            #combine
            self.combine()
        elif self._ib:
            self._buydic=self._ib.buydic
        elif self._stock:
            self._buydic = self._stock.buydic

        self._buydic= {pytz.UTC.localize(x,True) : y  for x,y in self._buydic.items() if x.tzinfo is None }




    def combine(self):
        self._buydic = self._ib.buydic
        datesymb = collections.defaultdict(list)
        for k, v in self._ib.buydic.items():
            datesymb[v[2]] += [(k.date(), float(v[1])*float(v[0]))]
        for s, v in self._stock.buydic.items():
            if v[2] in config.IGNORECONF and s > config.IGNORECONF[v[2]]:
                print("ignoring trans: %s %s because of conf" % (s, v))
                continue

            forsym = datesymb[v[2]]
            for l in forsym:
                paid=v[0]*v[1]

                if abs((l[0] - s.date()).days) < config.COMBINEDATEDIFF and abs(float(l[1]) - paid) < (
                        (l[1] + paid)/2 * config.COMBINEAMOUNTPERC / 100):
                    print("ignoring trans: %s %s" % (s, v))
                    break
            else:
                self._buydic[s] = v

    def get_handlers(self):
        for x, fun in zip([TransactionSourceType.IB, TransactionSourceType.MyStock], [get_ib_handler, get_stock_handler]):
            if ((config.TRANSACTIONSOURCE & x) == x):
                handler: TransactionHandlerInterface = fun(self)
                handler.process_transactions()
                self._buysymbols.update(handler.buysymbols)
                yield handler
            else:
                yield None

    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic