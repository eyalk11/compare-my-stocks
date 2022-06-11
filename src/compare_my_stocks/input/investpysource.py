import os
import random

import pandas as pd

from config import config
from input.inputsource import InputSource


class InvestPySource(InputSource):
    import investpy #use my fork please

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
        import time
        time.sleep(random.randrange(0,300)/100)
        if iscrypto:
            return self._get_crypto_history(sym,startdate,enddate)
        else:
            return self._get_symbol_history(sym,startdate,enddate)

    #def manual_resolve_symbol(self,sym):
        #for l in InvestPySource.investpy.search_quotes(text=sym, n_results=10):
    def get_matching_symbols(self,sym,results=16):
        '''
        returns dic
        '''
        return  list(map(lambda x: x.__dict__, InvestPySource.investpy.search_quotes(text=sym, n_results=results)))






    def _get_symbol_history(self, sym, startdate, enddate):
        try:
            l=None
            l=self.resolve_symbol(sym)
            if 1:
                df = InvestPySource.investpy.get_etf_historical_data(etf=l['symbol'], country=l['country'], id=l['id_'],
                                                      from_date=startdate.strftime('%d/%m/%Y'),
                                                      to_date=enddate.strftime('%d/%m/%Y'))

            return l, df
        except Exception as  r:
            print(f'{l if l else ""} is  {r}')
            return l,None



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