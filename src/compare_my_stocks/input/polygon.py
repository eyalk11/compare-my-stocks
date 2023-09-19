import threading
import logging
import datetime
from dataclasses import asdict

import polygon
from memoization import cached
from polygon.rest.models import TickerDetails

from common.common import c, lmap
from common.simpleexceptioncontext import simple_exception_handling, excp_handler
from config import config
from input.inputsource import InputSource
import pandas as pd 
from common.common import conv_date, dictfilt, log_conv

def get_polysource():
    return PolySource() 
#BadResponse standard errorr 
class PolySource(InputSource):
    def __init__(self,notify=None):
        from polygon import RESTClient
        self.client = RESTClient(api_key=config.Sources.PolySource.Key)
        self.lock = threading.Lock()
        self.notify=notify

    def excphandler(self,exception):
        logging.error(f"bad response poly: {exception}")
        self.notify(exception["status"])
    @excp_handler(polygon.exceptions.BadResponse,handler= excphandler)
    def get_current_currency(self, pair):
        return self.client.get_last_forex_quote(pair[0],to=pair[1])


    @simple_exception_handling(err_description='error in resolve symbol',return_succ=None,never_throw=True)
    @excp_handler(polygon.exceptions.BadResponse, handler=excphandler)
    @cached
    def resolve_symbol(self, sym): 
        return c(self.convert_sym_dic,self.client.get_ticker_details)(sym)

    @simple_exception_handling(err_description='error in matching symbols')
    @excp_handler(polygon.exceptions.BadResponse, handler=excphandler)
    def get_matching_symbols(self, sym, results=10):
        ls=lmap(c(self.client.get_ticker_details,lambda x:x.ticker) ,self.client.list_tickers(search=sym))
        ls=lmap(self.convert_sym_dic, ls)
        return ls[:results] 

    # def get_best_matches(self, sym, results=10, strict=True):
        # if not strict:
            # return self.get_matching_symbols(sym,results=results)
        # else:
            # return [self.resolve_symbol(sym)]





        #logging.debug(('owner',threading.currentThread().ident))
        #self.ibrem._pyroClaimOwnership()


    @staticmethod 
    def convert_sym_dic(dic):
        if type(dic) is not dict: 
            dic=asdict(dic)
        dic['currency']=dic.get('currency_name').upper()
        dic['exchange']=dic.get('primary_exchange')
        dic['symbol']=dic.get('ticker') 
        return dic 


    @simple_exception_handling(err_description='error in get_symbol_history',return_succ=(None,[]),never_throw=True)
    @excp_handler(polygon.exceptions.BadResponse, handler=excphandler)
    def get_symbol_history(self, sym, startdate, enddate, iscrypto=False):
        if not(type(sym) is str):
            if hasattr(sym,'ticker') or sym.get('ticker') is not None:
                try:
                    sym=sym.ticker
                except:
                    sym=sym.get('ticker')
            else:
                raise ValueError(f"Dont know how to handle {sym}")

        l = self.resolve_symbol(sym)
        if not l:
            logging.debug((f'error resolving {sym}'))
            return None, None
        return l, self.historicalhelper(startdate, enddate, sym)

    def historicalhelper(self, startdate, enddate, sym):
        startdate=conv_date(startdate,premissive=False)
        enddate = conv_date(enddate)
        #startdate=datetime.datetime(startdate)
        #enddate=datetime.da
        # if enddate.date() ==startdate.date():
            # enddate=enddate+datetime.timedelta(days=1) 

        aggs= list(self.client.list_aggs(ticker=sym, multiplier=1,adjusted=True, timespan="day", from_=startdate, to=enddate, limit=5000))
        if len(aggs)==0:
            return None
        df = pd.DataFrame(aggs) 
        df = df.rename(columns={'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low'})
        df['date']=df['timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(x/1000))
        df.set_index('date',inplace=True)
        df=df.rename(index={i: conv_date(str(i)) for i in df.index})
        df = df.loc[df.index >= pd.to_datetime(startdate.date())]
        df = df.loc[df.index <= pd.to_datetime(enddate.date())]
        #timestamp to datetime 

        return df



    def can_handle_dict(self, sym):
        if type(sym) is TickerDetails:
            return True
        if hasattr(sym,"dic"):
            sym=sym.dic
        if type(sym)==dict and "_dic" in sym:
            sym=sym['_dic'] #why?

        return type(sym)==dict and 'currency_name' in sym


    def query_symbol(self, sym):
        pass

    @simple_exception_handling(err_description='error in get_symbol_history',return_succ=None,never_throw=True)
    def get_currency_history(self, pair, startdate, enddate):
       raise NotImplementedError()  


