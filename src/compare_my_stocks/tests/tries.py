import collections
import logging
from unittest.mock import patch

import pandas

from config import config as cfg
from input.earningsproc import EarningProcessor
from input.inputprocessor import InputProcessor
from transactions.IBtransactionhandler import IBTransactionHandler
from transactions.parsecsv import return_trades
import config
cfg.STOP_EXCEPTION_IN_DEBUG=True

def test_fix_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    nv=collections.defaultdict(dict)
    for k,dic in tmpinp._hist_by_date.items():
        for sym, v in dic.items():
            z=pandas.DataFrame.from_dict(v[0])
            u=pandas.DataFrame.from_dict(v[1])

        nv[k][sym]=(z,u)


def y():
    e=EarningProcessor()
    zz=e._pr.get_hist_split(['TSLA']) #get_earnings(['TSLA'])
    zz=zz


def test_fix_transactions(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    inp: InputProcessor
    inp.process_transactions()
    ibc : IBTransactionHandler =inp.transaction_handler._ib
    ntrades=return_trades(r'C:\temp\IBtradesx.csv')
    ss=set([ (t.quantity,t.tradePrice,t.tradeDate,t.fxRateToBase) for t in  ibc._tradescache.values()])
    wss = set([(t.quantity, t.tradePrice) for t in ibc._tradescache.values()])
    n=0
    for t in ntrades:
        if t.tradeID in ibc._tradescache:
            logging.info('already there')
            continue
        if (t.quantity,t.tradePrice,t.tradeDate,t.fxRateToBase) not in ss:
            logging.info(t)
            if (t.quantity, t.tradePrice) in wss:
                logging.info("strangge")
                continue

            ibc._tradescache[t.tradeID]=t
            n+=1
        else:
            logging.info(f'found {t}')
    logging.info(f'added {n} trades')
    a=1
    ibc.need_to_save=True
    ibc.save_cache()


@patch.object(config.config.File, 'HIST_F',new='./data/hist_file.cache')
def test_org_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    assert 1==1
