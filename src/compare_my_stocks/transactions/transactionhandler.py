import pickle
from datetime import datetime

from common.common import UseCache
from config import config
from transactions.transactioninterface import TransactionHandlerInterface,TransactionHandlerImplementator



class TrasnasctionHandler(TransactionHandlerInterface,TransactionHandlerImplementator):

    def __init__(self,manager):
        self._manager  =manager
        self._buydic = {}
        self._buysymbols = set()
        self._cache_date=None
        self.File=None
        self.Use=None
        self.CacheSpan=None
        self.__dict__.update(config.TRANSACTION_HANDLERS[self.NAME])
        ok,path = config.resolvefile(self.File)
        if not ok:
            print(f'Cache not found for {self.Name}')
        self.File=path


    def get_vars_for_cache(self):
        return []
    def set_vars_for_cache(self,v):
        pass

    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic

    def get_portfolio_stocks(self):  # TODO:: to fix
        return self._buysymbols #[config.TRANSLATEDIC.get(s,s) for s in  self._buysymbols] #get_options_from_groups(self.Groups)

    def update_sym_property(self, symbol, value, prop='currency', updateanyway=True):
        current=  self._manager.symbol_info.get(symbol)
        if current:

            current=current.get(prop)
        if not current:
            self._manager.symbol_info[symbol][prop] = value
        elif current!=value:
            print(f'diff {prop} for {symbol} {current} {value}')
            if updateanyway:
                self._manager.symbol_info[symbol][prop] = value

    def try_to_use_cache(self):

        try:
            v=list(pickle.load(open(self.File, 'rb')))
            if self.save_cache_date():
                self._cache_date=v[0]
                if self.Use == UseCache.USEIFAVALIABLE and self.CacheSpan and self._cache_date and datetime.now() - self._cache_date > self.CacheSpan:
                    print("not using after all")
                    return  0
            else:
                return self.set_vars_for_cache(v)
            return self.set_vars_for_cache(tuple(v[1:]))
        except Exception as e:
            print(e)
            return 0
        return 1

    def save_cache_date(self):
        return 1

    def save_cache(self):
        if not self.File:
            return
        try:
            if self.save_cache_date():
                self._cache_date = datetime.now()
                pickle.dump(tuple([self._cache_date] + list(self.get_vars_for_cache())), open(self.File, 'wb'))
            else:
                pickle.dump((self.get_vars_for_cache()), open(self.File, 'wb'))
            print('dumpted')
        except Exception as e:
            print(e)

    def process_transactions(self):

        self._buydic = {}
        self._buysymbols = set()

        if not self.Use or (self.Use and self.Use!=UseCache.DONT):
            if  self.try_to_use_cache():
                print('using buydict cache ')
                return


        self.populate_buydic()


        self.save_cache()

