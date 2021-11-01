import datetime
import os
from abc import ABC, abstractmethod

import pandas as pd

from config import config


class InputSource(ABC):
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

    def get_all_symbols(self):
        ...

    def query_symbol(self, sym):
        ...
    def get_currency_history(self,pair,startdate,enddate):
        ...

    def get_current_currency(self, pair):
        ...
#Not working currently.
class IBSource(InputSource):

    def get_symbol_history(self,sym,startdate,enddate, iscrypto=False):
        ll = datetime.datetime.now(config.TZINFO) - startdate
        from ib.ibtest import get_symbol_history
        return get_symbol_history(sym, '%sd' % ll.days, '1d')


class InvestPySource(InputSource):
    import investpy #use my fork please
    def __init__(self):
        self._allsymbols = []
    def _get_crypto_history(self,sym,startdate,enddate):
        try:
            df= InvestPySource.investpy.crypto.get_crypto_historical_data(crypto=sym,
                                                       from_date=startdate.strftime('%d/%m/%Y'),
                                                       to_date=enddate.strftime('%d/%m/%Y'))
            return None, df
        except Exception as r:
            print(f'Symbols {sym} failed: {r}')
            return None, None

    def get_symbol_history(self, sym, startdate, enddate, iscrypto=False):
        if iscrypto:
            return self._get_crypto_history(sym,startdate,enddate)
        else:
            return self._get_symbol_history(sym,startdate,enddate)

    def _get_symbol_history(self, sym, startdate, enddate):
        try:
            l=None
            for l in InvestPySource.investpy.search_quotes(text=sym,n_results=10):
                l=l.__dict__
                if l['exchange'].lower() in  config.EXCHANGES:
                    break
            else:
                if l:
                    print(f'not  right exchange {sym}, picking {l}' )
                else:
                    print('nothing for %s ' % sym )
                    return l,None
            if 1:
                df = InvestPySource.investpy.get_etf_historical_data(etf=l['symbol'], country=l['country'], id=l['id_'],
                                                      from_date=startdate.strftime('%d/%m/%Y'),
                                                      to_date=enddate.strftime('%d/%m/%Y'))

            return l, df
        except Exception as  r:
            print(f'{l if l else ""} is  {r}')
            return l,None

    def get_all_symbols(self):
        if self._allsymbols:
            return self._allsymbols
        names=set()
        for res in config.RESOURCES:
            resource= open(os.path.join(config.RESDIR, res),'rt')
            resource=pd.read_csv(resource)
            if 'name' in resource:
                names.add(resource['name'])
        self._allsymbols= names
        return names

    def get_currency_history(self, pair : tuple, startdate, enddate):
        return InvestPySource.investpy.get_currency_cross_historical_data(pair[0]+'/'+ pair[1], startdate,
                                                    enddate)
    #gets if pair USD,EUR gets EUR price in USD
    def get_current_currency(self,pair):
        a = self.investpy.get_currency_crosses_overview(pair[1])
        a.set_index('symbol', inplace=True)
        bid=a.at[pair[1]+'/'+ pair[0],'bid']
        ask = a.at[pair[1] + '/' + pair[0], 'ask']
        return (bid+ask)/2


    def query_symbol(self,sym):
        try:
            return len(InvestPySource.investpy.search_quotes(text=sym, n_results=10)) !=0
        except:
            print('error')
            return 0
