import logging
import collections
import pickle
from datetime import datetime, timedelta

from common.common import UseCache
from common.simpleexceptioncontext import SimpleExceptionContext
from config import config
from transactions.transactioninterface import TransactionHandlerImplementator, BuyDictItem, TransactionSource
from ibflex import client, parser, Trade
from transactions.transactionhandler import TrasnasctionHandler
def get_ib_handler(manager):
    return IBTransactionHandler(manager)


class IBTransactionHandler(TrasnasctionHandler, TransactionHandlerImplementator):
    NAME="IB"
    def __init__(self,man):
        self.DoQuery=True
        #self.FlexToken, self.FlexQuery = None,None
        super().__init__(man)
        self.query_id = self.FlexQuery
        self.token_id =  self.FlexToken
        self._tradescache :dict  = {}
        self._cache_date=None
        self.need_to_save=True

    def doquery(self):
        logging.info(("running query in IB  for transaction"))
        if not self.DoQuery or not (self.query_id) or not self.token_id:
            return
        response = None
        with SimpleExceptionContext("IB query failed",never_throw=True):
            response = client.download(self.token_id, self.query_id)
        if not response:
            return None
        with SimpleExceptionContext("IB parse failed",never_throw=True):
            p = parser.parse(response)
            return  p.FlexStatements[0].Trades

    def try_to_use_cache(self):
        try:

            (self._tradescache , self._cache_date) = pickle.load(open(self.File, 'rb'))
            if len(self._tradescache) == 0:
                self._tradescache={}

        except Exception as e:
            logging.debug((e))
            self._tradescache = {}
        return 0 #make it proceed


    def save_cache(self):
        if not config.TransactionHandlers.SaveCaches:
            logging.debug(f"not saving cache because of config{self.NAME}")
            return
        if not self.need_to_save:
            logging.debug(f"not saving cache {self.NAME}")
            return
        try:
            self._cache_date =datetime.now()
            pickle.dump((self._tradescache, self._cache_date), open(self.File, 'wb'))
            logging.debug(('IB cache saved'))
        except Exception as e:
            logging.debug((e))


    def populate_buydic(self):
        n=None
        last_date=None
        last_date_cache = max([d.dateTime for d in self._tradescache.values()]) if len(self._tradescache)>0 else None
        first_date_cache = min([d.dateTime for d in self._tradescache.values()]) if len(self._tradescache)>0 else None
        usecache= ((self._cache_date  and  self._cache_date - datetime.now() < self.CacheSpan) or self.Use == UseCache.FORCEUSE) and (not self.Use == UseCache.DONT)

        if last_date_cache:
            logging.info(f'{len(self._tradescache)} entries in IB cache. Last trade in cache {last_date_cache} . First trade in cache {first_date_cache} ')

        if usecache:
            logging.info(f'using ib cache. Cache date is {self._cache_date}')
            newres=[]
            self.need_to_save=False

        if not usecache or self.TryToQueryAnyway:
            newres= self.doquery()
            logging.debug('completed')
            if newres is None:
                logging.debug('no results obtained :(')
                return

            n=0
            min_date = datetime.now()
            max_date = datetime.fromtimestamp(0)
            for x in newres:
                if x.tradeID not in self._tradescache:
                    self._tradescache[x.tradeID]=x
                    if x.dateTime < min_date:
                        min_date = x.dateTime
                    if x.dateTime > max_date:
                        max_date = x.dateTime
                    n+=1
            if not last_date:
                last_date=last_date_cache
            if n > 0:
                self.need_to_save=True
                logging.info(f"New trades {n}. Minimum trade date in this batch is {min_date}. Maximum trade date in this batch is {max_date}.")
            elif newres:
                logging.info(f"No new trades in query. Last trade {last_date}.")
            elif (not ( not usecache or self.TryToQueryAnyway)) and self._tradescache:
                logging.info(f"Didnt query cache. Last trade {last_date}")

        for z in self._tradescache.values():
            date=z.dateTime
            z : Trade
            while date in self._buydic:
                date += timedelta(seconds=1)
            self._buydic[date] = BuyDictItem(float(z.quantity),float(z.tradePrice),z.symbol,'IB',z, Source=TransactionSource.IB )
            self._buysymbols.add(z.symbol)

            self.update_sym_property(z.symbol, z.currency)
            self.update_sym_property(z.symbol, z.conid,'conId')
            self.update_sym_property(z.symbol, z.exchange, 'exchange')
        a=1





