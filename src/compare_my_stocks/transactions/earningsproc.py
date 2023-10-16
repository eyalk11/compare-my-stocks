import dateutil

import pandas

from transactions.earningscommon import RapidApi

from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import TransactionHandlerImplementator


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

    def generate(self,ls,dontsave=False ):
        aa = [self.get_dfs(k) for k in ls]
        rev, inc = zip(*aa)
        allrev = pandas.concat(rev, axis=1)
        allrev=allrev.fillna(method='bfill', axis=0)
        allinc = pandas.concat(inc, axis=1).fillna(method='bfill', axis=0)
        if self.revdf is not None:
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

    def populate_buydic(self):
        if not self.EarningsAtStart:
            return
        def gen():
            for x in self._tickers:
                if x in self.IgnoreSymbols:
                    continue
                if self.revdf is not None and (x in self.revdf.columns):
                    continue
                yield x

        self.generate(list(gen())[0:self.MaxElements],dontsave=True) #will save afterwards