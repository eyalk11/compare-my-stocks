import logging
import asyncio
import datetime
import math
import multiprocessing
import random
import threading
from dataclasses import asdict
from functools import partial, lru_cache

import pandas as pd
from ib_insync import Forex, util as nbutil, Contract, RequestError
from memoization import cached

from common.common import conv_date, dictfilt, log_conv, print_formatted_traceback, selfifnn, ifnn, StandardColumns, \
    cache_if_not_none
from common.refvar import RefVar
from common.simpleexceptioncontext import simple_exception_handling, SimpleExceptionContext
from common.loghandler import TRACELEVEL
from config import config
from input.inputsource import InputSource
from config import config
from ib_insync import IB,util
import Pyro5.server
import Pyro5.client
import Pyro5.api
from ib import timeoutreg #register timeout error. don't remove!

WRONG_EXCHANGE = 200
HISTORY_ERROR=162
from ib.remoteprocess import RemoteProcess



#class MyIBSourceProxy(Pyro5.api.Proxy):

def make_sure_connected(func):
    def wrapper(self,*args,**kwargs):
        if not self.connected:
            if self.ib is None:
                self.init()
            if self.ib is not None:
                self.do_connect()
        return func(self,*args,**kwargs)
    return wrapper
class IBSourceRemGenerator:
    @Pyro5.server.expose
    def generate(self,host=config.Sources.IBSource.HostIB,port=config.Sources.IBSource.PortIB,clientId=None,readonly=True):

        ibrem= IBSourceRem(host,port,clientId,readonly)
        self._pyroDaemon.register(ibrem)
        return ibrem

