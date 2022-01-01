import datetime
import math
import pickle

import pandas as pd
from dateutil import parser

from config import config
from engine.symbolsinterface import SymbolsInterface


class TransactionHandler(SymbolsInterface):
    def __init__(self, filename):
        self._fn = filename
        self._buysymbols = set()

    def try_to_use_cache(self):
        try:
            (self._buydic, self._buysymbols) = pickle.load(open(config.BUYDICTCACHE, 'rb'))
            if len(self._buydic)==0:
                return 0
            return 1
        except Exception as e:
            print(e)
            return 0

    def get_portfolio_stocks(self):  # TODO:: to fix

        return self._buysymbols #[config.TRANSLATEDIC.get(s,s) for s in  self._buysymbols] #get_options_from_groups(self.Groups)

    def populate_buydic(self):
        if self.try_to_use_cache():
            return
        self._buydic = {}
        self._buysymbols = set()
        try:
            x = pd.read_csv(self._fn)
        except Exception as e:
            print(f'{e} while getting buydic data')
            return
        try:
            self.read_trasaction_table(x)
        except Exception as e:
            print(f'{e} while reading transaction data')
            return

        if config.BUYDICTCACHE:
            try:
                pickle.dump((self._buydic, self._buysymbols), open(config.BUYDICTCACHE, 'wb'))
                print('dumpted')
            except Exception as e:
                print(e)

    def read_trasaction_table(self, x):
        #x = x[['Portfolio', 'Symbol', 'Quantity', 'Cost Per Share', 'Type', 'Date']]
        #   x['TimeOfDay']
        for t in zip(x['Portfolio'], x['Symbol'], x['Quantity'], x['Cost Per Share'], x['Type'], x['Date'],x['TimeOfDay']):
            #   x['TimeOfDay']):
            # if not math.isnan(t[1]):
            #    self._symbols.add(t[1])


            if (self.params.portfolio and t[0] != self.params.portfolio) or math.isnan(t[2]):
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
            self._buydic[dt] = (t[2] * ((-1) if t[-3] == 'Sell' else 1), t[3], t[1])  # Qty,cost,sym
            self._buysymbols.add(t[1])