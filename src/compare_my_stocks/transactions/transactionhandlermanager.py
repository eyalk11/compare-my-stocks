import logging
import collections
import math
from datetime import datetime
from typing import Tuple
from collections import OrderedDict

import numpy as np
import pandas as pd
import pytz

from common.common import simple_exception_handling, CombineStrategy, localize_it
from config import config
from engine.symbolsinterface import SymbolsInterface
from transactions.IBtransactionhandler import get_ib_handler
from transactions.mystockstransactionhandler import get_stock_handler
from transactions.stockprices import StockPrices
from transactions.transactioninterface import TransactionHandlerInterface, TransactionSourceType, BuyDictItem


class TransactionHandlerManager(TransactionHandlerInterface):
    def __init__(self,input_processer):
        self._inp =input_processer
        self._buydicforexport={}
        self._stockprices=None


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
        self._buysymbols= set()
        handlers= []
        self.combine_transactions()

        self._buydic= { (pytz.UTC.localize(x,True) if x.tzinfo is None else x )  : y  for x,y in self._buydic.items()  }


        self._stockprices=StockPrices(self,self.buysymbols)
        self._stockprices.process_transactions()

    @simple_exception_handling("error in combine transactions")
    def combine_transactions(self):
        self._ib: TransactionHandlerInterface
        self._stock: TransactionHandlerInterface
        (self._ib, self._stock) = tuple(self.get_handlers())
        logging.info((
                         f"Loaded  {len(self._stock.buydic) if self._stock else '0'} MyStocks , {len(self._ib.buydic) if self._ib else '0'} IB transactions! "))
        if self._ib and self._stock:
            # combine
            self.combine()

        elif self._ib:
            self._buydic = self._ib.buydic
        elif self._stock:
            self._buydic = self._stock.buydic
        logging.info((f" Number of combined transactions {len(self._buydic)}"))

    def try_fix_dic(self,cur_action : Tuple[datetime,BuyDictItem],last_action :  Tuple[datetime,BuyDictItem],curhold):
        if last_action is None:
            return
        if (last_action[0]-cur_action[0]).days < config.FIXBUYSELLDIFFDAYS and  curhold-cur_action[1].Qty+last_action[1].Qty>=0:

            self._buydic[cur_action[0]]= last_action[1]._replace(Notes=last_action[1].Notes+"| Orig time: "+ str(last_action[0]))
            self._buydic[last_action[0]] = cur_action[1]._replace(
                Notes=cur_action[1].Notes + "| Orig time: " + str(cur_action[0]))
            logging.debug((f"replaced {last_action} {cur_action}"))

    def combine(self):
#include all old IB:
#replace all new IB
        def update_dic(firstinst, secondinst,dic,real):
            datesymfirst = get_datesym(firstinst)
            firstinst = {x: min([y[0] for y in datesymfirst[x]]) for x in datesymfirst}
            maxdate = {x: max([y[0] for y in datesymfirst[x]]) for x in datesymfirst}
            for s, v in secondinst.items():

                if (firstinst.get(v.Symbol) and s.date() >= firstinst[v.Symbol] and s.date() <= maxdate[v.Symbol]):
                    if v.Symbol not in config.BOTHSYMBOLS and config.COMBINESTRATEGY == CombineStrategy.PREFERIB:
                        log(("ignoring trans: %s %s because in less prefered source %s" % (s, v,"real" if real else "simul" )))
                        continue
                if v.Symbol in config.IGNORECONF and s > config.IGNORECONF[v.Symbol]:
                    log(("ignoring trans: %s %s because of conf  %s" % (s, v,"real" if real else "simul" )))
                    continue
                if 'IB:' in v.Notes and CombineStrategy.PREFERSTOCKS and real:
                    logging.warning(("trans: %s %s is of note ib" %(s,v)))
                forsym = datesymfirst[v.Symbol]
                for l in forsym:
                    paid = v[0] * v[1]

                    if abs((l[0] - s.date()).days) < config.COMBINEDATEDIFF and abs(float(l[1]) - paid) < (
                            (l[1] + paid) / 2 * config.COMBINEAMOUNTPERC / 100):
                        logging.debug(("ignoring trans: %s %s because of\n %s %s %s" % (s, v, l[0], l[2:],"real" if real else "simul" )))
                        break
                else:
                    dic[s] = v

        def get_datesym(buydic):
            datesymb = collections.defaultdict(list)
            for k, v in buydic.items():
                datesymb[v.Symbol] += [(k.date(), float(v.Qty) * float(v.Cost), float(v.Qty), float(v.Cost))]

            return datesymb

        def get_vars(dicforsym,mindate):
            return sum( abs(v[1]) for v in dicforsym  if v[0]>=mindate), sum( 1 for v in dicforsym  if v[0]>=mindate)


        second,first= ((self._stock.buydic,self._ib.buydic) if config.COMBINESTRATEGY == CombineStrategy.PREFERIB else (self._ib.buydic, self._stock.buydic))
        firstcopy = OrderedDict(sorted(first.items()))
        secondcopy= OrderedDict(sorted(second.items()))
        mindate=min(list(secondcopy.keys()))
        self._buydic={}

        if config.COMBINESTRATEGY == CombineStrategy.PREFERSTOCKS:
            ls =list(filter( lambda va: "IB:" in va[1].Notes , firstcopy.items()))

            for (s,v) in list(ls):
                for secs, secv in list(secondcopy.items()):
                    if v.Qty == secv.Qty and v.Cost == secv.Cost:
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
        #     if abs(perc-1)>config.MAXPERCDIFFIBSTOCKWARN:
        #         logging.debug((f"warning: {s} is suspicous IB: {  get_vars(datesymfirst,mindate) } STOCK: { get_vars(datesymfirst,mindate)} date: {mindate} "))

        update_dic(firstcopy,secondcopy, self._buydic,True)
        update_dic(first,second, self._buydicforexport,False)



    def get_handlers(self):
        for x, fun in zip([TransactionSourceType.IB, TransactionSourceType.MyStock], [get_ib_handler, get_stock_handler]):
            if ((config.TRANSACTIONSOURCE & x) == x):
                handler: TransactionHandlerInterface = fun(self)
                handler.process_transactions()
                self._buysymbols.update(handler.buysymbols)
                yield handler
            else:
                yield None

    @simple_exception_handling("Error in export_portfolio")
    def export_portfolio(self):
        self._stock.save_transaction_table(buydict=self._buydic, file=config.EXPORTEDPORT)
        dt=self._inp._current_status
        dfIB,dfMYSTOCK=  self._inp.complete_status()
        dt : pd.DataFrame
        dt=dt.join(dfIB,on="stock",rsuffix="_IB").join(dfMYSTOCK,on="stock",rsuffix="_MY")
        dt.to_csv(config.EXPORTEDPORT+".state.csv")


    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic
    @property
    def buydicforexport(self) -> dict:
        return self._buydicforexport