class IBSourceRem:
    ConnectedME=None
    # def __del__(self):
    #     if self.IB:
    #         self.on_disconnect()
    Retries=0
    def __init__(self,host=config.Sources.IBSource.HostIB,port=config.Sources.IBSource.PortIB,clientId=None,readonly=True):
        if clientId is None:
            clientId=random.randrange(1, 900)
        self._connected = False
        self._host=host
        self._port=port
        self._clientid=clientId
        self._readonly=readonly
        self.ib=None

    @classmethod
    def on_disconnect(cls):
        logging.debug(('disconnected'))
        if cls.Retries>config.Sources.IBSource.MaxIBConnectionRetries:
            logging.error("too many retries")
            return
        IBSourceRem.ConnectedME: IBSourceRem
        if IBSourceRem.ConnectedME:
            if IBSourceRem.ConnectedME.ib is not None:
                IBSourceRem.ConnectedME.ib.disconnect()
                IBSourceRem.ConnectedME.connected=False

                if IBSourceRem.ConnectedME.ib is not None:
                    try:
                        IBSourceRem.ConnectedME.init()
                    except:
                        logging.error("error re-connecting")
                        print_formatted_traceback()

    @Pyro5.server.expose
    @property
    def connected(self):
        return self._connected
    @connected.setter
    def connected(self,value):
        self._connected=value
        if value:
            IBSourceRem.ConnectedME=self
        else:
            IBSourceRem.ConnectedME=None

    @Pyro5.server.expose
    def init(self):
        IB.RaiseRequestErrors=True

        #util.UseQT('PySide6')
        util.logToConsole('DEBUG')
        logging.debug(('initaa'))
        try:
            asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.ib=IB()
        self.ib.RequestTimeout = 20

        self.do_connect()

    def do_connect(self):
        try:
            self.ib.connect(self._host,self._port , clientId=self._clientid, readonly=self._readonly)
            IBSourceRem.ConnectedME=self
            self.connected=True
            logging.debug(('ib connected OK'))
        except Exception as e:
            logging.debug(( f"{e} in connecting to ib"))
            raise

    def whatToShow(self,contract :Contract):
        logging.debug((contract.secType))
        return ('TRADES' if contract.secType=='IND' else 'MIDPOINT')


    def reqHistoricalData(self, contract, enddate, td):
        logging.debug((log_conv("xxxx",enddate,td,type(enddate))))
        self.ib.reqMarketDataType(4) #forzen +delayed
        if td>365:
            import math
            tdy= math.ceil(td/365)
            bars = self.ib.reqHistoricalData(
                contract, endDateTime=enddate, durationStr=f'{tdy} Y',
                barSizeSetting='1 day', whatToShow=self.whatToShow(contract), useRTH=True)

        else:

            bars = self.ib.reqHistoricalData(
                contract, endDateTime= enddate, durationStr=f'{td} D',
                barSizeSetting='1 day', whatToShow=self.whatToShow(contract), useRTH=True)
        return bars






    @Pyro5.server.expose
    @make_sure_connected
    def get_current_currency(self, pair):
        logging.debug("get_current_currency {pair}")
        f=pair[0]+pair[1]
        contract=Forex(f)
        m= self.get_realtime_contract(contract).markPrice
        if math.isnan(m):
            logging.warn('getting historical data instead of real')
            a=self.reqHistoricalData(contract,datetime.datetime.now(),1)
            if len(a)>0:
                return a[0].close

    def get_realtime_contract(self, contract):
        tick = self.ib.reqMktData(contract, '233,221')
        tick.update()
        return tick

    @Pyro5.server.expose
    @make_sure_connected
    def reqHistoricalData_ext(self, contract, enddate, td):
        logging.debug(f"reqHistoricalData_ext {contract} .days {td} to {enddate}")
        if type(contract)!=Contract:

            try:
                cont=Contract.create(**contract)
            except:
                cont = Contract(**contract)
        bars= self.reqHistoricalData(cont,
                                      conv_date(enddate), td)

        ls=[asdict(x) for x in bars]
        logging.debug(f"got {len(ls)} . looking for {td}")

        return ls[::-1][:td]

    @Pyro5.server.expose
    @make_sure_connected
    def get_matching_symbols_int(self, sym,results=10):
        logging.debug(('get_matching_symbols'))
        #ignore results num
        logging.debug('before req symbols')
        ls=self.ib.reqMatchingSymbols(sym)
        if ls is None:
            logging.debug(f'req matching failed {sym}')
            return []
        logging.debug((ls))

        lsa=[]
        count=0
        for c in ls:
            count+=1

            #dic = c.contract.__dict__
            dic=asdict(c.contract)
            #if not c.contract:
            #     c.contract.exchange= config.Symbols.TRANSLATE_Symbols.Exchanges.get(c.contract.primaryExchange, c.contract.primaryExchange)
            dic['derivativeSecTypes'] = c.derivativeSecTypes
            #dic['exchange']= config.Symbols.TRANSLATE_Symbols.Exchanges.get(c.contract.primaryExchange,c.contract.primaryExchange)
            dic['contractdic']=asdict(c.contract)
            if c.contract.secType in ['BOND',"FUT","CMDTY","WAR"]:
                continue

            lsa+=[dic]
            if count == results:
                break
        return lsa

    @Pyro5.server.expose
    @make_sure_connected
    def get_contract_details_ext(self, contractdic):
        INC=["category","subcategory", "longName","validexchanges","marketName","stockType", "lastTradeTime"]
        c=Contract(**contractdic)
        for x in  self.ib.reqContractDetails(c):
            logging.debug((log_conv(asdict(x),x.validExchanges)))
            yield dictfilt(asdict(x),INC)




    def get_positions(self):
        logging.debug("positions")
        y = self.ib.reqPositions()
        for k in y:
            if k.contract.secType=='STK':
                yield {'contract':k.contract, 'currency':k.contract.currency,'avgCost':k.avgCost,'position':k.position}

