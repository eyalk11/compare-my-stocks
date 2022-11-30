import collections
import pickle
from datetime import datetime

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
        self.DOQUERY=True
        #self.FLEXTOKEN, self.FLEXQUERY = None,None
        super().__init__(man)
        self.query_id = self.FLEXQUERY
        self.token_id =  self.FLEXTOKEN
        self._tradescache :dict  = {}
        self._cache_date=None
        self.need_to_save=True
    def doquery(self):
        logging.debug(("running query"))
        if not self.DOQUERY:
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

        if ((self._cache_date  and  self._cache_date - datetime.now() < self.CacheSpan) or self.Use == UseCache.FORCEUSE) and (not self.Use == UseCache.DONT):
            logging.debug(('using ib cache alone'))
            self.need_to_save=False
        else:
            logging.debug(('doing query'))
            newres= self.doquery()
            logging.debug(('completed'))
            if newres is None:
                logging.debug(('no results obtained :('))
                return



            for x in newres:
                if x.tradeID not in self._tradescache:
                    self._tradescache[x.tradeID]=x


        for z in self._tradescache.values():
            z : Trade
            self._buydic[z.dateTime] = BuyDictItem(float(z.quantity),float(z.tradePrice),z.symbol,'IB',z )

            self._buysymbols.add(z.symbol)

            self.update_sym_property(z.symbol, z.currency)
            self.update_sym_property(z.symbol, z.conid,'conId')
            self.update_sym_property(z.symbol, z.exchange, 'exchange')





