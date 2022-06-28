import asyncio
import datetime

from ib_insync import Forex,util

from config import config
from input.inputsource import InputSource
from config import config



class IBSource(InputSource):

    def __init__(self,host=config.HOSTIB,port=config.PORTIB,clientId=1,readonly=True):
        super().__init__()
        from ib_insync import IB
        #loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(loop)
        self.ib=IB()
        try:
            self.ib.connect(host,port , clientId=clientId, readonly=readonly)
            print('ib connected OK')
        except Exception as e:
            import traceback;traceback.print_exc()
            print( f"{e} in connecting to ib")
            raise

    def get_positions(self):
        y = self.ib.reqPositions()
        for k in y:
            if k.contract.secType=='STK':
                yield {'contract':k.contract, 'currency':k.contract.currency,'avgCost':k.avgCost,'position':k.position}
    def get_symbol_history(self, sym, startdate, enddate, iscrypto=False):

        l=self.resolve_symbol(sym)
        if not l:
            print(f'error resolving {sym}')
            return None,None
        return l,self.historicalhelper(startdate,enddate,l['contract'])

    def historicalhelper(self, startdate,enddate,contract):
        td = enddate - startdate
        bars = self.ib.reqHistoricalData(
            contract, endDateTime=enddate, durationStr=f'{td.days} D',
            barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True)
        df = util.df(bars)
        df = df.rename({'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low'})
        return df

    def query_symbol(self, sym):
        pass


    def get_currency_history(self, pair, startdate, enddate):
        f=pair[0]+pair[1]
        contract=Forex(f)
        return None, self.historicalhelper(startdate,enddate,contract)

    def get_current_currency(self, pair):
        f=pair[0]+pair[1]
        contract=Forex(f)
        return self.get_realtime_contract(contract).markPrice

        pass

    def get_realtime_contract(self, contract):
        tick = self.ib.reqMktData(contract, '233,221')
        tick.update()
        return tick

    def get_matching_symbols(self, sym,results=10):
        #ignore results num
        ls=self.ib.reqMatchingSymbols(sym)
        for c in ls:
            dic = c.contract.__dict__
            dic['derivativeSecTypes'] = c.derivativeSecTypes
            dic['exchange']= c.contract.primaryExchange
            dic['contract']=c.contract
            yield dic
        return []

    # v = {"Sym":w['contractDesc'], "Qty": w["position"], "Last": last , "RelProfit": w['realizedPnl'], "Value": w['mktValue'],
    #      'Currency': w['currency'], 'Crypto': 0, 'Open': open, 'Source': 'IB', 'AvgConst': w['AvgCost'],
    #      'Hist': hist,'Stat':stat}
