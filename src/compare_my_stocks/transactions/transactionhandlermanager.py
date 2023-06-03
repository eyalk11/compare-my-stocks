import logging

from common.logger import *
import collections
import math
from datetime import datetime
from typing import Tuple
from collections import OrderedDict
from common.common import selfifnn 
import numpy as np
import pandas as pd
import pytz

from common.common import simple_exception_handling, CombineStrategy, localize_it, TransactionSourceType, lmap
from config import config
from engine.symbolsinterface import SymbolsInterface
from transactions.IBtransactionhandler import get_ib_handler
from transactions.mystockstransactionhandler import get_stock_handler
from transactions.stockprices import StockPrices
from transactions.transactioninterface import TransactionHandlerInterface, BuyDictItem

#write a enum for transaction source 


class TransactionHandlerManager(TransactionHandlerInterface):
    def __init__(self,input_processer):
        self._inp =input_processer
        self._buydicforexport={}
        self._handlers= (self._ib, self._stock) = tuple(self.get_handlers())
        self._buysymbols=set()
        self._stockprices = StockPrices(self, self.buysymbols)

    def log_buydict_stats(self):
        pass



    @property
    def symbol_info(self):
        return self._inp.symbol_info
    
    @symbol_info.setter
    def symbol_info(self, value):
        self._inp.symbol_info = value

    @property
    def params(self):
        return self._inp._eng.params #should be process_params but it is readonly(copied) . And we want to change portfolio.
    def process_transactions(self): #from all sources
        self._buydic = {}
        self._buydicforexport={}
        self._buysymbols.clear()
        self.combine_transactions()

        self._buydic= { (pytz.UTC.localize(x,True) if x.tzinfo is None else x )  : y  for x,y in self._buydic.items()  }

        #replace the following assigment  with a property
        #self._stockprices._tickers=self.buysymbols
        self._stockprices._tickers = self.buysymbols

        self._stockprices.process_transactions()

    @simple_exception_handling("error in combine transactions")
    def combine_transactions(self):
        self._ib: TransactionHandlerInterface
        self._stock: TransactionHandlerInterface
        for k in self._handlers:
            if k is not None:
                k.process_transactions()
                self._buysymbols.update(k.buysymbols)

        logging.info((
                         f"Loaded  {len(self._stock.buydic) if self._stock else '0'} MyStocks , {len(self._ib.buydic) if self._ib else '0'} IB transactions! "))
        if self._ib and self._stock:
            # combine
            if len(self._stock.buydic)*len(self._ib.buydic)==0:
                self._buydic=self._stock.buydic if len(self._stock.buydic) else self._ib.buydic
            else:
                self.combine()
                logging.info((f" Number of combined transactions {len(self._buydic)}"))
                bysource = collections.defaultdict(int)
                for k in self._buydic.values():
                    bysource[selfifnn(k.Source,'UNK') ] += 1

                logging.info((f" Number of combined transactions by source { { x.name: y for x, y in bysource.items()} }"))
        elif self._ib:
            self._buydic = self._ib.buydic
        elif self._stock:
            self._buydic = self._stock.buydic
        #split transaction by source all posibilities




        totsum = 0
        totholding = 0
        # for k, v in sorted(lmap(lambda x: (localize_it(x[0]),x[1]) ,self._buydic.items())):
            # if v.Symbol!="TSLA":
                # continue
            # totholding += v[0]
            # totsum += v[0] * v[1]
            # print(v[0] * v[1],v.Qty , v.Cost, k, v.Notes, totsum, totholding)


    def try_fix_dic(self,cur_action : Tuple[datetime,BuyDictItem],last_action :  Tuple[datetime,BuyDictItem],curhold):
        if last_action is None:
            return
        if (last_action[0]-cur_action[0]).days < config.TransactionHandlers.FIXBUYSELLDIFFDAYS and  curhold-cur_action[1].Qty+last_action[1].Qty>=0:

            self._buydic[cur_action[0]]= last_action[1]._replace(Notes=last_action[1].Notes+"| Orig time: "+ str(last_action[0]))
            self._buydic[last_action[0]] = cur_action[1]._replace(
                Notes=cur_action[1].Notes + "| Orig time: " + str(cur_action[0]))
            logging.debug((f"replaced {last_action} {cur_action}"))

    def combine(self):
