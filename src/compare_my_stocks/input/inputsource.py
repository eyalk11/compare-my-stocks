import os
from abc import ABC, abstractmethod

import pandas as pd

from config import config


class InputSource(ABC):
    def __init__(self):
        self._allsymbols = []

    @abstractmethod
    def get_symbol_history(self,sym,startdate,enddate, iscrypto=False):
        '''
        The right out format is dic[dates]['Open','Close'] and more ..
        :param sym:
        :param startdate:
        :param enddate:
        :return:
        '''
        ...

    @abstractmethod
    def get_all_symbols(self):
        ...

    @abstractmethod
    def query_symbol(self, sym):
        ...

    @abstractmethod
    def get_currency_history(self,pair,startdate,enddate):
        ...

    @abstractmethod
    def get_current_currency(self, pair):
        ...

    @abstractmethod
    def get_matching_symbols(self, sym,results=16):
        ...

    def resolve_symbol(self,sym):
        ls,exchok,symok=self.resolve_symbols(sym)

        if len(ls)==0:
            print('nothing for %s ' % sym)
            return None
        l=ls[0]
        if exchok>1:
            print(f'multiple same exchange {sym}, piciking {l}')

        if exchok:
            return l
        elif symok:
            print(f'not right exchange {sym}, picking {l}')
        else:
            print(f'using unmatch sym.  {l["symbol"]} o: {sym} l:{l} ')
        return l

    def resolve_symbols(self,sym,results=10):
        ls= list(self.get_matching_symbols(sym,results))

        matched = [l for l in ls if l['symbol'].lower() == sym.lower() and  l['exchange'].lower() in config.EXCHANGES]
        matched.sort(key=lambda x: config.EXCHANGES.index(x['exchange'].lower()))
        matchednex = [l for l in ls if l['symbol'].lower() == sym.lower() and l['exchange'].lower() not in config.EXCHANGES]
        if len(matched)>=1 or len(matchednex)>=1:
            return matched + matchednex,len(matched),len(matchednex) #+ set(ls)-set(matched+matchednex),1
        else:
            return ls,len(matched),len(matchednex)


    def get_all_symbols(self):
        if self._allsymbols:
            return self._allsymbols
        names = set()
        for res in config.RESOURCES:
            resource = open(os.path.join(config.RESDIR, res), 'rt')
            resource = pd.read_csv(resource)
            if 'name' in resource:
                names.add(resource['name'])
        self._allsymbols = names
        return names



