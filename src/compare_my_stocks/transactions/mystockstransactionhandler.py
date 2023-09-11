import logging
import csv
import datetime
import math
import re
import bisect
from collections import namedtuple

import matplotlib
import pandas as pd
from dateutil import parser

from common.common import neverthrow
from common.simpleexceptioncontext import simple_exception_handling
from config import config,resolvefile
from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator, BuyDictItem, TransactionSource


def get_stock_handler(man):
    return MyStocksTransactionHandler(man)


class MyStocksTransactionHandler(TrasnasctionHandler, TransactionHandlerImplementator):
    NAME = "MyStocks"
    COLUMNS = ["Id", "Symbol", "Name", "DisplaySymbol", "Exchange", "Portfolio", "Currency", "Last Traded Price",
               "Quantity", "Cost Per Share", "Cost Basis Method", "Commission", "Date", "TimeOfDay", "PurchaseFX",
               "Type", "Method", "Method Execution Ids", "Notes"]
    FAKECOLUMNS = ["Id", "Symbol", "Name", "DisplaySymbol", "Exchange", "Portfolio", "Currency", "Last_Traded_Price",
               "Quantity", "Cost_Per_Share", "Cost_Basis_Method", "Commission", "Date", "TimeOfDay", "PurchaseFX",
               "Type", "Method", "Method_Execution_Ids", "Notes"]
    Row=namedtuple("Row", FAKECOLUMNS,defaults=[""]* len(COLUMNS ))
    def __init__(self,manager,):
        super().__init__(manager)

    def log_buydict_stats(self):
        if len(self._buydic) == 0:
            logging.info("Buy dictionary is empty.")
            return

        min_date, max_date = min(self._buydic), max(self._buydic)
        num_transactions = len(self._buydic)

        logging.info(f"Buy dictionary  for MyStocks contains {num_transactions} transactions.")
        logging.info(f"Earliest transaction date: {min_date}.")
        logging.info(f"Latest transaction date: {max_date}.")


    def save_cache_date(self):
        return 0

    def populate_buydic(self):
        try:
            ok, path = resolvefile(self.SrcFile,use_alternative=config.Running.USE_ALTERANTIVE_LOCATION)
            if not ok:
                logging.error((f'Srcfile {self.SrcFile} not found for {self.NAME}'))
                return
            else:
                logging.info(f"Mystock src file is {self.SrcFile}")
            x = pd.read_csv(path)
        except Exception as e:
            logging.debug((f'{e} while getting buydic data'))
            return

        self.read_trasaction_table(x)


    @simple_exception_handling("read_transaction")
    def read_trasaction_table(self, x):
        #x = x[['Portfolio', 'Symbol', 'Quantity', 'Cost Per Share', 'Type', 'Date']]
        #   x['TimeOfDay']
        x.columns = (list(x.columns[:-1]) + ["Notes"]) #Fix Notes
        x=x.rename(columns={'Shares Owned':'Quantity','Transaction Date':'Date','Transaction Time':'TimeOfDay','Display Symbol':'DisplaySymbol'})
        for q in zip(x['Portfolio'], x['Symbol'], x['Quantity'], x['Cost Per Share'], x['Type'], x['Date'],x['TimeOfDay'],x['Currency'],x['Exchange'],x["DisplaySymbol"],x["Notes"]):
            t=q[:-4]
            t= tuple([t[0], self.translate_symbol(t[1]) ] + list(t[2:]))
            #   x['TimeOfDay']):
            # if not math.isnan(t[1]):
            #    self._symbols.add(t[1])
            prot = self.PortofolioName

            if (self._manager.params is not None ):
                if (self._manager.params.portfolio  is None):
                    self._manager.params.portfolio= prot
                else:
                    prot = self._manager.params.portfolio

            if (prot and t[0] != prot) or math.isnan(t[2]):
                if not config.TransactionHandlers.SUPRESS_COMMON:
                    logging.warn(f"skipping over transaction {t}")
                continue
            dt = str(t[-2]) + ' ' + str(t[-1])
            # logging.debug((dt))
            try:
                if math.isnan(t[-2]):
                    logging.debug((t))
            except:
                pass
            arr = dt.split(' ')

            dt = parser.parse(' '.join([arr[0], arr[2], arr[1]]))
            while dt in self._buydic:
                dt += datetime.timedelta(milliseconds=10)

            # aa=matplotlib.dates.date2num(dt)
            # timezone = pytz.timezone("UTC")
            # dt=timezone.normalize(dt)
            # dt=dt.replace(tzinfo=None)

            if (neverthrow(math.isnan,q[-1]) or neverthrow(lambda : len(q)==0)):
                self._buydic[dt] = BuyDictItem(t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1],'MYSTOCK',Source=TransactionSource.STOCK)  # Qty,cost,sym
            else:
                self._buydic[dt] = BuyDictItem(t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1],q[-1], Source=TransactionSource.CACHEDIBINSTOCK if "IB" in q[-1] else TransactionSource.STOCK )  # Qty,cost,sym
            self._buysymbols.add(t[1])
            if q[-4]:
                self.update_sym_property(t[1], q[-4])
            self.update_sym_property(t[1],q[-3],"exchange")
            self.update_sym_property(t[1], q[-2], "DisplaySymbol")
            self.update_sym_property(t[1], q[-1], "Notes")

    @simple_exception_handling(err_description="save_transaction_table")
    def save_transaction_table(self, buydict,file,normailze_to_cur=False):
        #overide buy dict
        def loctim(dic,item): #not the most efficient.
            ll=list(dic.keys())
            ind=bisect.bisect_left(ll, item)
            if ind>0:
                return dic.get(ll[ind - 1])
        dt= pd.DataFrame(columns=self.COLUMNS)
        index=0
        for t  ,z in sorted(buydict.items()):
            tim = matplotlib.dates.date2num(t)
            if normailze_to_cur:
                inp = self._manager._inp 
                cur=inp._cur_splits.get(z.Symbol)
                then=loctim(inp._split_by_stock.get(z.Symbol),tim)
                if cur and then:
                    z=z._replace(Qty=float(z.Qty)*cur/then,Cost=float(z.Cost)*then/cur)
                else:
                    z=z

            index+=1
            t : datetime.datetime
            syminfo=self._manager.symbol_info.get(z[2])
            if  syminfo:
                currency=syminfo.get("currency",config.Symbols.BASECUR)
            else:
                syminfo={}
            x=self.Row(Id=index,
                Symbol=z[2],Portfolio=self.PortofolioName,TimeOfDay=str(t.time().strftime("%H:%M:%S")),Date=re.sub("GMT$","GMT+0000", str(t.date().strftime("%Y-%m-%d GMT%z"))),
                DisplaySymbol=syminfo.get("DisplaySymbol",z[2]),Currency= currency,Type="Buy" if z[0]>0 else "Sell",Method="FIFO",Notes=z[3],
                Exchange=syminfo.get("exchange","UNK"),Quantity=abs(z[0]),Cost_Per_Share=z[1],Name=syminfo.get("name",z[2]))

            dt=dt.append(dict(zip(self.COLUMNS,tuple(x))),ignore_index=True)


        dt.set_index("Id",inplace=True)
        dt = dt.applymap(lambda x: "" if str(x) == "nan" else x )
        dt=dt.applymap(lambda x: '"%s"' % x if x != ''  else x)
        dt.to_csv(file, quoting=csv.QUOTE_NONE,escapechar='\\')
        logging.debug(("saved"))









    def get_vars_for_cache(self):
        return (self._buydic, self._buysymbols, "tmp")

    def set_vars_for_cache(self,v):
        (self._buydic, self._buysymbols, _) = v
        if len(self._buydic) == 0:
            return 0
        return 1