#include all old IB:
#replace all new IB
        def update_dic(mindate, secondinst, dic, real,num_of_duplicates):
            tmpcalc={}
            datesymfirst = get_datesym(mindate)
            mindate = {x: min([y[0] for y in datesymfirst[x]]) for x in datesymfirst}
            maxdate = {x: max([y[0] for y in datesymfirst[x]]) for x in datesymfirst}
            maxmaxdate = max([maxdate[x] for x in maxdate])
            #update new variable of mindate when dic[s] updated
            mindate_updated = None
            maxdate_updated = None
            num_of_updates=0 
            
            for s, v in secondinst.items():
                if CombineStrategy.PREFERSTOCKS == config.TransactionHandlers.COMBINESTRATEGY:
                    if config.TransactionHandlers.JustFromTheEndOfMyStock:
                        if s.date() < maxmaxdate:
                            num_of_duplicates+=1 
                            continue

                if (mindate.get(v.Symbol) and s.date() >= mindate[v.Symbol] and s.date() <= maxdate[v.Symbol]):
                    if v.Symbol not in config.TransactionHandlers.BOTHSYMBOLS and config.TransactionHandlers.COMBINESTRATEGY == CombineStrategy.PREFERIB:
                        num_of_duplicates +=1
                        log.debug(("ignoring trans: %s %s because in less prefered source %s" % (s, v,"real" if real else "simul" )))
                        continue
                if v.Symbol in config.TransactionHandlers.IGNORECONF and s > config.TransactionHandlers.IGNORECONF[v.Symbol]:
                    num_of_duplicates +=1 
                    log.debug(("ignoring trans: %s %s because of conf  %s" % (s, v,"real" if real else "simul" )))
                    continue
                if 'IB:' in v.Notes and CombineStrategy.PREFERSTOCKS and real:
                    logging.warning(("trans: %s %s is of note ib" %(s,v)))
                forsym = datesymfirst[v.Symbol]
                for l in forsym:
                    paid = v[0] * v[1]

                    if abs((l[0] - s.date()).days) < config.TransactionHandlers.COMBINEDATEDIFF and abs(float(l[1]) - paid) < (
                            (l[1] + paid) / 2 * config.TransactionHandlers.COMBINEAMOUNTPERC / 100):
                        logging.debug(("ignoring trans: %s %s because of\n %s %s %s" % (s, v, l[0], l[2:],"real" if real else "simul" )))
                        num_of_duplicates +=1 
                        break
                else:
                    if v.Symbol=="TSLA":
                        tmpcalc[s]=v
                    
                    num_of_updates +=1

                    dic[s] = v
                    if mindate_updated==None or s< mindate_updated:
                        mindate_updated=s
                    if maxdate_updated==None or s> maxdate_updated:
                        maxdate_updated=s

            logging.info( "Changes in combine num_of_updates %s num_of_duplicates %s mindate %s maxdate %s " % (num_of_updates,num_of_duplicates,mindate_updated,maxdate_updated ))
            a=1


        def get_datesym(buydic):
            datesymb = collections.defaultdict(list)
            for k, v in buydic.items():
                datesymb[v.Symbol] += [(k.date(), float(v.Qty) * float(v.Cost), float(v.Qty), float(v.Cost))]

            return datesymb

        def get_vars(dicforsym,mindate):
            return sum( abs(v[1]) for v in dicforsym  if v[0]>=mindate), sum( 1 for v in dicforsym  if v[0]>=mindate)


        second,first= ((self._stock.buydic,self._ib.buydic) if config.TransactionHandlers.COMBINESTRATEGY == CombineStrategy.PREFERIB else (self._ib.buydic, self._stock.buydic))
        firstcopy = OrderedDict(sorted(first.items()))
        secondcopy= OrderedDict(sorted(second.items()))
        mindate=min(list(secondcopy.keys()))
        self._buydic={}
        num_of_duplicates=0

        if config.TransactionHandlers.COMBINESTRATEGY == CombineStrategy.PREFERSTOCKS:
            ls =list(filter( lambda va: "IB:" in va[1].Notes , firstcopy.items()))

            for (s,v) in list(ls):
                for secs, secv in list(secondcopy.items()):
                    if v.Qty == secv.Qty and v.Cost == secv.Cost:
                        num_of_duplicates+=1
                        firstcopy.pop(s)
                        secondcopy.pop(secs)
                        self._buydic[s]=v
                        break
                else:
                    if localize_it(s)>localize_it(mindate):
                        logging.warn(f"not found trans in IB : {s,v}")
                        firstcopy.pop(s) #remove it anyway.

            logging.debug(f"number of IB notes: {len(ls)}. Use origin {len(self.buydic)}")
        self._buydic.update( firstcopy)
        self._buydicforexport= first.copy()



        # for s,mindate in mindate.items():
        #     perc= np.linalg.norm( np.array( get_vars(datesymfirst,mindate)) - np.array(get_vars(datesymbstocks,mindate)))/  np.linalg.norm( np.array( get_vars(datesymfirst,mindate)))
        #     if abs(perc-1)>config.TransactionHandlers.MAXPERCDIFFIBSTOCKWARN:
        #         logging.debug((f"warning: {s} is suspicous IB: {  get_vars(datesymfirst,mindate) } STOCK: { get_vars(datesymfirst,mindate)} date: {mindate} "))

        update_dic(firstcopy,secondcopy, self._buydic,True,num_of_duplicates )
        update_dic(first,second, self._buydicforexport,False, num_of_duplicates)



    def get_handlers(self):
        for x, fun in zip([TransactionSourceType.IB, TransactionSourceType.MyStock], [get_ib_handler, get_stock_handler]):
            if ((config.TransactionHandlers.TRANSACTIONSOURCE & x) == x):
                handler: TransactionHandlerInterface = fun(self)
                yield handler
            else:
                yield None

    @simple_exception_handling("Error in export_portfolio")
    def export_portfolio(self):
        if config.TransactionHandlers.IncludeNormalizedOnSave:
            self._stock.save_transaction_table(buydict=self._buydic, file=config.File.EXPORTEDPORT,normailze_to_cur=False)
            self._stock.save_transaction_table(buydict=self._buydic, file=config.File.EXPORTEDPORT+"normailzed",normailze_to_cur=True)
        else:
            self._stock.save_transaction_table(buydict=self._buydic, file=config.File.EXPORTEDPORT,
                                               normailze_to_cur=False)

        dt=self._inp._current_status
        dfIB,dfMYSTOCK=  self._inp.complete_status()
        dt : pd.DataFrame
        dt=dt.join(dfIB,on="stock",rsuffix="_IB").join(dfMYSTOCK,on="stock",rsuffix="_MY")
        dt.to_csv(config.File.EXPORTEDPORT+".state.csv")

    def update_buydic(self,key,val):
        self._buydic[key]=val


    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic
    @property
    def buydicforexport(self) -> dict:
        return self._buydicforexport
