import datetime

import dateutil

import pandas

from transactions.earningscommon import RapidApi

from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator

from config import config
class EarningProcessor(TrasnasctionHandler,RapidApi,TransactionHandlerImplementator):
    NAME="Earnings"
    def __init__(self, man,tickers):
        self.revdf = None
        self.epsnorm = None
        super(EarningProcessor, self).__init__(man)
        RapidApi.__init__(self,'SeekingAlpha')

        self._tickers=tickers


    def set_vars_for_cache(self, v):
        self.revdf = v[0]
        self.epsnorm = v[1]

    def get_earnings(self):
        if self.NoEarnings:
            raise ValueError("No earnings")
        return self.revdf.copy(), self.epsnorm.copy()
    def get_vars_for_cache(self):
        return (self.revdf, self.epsnorm)

    def get_earnings_ttm(self, sym):
        url = "https://seeking-alpha.p.rapidapi.com/symbols/get-financials"
        querystring = {"symbol": sym, "target_currency": "USD", "period_type": "ttm",
                       "statement_type": "income-statement"}

        dic = self.get_json(querystring, url)
        return dic

    def get_dfs(self, sym):
        def do(df):
            df = df[(df['value'] != False)]
            df['name'] = df['name'].apply(lambda x: dateutil.parser.parse("%s 1st %s" % tuple(x.replace('12 Months ', '').split(' '))))
            df = df.set_index('name')
            df= df[['raw_value']]
            df.columns = [sym]
            return df

        try:
            dic = self.get_earnings_ttm(sym)
            import time
            time.sleep(0.8)
            revdf = pandas.DataFrame(pandas.DataFrame(pandas.DataFrame(dic).loc[4, 'rows']).loc[0, 'cells'])
            incdf = pandas.DataFrame(pandas.DataFrame(pandas.DataFrame(dic).loc[4, 'rows']).loc[1, 'cells'])
            ls = [revdf, incdf]
            return tuple(map(do, ls))
        except:
            return (pandas.DataFrame(), pandas.DataFrame())

    def generate(self,ls,dontsave=False,force=False ):
        def adjust(df):
            df = pandas.concat(df, axis=1)
            if df.empty:
                return df

            # Resample the DataFrame to monthly frequency
            df_monthly = df.resample('MS').asfreq()

            # Forward fill the missing values with a limit of 12
            #df_filled = df_monthly.fillna(method='bfill', limit=12)
            #df_filled = df_filled.fillna(method='ffill', limit=4) #lets fill up to 4 months forward
            return df_monthly

        aa = [self.get_dfs(k) for k in self.gen(ls,force=force)]
        allrev, allinc = tuple(map(adjust,zip(*aa)))

        if self.revdf is not None:
            common = set(self.revdf.columns).intersection(set(allrev.columns))
            if len(common) > 0:
                self.revdf.drop(columns=common, inplace=True)
                self.epsnorm.drop(columns=common, inplace=True)
            allrev = pandas.concat([self.revdf, allrev], axis=1) 
        self.revdf = allrev
        if self.epsnorm is not None:
            allinc = pandas.concat([self.epsnorm, allinc], axis=1)
        self.epsnorm = allinc

        if not dontsave:
            self.save_cache()

    def init_vars(self):
        self.revdf = None
        self.epsnorm = None 



    def gen(self,ls,force=False):
        for x in ls:
            if x in self.IgnoreSymbols:
                continue
            if self.revdf is not None and (x in self.revdf.columns):
                if not force:
                    try:
                        if (datetime.datetime.now() - max(self.revdf[~self.revdf[[x]].isnull()].index))< config.Earnings.MaxSpanToRefershEntry:
                            continue
                    except:
                        pass

            yield x
    def populate_buydic(self):
        if not self.EarningsAtStart:
            return


        self.generate(list(self.gen(self._tickers))[0:self.MaxElements],dontsave=True) #will save afterwards