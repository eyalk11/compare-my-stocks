import collections
import pickle
from datetime import datetime

from common.common import UseCache
from config import config
from transactions.transactioninterface import TrascationImplemenetorInterface
from ibflex import client, parser, Trade
from transactions.transactionhandler import TrasnasctionHandler
def get_ib_handler(man):
    return IBTransactionHandler(man,config.FLEXTOKEN,config.FLEXQUERY)


class IBTransactionHandler(TrasnasctionHandler, TrascationImplemenetorInterface):
    def __init__(self,man,token_id, query_id):
        super().__init__(man)
        self.query_id = query_id
        self.token_id = token_id
        self._tradescache :dict  = {}
        self._cache_date=None
        self.need_to_save=True
    def doquery(self):
        try:
            response = client.download(self.token_id, self.query_id)
        except:
            print('err in querying flex')
            import traceback;traceback.print_exc()
            return

        p = parser.parse(response)
        return  p.FlexStatements[0].Trades

    def try_to_use_cache(self):
        try:

            (self._tradescache , self._cache_date) = pickle.load(open(config.IBCACHE, 'rb'))
            if len(self._tradescache) == 0:
                self._tradescache={}

        except Exception as e:
            print(e)
            self._tradescache = {}
        return 0 #make it proceed


    def save_cache(self):
        if not self.need_to_save:
            return
        try:
            self._cache_date =datetime.now()
            pickle.dump((self._tradescache, self._cache_date), open(config.IBCACHE, 'wb'))
            print('dumpted')
        except Exception as e:
            print(e)


    def populate_buydic(self):
        if (self._cache_date  and  self._cache_date - datetime.now() < config.IBMAXCACHETIMESPAN) or config.IBTRANSCACHE == UseCache.FORCEUSE:
            print('using ib cache alone')
            self.need_to_save=False
        else:
            print('doing query')
            newres= self.doquery()
            print('completed')

            for x in newres:
                if x.tradeID not in self._tradescache:
                    self._tradescache[x.tradeID]=x


        for z in self._tradescache.values():
            z : Trade
            self._buydic[z.dateTime] = (float(z.quantity),float(z.tradePrice),z.symbol,'IB',z )

            self._buysymbols.add(z.symbol)

            self.update_sym_property(z.symbol, z.currency)
            self.update_sym_property(z.symbol, z.conid,'conId')
            self.update_sym_property(z.symbol, z.exchange, 'exchange')





