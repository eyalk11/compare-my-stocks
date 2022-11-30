import csv
import datetime
import math
import re
from collections import namedtuple

import pandas as pd
from dateutil import parser

from config import config
from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator, BuyDictItem


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


    def save_cache_date(self):
        return 0

    def populate_buydic(self):
        try:
            x = pd.read_csv(self.SrcFile)
        except Exception as e:
            print(f'{e} while getting buydic data')
            return
        try:
            self.read_trasaction_table(x)
        except Exception as e:
            print(f'{e} while reading transaction data')
            return


    def read_trasaction_table(self, x):
        #x = x[['Portfolio', 'Symbol', 'Quantity', 'Cost Per Share', 'Type', 'Date']]
        #   x['TimeOfDay']
        x.columns = (list(x.columns[:-1]) + ["Notes"]) #Fix Notes
        for q in zip(x['Portfolio'], x['Symbol'], x['Quantity'], x['Cost Per Share'], x['Type'], x['Date'],x['TimeOfDay'],x['Currency'],x['Exchange'],x["DisplaySymbol"],x["Notes"]):
            t=q[:-4]
            #   x['TimeOfDay']):
            # if not math.isnan(t[1]):
            #    self._symbols.add(t[1])

            if self._manager.params.portfolio  is None:
                self._manager.params.portfolio = self.PortofolioName
            if (self._manager.params.portfolio and t[0] != self._manager.params.portfolio) or math.isnan(t[2]):
                continue
            dt = str(t[-2]) + ' ' + str(t[-1])
            # print(dt)
            try:
                if math.isnan(t[-2]):
                    print(t)
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
            self._buydic[dt] = BuyDictItem(t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1],'MYSTOCK')  # Qty,cost,sym
            self._buysymbols.add(t[1])
            if q[-4]:
                self.update_sym_property(t[1], q[-4])
            self.update_sym_property(t[1],q[-3],"exchange")
            self.update_sym_property(t[1], q[-2], "DisplaySymbol")
            self.update_sym_property(t[1], q[-1], "Notes")


    def save_transaction_table(self, buydict,file):
        dt= pd.DataFrame(columns=self.COLUMNS)
        index=0
        for t  ,z in sorted(buydict.items()):
            index+=1
            t : datetime.datetime
            syminfo=self._manager.symbol_info.get(z[2])
            if  syminfo:
                currency=syminfo.get("currency",config.BASECUR)
            else:
                syminfo={}
            x=self.Row(Id=index,
                Symbol=z[2],Portfolio=self.PortofolioName,TimeOfDay=str(t.time().strftime("%H:%M:%S")),Date=re.sub("GMT$","GMT+0000", str(t.date().strftime("%Y-%m-%d GMT%z"))),
                DisplaySymbol=syminfo.get("DisplaySymbol",z[2]),Currency= currency,Type="Buy" if z[0]>0 else "Sell",Method="FIFO",Notes=z[3]+":"+syminfo.get("Notes",""),
                Exchange=syminfo.get("exchange","UNK"),Quantity=abs(z[0]),Cost_Per_Share=z[1],Name=syminfo.get("name",z[2]))

            dt=dt.append(dict(zip(self.COLUMNS,tuple(x))),ignore_index=True)


        dt.set_index("Id",inplace=True)
        dt = dt.applymap(lambda x: "" if str(x) == "nan" else x )
        dt=dt.applymap(lambda x: '"%s"' % x if x != ''  else x)
        dt.to_csv(file, quoting=csv.QUOTE_NONE)
        print("saved")









    def get_vars_for_cache(self):
        return (self._buydic, self._buysymbols, "tmp")

    def set_vars_for_cache(self,v):
        (self._buydic, self._buysymbols, _) = v
        if len(self._buydic) == 0:
            return 0
        return 1