class IBSource(InputSource):
    def __init__(self,host=config.Sources.IBSource.HostIB,port=config.Sources.IBSource.PortIB,clientId=None,readonly=True,proxy=True):
        super().__init__()
        if proxy:
            self._ibremgenerator=Pyro5.api.Proxy('PYRO:aaa@localhost:%s' % config.Sources.IBSource.IBSrvPort )
            self._ibremgenerator._pyroTimeout = 20

            self.ibrem=self._ibremgenerator.generate( host, port, clientId, readonly)
            self.ibrem.__class__._Proxy__check_owner = lambda self: 1
        else:
            self.ibrem=IBSourceRem(host,port,clientId,readonly)
        try:
            self.ibrem.init()
        except ConnectionRefusedError:
            logging.error('TWS not connected!')
        except TimeoutError:
            logging.warn('Got timeout on initialization (TWS), will try again.')
        except Exception as e:
            logging.error("init failed unknown error. Will keep trying.")
            print_formatted_traceback(True)



        self.lock = threading.Lock()
    def disconnect(self):
        self.ibrem._pyroRelease()
        self.ibrem.connected=False

    @cache_if_not_none
    @cached(ttl=300)
    @simple_exception_handling(err_description='get currenct currency', return_succ=None, never_throw=True)
    def get_current_currency(self, pair):
        try:
            res= self.ibrem.get_current_currency(pair)
        except RequestError:
            res = None
        if res is None:
            res=self.ibrem.get_current_currency(tuple(pair[::-1]))
            if res is not None:
                res=1/res
        return res

    # def get_current_currency(self,pair):
        # self.get_current_currency_int.cache_remove_if( lambda user_function_arguments, user_function_result, is_alive: user_function_result is None)
        # return self.get_current_currency_int(pair)



    @cache_if_not_none
    @cached
    @simple_exception_handling(err_description='error in resolve symbol',return_succ=None,never_throw=True)
    def get_matching_symbols(self, sym, results=10):
        def tmp(x):
            try:
                x.update({'contract': Contract(**x['contractdic'])})
                return x
            except:
                logging.debug((f'err in create for {x}'))
                import traceback;
                traceback.print_exc()
        with self.lock:
            ls=self.ibrem.get_matching_symbols_int(sym,results)

            contracts = list(map(tmp, ls))

            for x in contracts:
                det=list(self.ibrem.get_contract_details_ext(x['contractdic']))
                if len(det)>1 :
                    logging.debug(('strange, multiple detailed descriptions'))
                if len(det)==0:
                    logging.debug((f'no detailed description {sym}'))
                    continue
                x.update(det[0])
                #x['exchange']=x['ValidExchanges']
                #x['contract'].exchange=x['exchange']
                x.pop('contractdic')
        return contracts


    def ownership(self):
        import threading

        #logging.debug(('owner',threading.currentThread().ident))
        #self.ibrem._pyroClaimOwnership()

    def __getattr__(self, item):
        def wrapper(fun,*args,**kw):
            with self.lock:
                logging.log(TRACELEVEL,"entering iblock")
                x= fun(*args,**kw)
                logging.log(TRACELEVEL, "after iblock")
                return x
        if 'ipython' in item:
            raise AttributeError(item)
        if 'getattr' in item:
            raise AttributeError(item)
        if 'ibrem' in item:
            raise Exception('asdasdasd')
            #raise AttributeError(item)
        #logging.debug(("getatt",item))
        if hasattr(self.ibrem,item):
            z=getattr(self.ibrem,item)
        else:
            raise AttributeError(item)
        return partial(wrapper,z)


    @simple_exception_handling(err_description='error in get_symbol_history',return_succ=(None,[]),never_throw=True)
    def get_symbol_history(self, sym, startdate, enddate, iscrypto=False):

        with SimpleExceptionContext('error resolving symbol',return_succ=(None,[]),never_throw=True,detailed=False):
            l = self.resolve_symbol(sym)
            if not l:
                logging.debug((f'error resolving {sym}'))
                return None, None
        return l, self.historicalhelper(startdate, enddate, l['contract'])

    @cached(custom_key_maker=lambda self,contract,enddate, td: contract)
    def get_right_contract_bars(self,contract,enddate, td):
        with self.lock:
            cont = asdict(contract) if type(contract) is not dict else contract
            if not cont['exchange'] and cont["secType"]=='STK':
                logging.warn((f'(historicalhelper) warning: no exchange for contract {cont}'))
                cont['exchange'] = config.Symbols.TranslateExchanges.get(cont['primaryExchange'],
                                                                         cont['primaryExchange'])

            for i in range(2):
                    try:
                        bars = self.ibrem.reqHistoricalData_ext(cont, enddate.replace(hour=23), td) #we might get more than we opted for because it returns all the traded days up to the enddate..
                        return cont,bars
                    except RequestError as e:
                        if  cont["secType"]!='STK':
                            raise
                        logging.debug('req err')
                        if e.code in [ WRONG_EXCHANGE,HISTORY_ERROR]:
                            logging.debug((f'bad exchange for symbol {cont}. trying to  resolve with {config.Sources.IBSource.DefaultExchange}  . {e.message}'))
                            cont['exchange']= config.Sources.IBSource.DefaultExchange
                            if config.Sources.IBSource.DefaultExchange is None:
                                return None
                            if i==1:
                                logging.debug("tried twice. giving up")
                                raise

                        else:
                            logging.debug((f'failed reqHistoricalData {e.message} {e.code}'))
                            return None


    def historicalhelper(self, startdate, enddate, contract):
        bars=None




        startdate=conv_date(startdate,premissive=False)
        enddate = conv_date(enddate)
        #startdate=datetime.datetime(startdate)
        #enddate=datetime.da
        if enddate.date() ==startdate.date():
            td=1
        else:
            td = enddate.date()-startdate.date()
            td = td.days + 1


        self.get_right_contract_bars.cache_remove_if( lambda user_function_arguments, user_function_result, is_alive: user_function_result is None)
        is_cached=  IBSource.get_right_contract_bars.cache_contains_argument((self,contract,enddate,td))
        cont,bars = self.get_right_contract_bars(contract,enddate,td)

        if cont is None:
            return None
        if is_cached: #used cache - the bars are probably wrong. but the contract is right
            bars = self.ibrem.reqHistoricalData_ext(cont, enddate.replace(hour=23), td)
        df = nbutil.df(bars)
        if df is None:
            return None

        df = df.rename(columns={'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low'})
        df.set_index('date',inplace=True)
        df=df.rename(index={i: conv_date(str(i)) for i in df.index})
        df = df.loc[df.index >= pd.to_datetime(startdate.date())]
        df = df.loc[df.index <= pd.to_datetime(enddate.date())]
        return df



    def can_handle_dict(self, sym):
        if hasattr(sym,"dic"):
            sym=sym.dic
        if type(sym)==dict and "_dic" in sym:
            sym=sym['_dic'] #why?

        return type(sym)==dict and ('validExchanges' in sym or 'primaryExchange' in sym)


    def query_symbol(self, sym):
        pass

    @cached  # type: ignore
    def to_reverse_pair(self,pair):
        f = pair[1] + pair[0]
        contract = Forex(f)
        ls = self.historicalhelper(datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now(), contract)
        if ls is not None and  len(ls) > 0:
            return False
        else:
            f = pair[0] + pair[1]
            contract = Forex(f)
            ls = self.historicalhelper(datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now(),
                                       contract)
            if ls is not None and len(ls) > 0:
                return True
            else:
                raise KeyError(f"no data for {pair} ")


    def get_currency_history(self, pair, startdate, enddate):
        f=pair[1]+pair[0]
        if b:=self.to_reverse_pair(pair): #might raise keyerror
            f=pair[0]+pair[1]
        contract=Forex(f)
        res= self.historicalhelper(startdate,enddate,contract)

        if b:
            if res is not None:
                res[StandardColumns] = res[StandardColumns].applymap(lambda x: 1 / x)
        return res
    def get_all_symbols(self):
        raise NotImplementedError() 

    # v = {"Sym":w['contractDesc'], "Qty": w["position"], "Last": last , "RelProfit": w['realizedPnl'], "Value": w['mktValue'],
    #      'Currency': w['currency'], 'Crypto': 0, 'Open': open, 'Source': 'IB', 'AvgConst': w['AvgCost'],
    #      'Hist': hist,'Stat':stat}
  # def get_matching_symbols(self, sym,results=10):
  #       #ignore results num
  #       #z=self.ib.reqPositions()
  #       #import threading
  #       ls = self.ib.reqMatchingSymbols(sym)
  #       #logging.debug((ls))
  #
  #           # for c in ls:
  #           #     dic = c.contract.__dict__
  #           #     dic['derivativeSecTypes'] = c.derivativeSecTypes
  #           #     dic['exchange']= c.contract.primaryExchange
  #           #     dic['contract']=c.contract
  #           #     yield dic
  #           # return []
  #       from multiprocessing import Process
  #       manager = multiprocessing.Manager()
  #       return_dict = manager.dict()
  #       t=Process(target=IBSource.tmp,args=(None,sym,return_dict))
  #       t.start()
  #       t.join(50)
  #       logging.debug(('joined'))
  #       logging.debug((return_dict['x']))
  #       #return ls
def get_ibsource() :
    #IBSource = IBSource()
    proxy= True if config.Sources.IBSource.AddProcess else False
    if proxy:
        RemoteProcess().wait_for_read()
    ibsource= IBSource(proxy=proxy)
    return ibsource
