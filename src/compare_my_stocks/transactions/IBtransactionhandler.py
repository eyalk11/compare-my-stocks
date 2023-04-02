import logging
import collections
import pickle
from datetime import datetime, timedelta

from common.common import UseCache
from config import config
from transactions.transactioninterface import TransactionHandlerImplementator, BuyDictItem
from ibflex import client, parser, Trade
from transactions.transactionhandler import TrasnasctionHandler
def get_ib_handler(man):
    return IBTransactionHandler(man)


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
        try:
            response = client.download(self.token_id, self.query_id)
        except:
            logging.debug(('err in querying flex'))
            import traceback;traceback.print_exc()
            return

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
        if not self.need_to_save:
            return
        try:
            self._cache_date =datetime.now()
            pickle.dump((self._tradescache, self._cache_date), open(self.File, 'wb'))
            logging.debug(('dumpted'))
        except Exception as e:
            logging.debug((e))


    def populate_buydic(self):
        n=None
        lastdate=None
        lastdateCache = max([d.dateTime for d in self._tradescache.values()]) if len(self._tradescache)>0 else "nocache"
        usecache= ((self._cache_date  and  self._cache_date - datetime.now() < self.CacheSpan) or self.Use == UseCache.FORCEUSE) and (not self.Use == UseCache.DONT)
        if usecache:
            logging.info(('using ib cache alone'))
            newres=[]
            self.need_to_save=False

        if not usecache or self.TryToQueryAnyway:
            newres= self.doquery()
            logging.debug(('completed'))
            if newres is None:
                logging.debug(('no results obtained :('))
                return


            n=0
            for x in newres:
                if x.tradeID not in self._tradescache:
                    self._tradescache[x.tradeID]=x
                    if lastdate and x.dateTime > lastdate:
                        lastdate=x.dateTime
                        n+=1
        if not lastdate:
            lastdate=lastdateCache
        if n:
            logging.info(f"Last trade date is {lastdate}. Last trade in cache {lastdateCache}. New trades {n}")
        elif newres:
            logging.info(f"no new trades in query. Last trade {lastdate}")
        elif (not ( not usecache or self.TryToQueryAnyway)) and self._tradescache:

            logging.info(f"Didnt query cache. Last trade {lastdate}")





        for z in self._tradescache.values():
            date=z.dateTime
            z : Trade
            while date in self._buydic:
                date += timedelta(seconds=1)
                #z.dateTime=z.dateTime

            self._buydic[date] = BuyDictItem(float(z.quantity),float(z.tradePrice),z.symbol,'IB',z )

            self._buysymbols.add(z.symbol)

            self.update_sym_property(z.symbol, z.currency)
            self.update_sym_property(z.symbol, z.conid,'conId')
            self.update_sym_property(z.symbol, z.exchange, 'exchange')





