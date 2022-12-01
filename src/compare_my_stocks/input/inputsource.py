import logging
import os
from abc import ABC, abstractmethod, ABCMeta

import pandas as pd

from common.common import InputSourceType, lmap
from config import config
from engine.symbols import AbstractSymbol


class InputSourceInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_symbol_history(self, sym, startdate, enddate, iscrypto):
        '''
        The right out format is dic[dates]['Open','Close'] and more ..
        :param sym:
        :param startdate:
        :param enddate:
        :return:
        '''
        pass

    @abstractmethod
    def get_all_symbols(self):
        pass

    @abstractmethod
    def query_symbol(self, sym):
        pass

    @abstractmethod
    def get_currency_history(self, pair, startdate, enddate):
        pass

    @abstractmethod
    def get_current_currency(self, pair):
        pass

    @abstractmethod
    def get_matching_symbols(self, sym, results):
        pass

    @abstractmethod
    def can_handle_dict(self, sym):
        pass

    @abstractmethod
    def resolve_symbol(self, sym):
        pass

    @abstractmethod
    def resolve_symbols(self, sym, results):
        pass


class InputSource():
    def __init__(self):
        self._allsymbols = []

    def can_handle_dict(self,sym):
        return True
    def resolve_symbol(self,sym):
        if self.can_handle_dict(sym) : #and (isinstance(sym, AbstractSymbol)  and sym.dic!=None) or type(sym)==dict
            if type(sym)==dict:
                return sym.get('_dic',sym)
            elif isinstance(sym, AbstractSymbol):
                return sym.dic #easy

        elif isinstance(sym, AbstractSymbol):
            sym=sym.symbol


        ls,exchok,symok=self.resolve_symbols(str(sym))

        if len(ls)==0:
            logging.debug(('nothing for %s ' % sym))
            return None
        l=ls[0]
        if exchok>1:
            logging.debug((f'multiple same exchange {sym}, picking {l}'))

        if exchok:
            return l
        elif symok:
            logging.debug((f'not right exchange {sym}, picking {l}'))
        else:
            logging.debug((f'using unmatch sym.  {l["symbol"]} o: {sym} l:{l} '))
        return l

    def resolve_symbols(self,sym,results=10):
        def fix_valid_exchanges(l):
            def upd(v):
                l['exchange'] = v
                l['contract'].exchange = l['exchange']
            #we choose here best exchange so we are surely picking the best possible score for entry
            if not ('validExchanges' in l)  or  l['contract'].exchange:
                return l
            if l['exchange']:

                logging.debug(('strange exch'))
            orgls=l['validExchanges'].split(',')
            if len(orgls)==0:
                if not l['exchange'] and 'primaryExchange' in l:
                    upd(l['primaryExchange'])
                return l

            ls=list(set(orgls).intersection(set(config.VALIDEXCHANGES)))
            ls.sort(key=lambda x: config.VALIDEXCHANGES.index(x))
            if len(ls)==0:
                logging.debug((f'couldnt find exchange {l["symbol"]} , picking {orgls[0]}'))
                upd(orgls[0])
            else:
                upd(ls[0])
            return l


        logging.debug((f'resolving {sym}'))
        ss=self.get_matching_symbols(sym, results)
        if ss is None:
            ls=[]
        else:
            ls= list(ss)

        ls = filter(lambda x: not(x is None or 'symbol' not in x), ls)
        exactmatches= list(filter(lambda x: x['symbol'].upper()==sym.upper(),ls))
        if len(exactmatches)>0:
            ls=exactmatches
        else:
            logging.warn(f"exact symbol not found {sym}")
            return [],0,0


        exchanges=config.EXCHANGES if config.INPUTSOURCE==InputSourceType.InvestPy else config.VALIDEXCHANGES
        exchanges=lmap(lambda x:x.lower(),exchanges)

        ls= list(map(fix_valid_exchanges,ls))
        matched = [l for l in ls if l['symbol'].lower() == sym.lower() and  l.get('exchange','').lower() in exchanges]
        matched.sort(key=lambda x: exchanges.index(x.get('exchange','').lower()))
        matchednex = [l for l in ls if l['symbol'].lower() == sym.lower() and l.get('exchange','').lower() not in exchanges]
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



