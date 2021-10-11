import math
import time
import datetime
from collections import defaultdict
from requests import HTTPError

import flask
import numpy
from flask import request
from flask import Flask

from ibw.client import IBClient
import importlib
CONFIGFILE='\..\config.py'
try:
    config=importlib.import_module('config',CONFIGFILE)
except:
    print('please create a valid config file (rename exampleconf to config.py)')



flaskapp = Flask('ibtest')

# Create a new session of the IB Web API.
ib_client = IBClient(
    username=config.REGULAR_USERNAME,
    account=config.REGULAR_ACCOUNT,
    is_server_running=True
)

GLOB_DIC=defaultdict( dict)
HIST_PERIOD='1m'
MAX_DIFF=60 #seconds
# grab the account data.



def grep_positions_value(acct,added_qty=0,buy_price=0,override=0):
    global GLOB_DIC
    account_data = ib_client.portfolio_accounts()
    k = 0
    cont = True
    while (cont):

        positions = ib_client.portfolio_account_positions(acct, k)
        for w in positions:
            yield get_updated_dict(w)
        cont = (len(positions) == 30)  # max in page


def get_updated_dict(w):
    stat=''
    tim = datetime.datetime.now()
    upd = False
    # symid = lookup_symbol(w[''])
    if w['conid'] in GLOB_DIC:
        td = tim - GLOB_DIC[w['conid']]['time']
        if td.total_seconds() > MAX_DIFF:
            upd = True
    else:
        upd = True
    if upd:
        hist = ib_client.market_data_history(w['conid'], HIST_PERIOD, '1d')['data']
        GLOB_DIC[w['conid']]['hist'] = hist
        GLOB_DIC[w['conid']]['time'] = tim
    else:
        hist = GLOB_DIC[w['conid']]['hist']
    if len(hist) == 0:
        print('didnt return hist')
        stat+='h'
    l = [ "84", "86", "7295","82","7741","31","7714","7682"] #7682 is change since opening , signifying if traded in market.

    mark = ib_client.market_data(w['conid'], since=None, fields=l)
    mark2 = ib_client.market_data(w['conid'], since=None, fields=l)
    bid=ask=open=None
    t= mark2[0]

    bid=t.get("84",0)
    ask=t.get('86',0)
    open=t.get('7295',None)
    if int(t.get('7682',0))==0 and '7714' not in t:
        notopennow=True

    last=w["mktPrice"]
    if open==None:
        print('open is none,using bidask')
        open=hist[-1]['o']
        last= (ask+bid)/2
        stat+='c'


    #diff=t['83']
    v = {"Sym":w['contractDesc'], "Qty": w["position"], "Last": last , "RelProfit": w['realizedPnl'], "Value": w['mktValue'],
         'Currency': w['currency'], 'Crypto': 0, 'Open': open, 'Source': 'IB', 'AvgConst': w['AvgCost'],
         'Hist': hist,'Stat':stat}

    return v


@flaskapp.route("/get_account_data")
def get_account_data():
    return {'data': list(grep_positions_value(config.REGULAR_ACCOUNT))}

PREFERED_BORSA=['NASDAQ','ISLAND','IBIS']
def test():
    acc = ib_client.portfolio_accounts()
    symid = lookup_symbol('AAPL')
    # acc2=ib_client.server_accounts()
    # hist=ib_client.market_data_history(symid, '1m','1d') #open times are on 100

    l = ["31", "70", "71", "74", "78", "84", "86", "88", "7058", "7068", "6509", "7682", "7290", "7295", "7296"]
    mark = ib_client.market_data(symid, since=None, fields=l)
    mark2 = ib_client.market_data(symid, since=None, fields=l)
    l=l

def main(runFalsk=True):
    # create a new session.
    ib_client.connect(start_server=False, check_user_input=False)
    #acc = ib_client.portfolio_accounts()
    #acc2 = ib_client.server_accounts()
    if not runFalsk:
        return
    if 0:
        test()
    else:
        flaskapp.run(debug=True, port=config.PORT)

def lookup_symbol(symb):
    try:
        contr = ib_client.symbol_search(symb)
    except Exception as e:
        print('failed %s' % symb)
        return None
    dic= {x['description']:x['conid'] for x in contr}
    picked=None
    for desc in PREFERED_BORSA:
        if desc in dic:
            return dic[desc]
    return list(dic.items())[0][1] #random

@flaskapp.route("/get_symbol_history")
def get_symbol_history(name,period,interval):
    condid=lookup_symbol(name)
    if not condid:
        return  None
    try:

        hist = ib_client.market_data_history(condid,period, interval)['data']
    except:
        print('failed getting data %s' % name )
        return None
    return hist


if __name__ == '__main__':
    main()
