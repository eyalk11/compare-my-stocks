import collections
import datetime
import pickle
from collections import defaultdict

import dateutil
from pandas.core.frame import DataFrame
from config import config




import pandas

from input.earningscommon import RapidApi, localize_me
from transactions.stockprices import StockPrices


def safeloc(x,df):
    try:
        df.loc[x]
        return True
    except:
        return False


class SeekingAlphaApi(RapidApi):
    def get_shares(self,tick):

        url = "https://seeking-alpha.p.rapidapi.com/symbols/get-key-data"

        querystring = {"symbol": tick}

        t = self.get_json(querystring, url)

        return t['data'][0]['attributes']['shares']

    def get_meta_data(self,tick):
        url = "https://seeking-alpha.p.rapidapi.com/symbols/get-meta-data"

        querystring = {"symbol":tick}

        #response = requests.request("GET", url, headers=headers, params=querystring)
        t = self.get_json(querystring, url)
        sub_ind='UNK'
        sector='UNK'
        for inc in t['included']:
            if inc['type']=="sub_industry":
                sub_ind=inc['attributes']['name']
            if inc['type']=="sector":
                sector=inc['attributes']['name']
        exchange= t['data']['attributes'].get('exchange','UNK')
        company= t['data']['attributes'].get("company",'unk')

        shares=self.get_shares(tick)
        return t['data']['attributes']['name'],t['data']['id'],sub_ind,sector,exchange,company,shares

    def get_earnings_hist(self,ids_dic,periods=range(-23,3)):
        url = "https://seeking-alpha.p.rapidapi.com/symbols/get-earnings"

        querystring = {"ticker_ids": ','.join(ids_dic.keys()) , "period_type": "quarterly",
                       "relative_periods": ','.join(map(str,periods) ),
                       "estimates_data_items": "revenue_actual,eps_normalized_actual"}
        t = self.get_json(querystring, url)
        #df=pandas.DataFrame.from_dict(t['estimates'])

        dic_rev=defaultdict(lambda:defaultdict(lambda:0))
        dic_eps = defaultdict(lambda:defaultdict(lambda: 0))
        for k, v in t['estimates'].items():
            for l in v['revenue_actual'].values():
                #logging.debug((l))
                dic_rev[ids_dic[k]][dateutil.parser.parse(l[0]['period']['periodenddate'])]=l[0]['dataitemvalue']
            for l in v[ 'eps_normalized_actual'].values():
                logging.debug((l))
                dic_eps[ids_dic[k]][dateutil.parser.parse(l[0]['period']['periodenddate'])]=l[0]['dataitemvalue']
        return pandas.DataFrame.from_dict(dic_rev),pandas.DataFrame.from_dict(dic_eps)

class EarningProcessor(SeekingAlphaApi):

    def __init__(self):

        self.df=DataFrame(columns=['id','nid','sub_ind','sector','exchange','company','shares'])
        self._pr= StockPrices()
        self.splitsdic=defaultdict(list)
        #self.df.set_index('id', inplace=True)
        #self.df.set_index('ticker',inplace=True)
        self.revdf=None
        self.epsnorm=None
        #super().__init__()
    @staticmethod
    def generate_or_make():
        if  config.SKIP_EARNINGS:
            return None
        if not config.TRYSTORAGEFOREARNINGS:
            s = EarningProcessor()
        # SeekingAlpha.get_earnings_hist()
        else:
            try:
                s = EarningProcessor.fromstorage()
            except:
                s = EarningProcessor()
        return s

    @staticmethod
    def fromstorage():
        return pickle.load(open(config.EARNINGSTORAGE,'rb'))

    def save(self):
        pickle.dump(self,open(config.EARNINGSTORAGE,'wb'))

    def get_earnings(self,tickers,periods=range(-23,3)):
        def appenddf(org,other):
            if not org:
                return other
            else:
                return org.append(other) #tocheck

        logging.debug((tickers))
        tickers=list(map(lambda x: x.upper(),tickers))
        ids= dict(list(self.get_ids(tickers)))
        idshasntearnings= {i:v for i,v in  ids.items() if not safeloc(v,self.revdf)}

        if len(idshasntearnings)>0:
            (self.revdf, self.epsnorm)=  tuple(map(appenddf,[self.revdf, self.epsnorm],self.get_earnings_hist(idshasntearnings,periods)))

        self.calc_shares(tickers)

        self.save()
        return  self.epsnorm* self.sharesdf ,self.revdf, self.sharesdf

    def calc_shares(self, tickers):
        self.sharesdf = DataFrame(columns=tickers, index=self.epsnorm.index)
        for t in tickers:
            if t not in self.splitsdic:
                l = list(self._pr.get_hist_split(t))
                self.splitsdic[t] = l
            else:
                l = self.splitsdic[t]

            self.update_shares(l, t)

    def update_shares(self, l, t):
        l.sort(key=lambda x: x[0], reverse=True)
        b = collections.OrderedDict(l)
        cur = b.popitem(False) if len(b) != 0 else (localize_me(datetime.datetime(1900, 1, 1)), 0)
        curshares = self.df2.loc[t]['shares']
        for i in range(len(self.sharesdf)):
            r = self.sharesdf.iloc[i]
            if r.name >= cur[0]:
                r[t] = curshares
            else:
                curshares /= cur[1]
                r[t] = curshares
                cur = b.popitem(False) if len(b) != 0 else (localize_me(datetime.datetime(1900, 1, 1)), 0)

    def get_ids(self, tickers):
        self.df2=self.df.set_index('id')
        for tick in tickers:
            x=tick.upper()
            if not safeloc(x,self.df2):
                dic = dict(list(zip(self.df.columns, self.get_meta_data(tick))))
                self.df = self.df.append(dic, ignore_index=True)
                #self.df.set_index('id', inplace=True)
                id = dic['nid']
            else:
                id = self.df2.loc[x]['nid']
            yield id,x
        self.df2=self.df.set_index('id')


        #logging.debug((t))



#s.get_earnings(['aapl','tsla'])
#s=s
# logging.debug((.get_meta_data('aapl')))
