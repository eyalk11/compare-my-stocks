import collections
import datetime
import logging
import pickle
from unittest.mock import patch

import dateutil
import pandas
import pytest
from ib_insync import Forex

from common.common import dictnfilt, UseCache, VerifySave
from config import config as cfg
from engine.parameters import Parameters
from input.earningsproc import EarningProcessor
from input.inputdata import InputDataImpl
from input.inputprocessor import InputProcessor
from transactions.IBtransactionhandler import IBTransactionHandler
from transactions.parsecsv import return_trades
import config
from tests.testtools import inp, realeng, ibsource,inpb,realenghookinp
from transactions.transactioninterface import BuyDictItem

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

def test_var():
    from common.refvar import GenRefVar
    import typing

    g=GenRefVar[bool]()()
    g.value=(True)
    assert g
    g.value=False
    assert not g
def test_basic_sym(ibsource):
    x = ibsource
    pair=('ILS','USD')
    f = pair[1] + pair[0]
    contract = Forex(f)


    ls = x.historicalhelper(datetime.datetime.now()-datetime.timedelta(days=3),datetime.datetime.now(),contract)

    #ls = x.get_matching_symbols('GBPUSD')

    assert len(ls) >= 1


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


def test_normal_histdic(inpb):
    tmpinp = inpb
    tmpinp.load_cache(True,)
    tmpinp.load_cache(False,process_params=tmpinp.process_params)



    tmpinp.data : InputDataImpl
    for k,v in tmpinp.data.symbol_info.items():
        if v.get('currency') in ['ILA','ILS']:
            try:
                tmpinp.data._alldates_adjusted.pop(k)
            except:
                pass

    config.config.Running.VERIFY_SAVING=VerifySave.ForceSave
    tmpinp.data.save_data()


@patch.object(config.config.File, 'HIST_F',new='./data/hist_file.cache')
def test_org_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    assert 1==1


def test_aa():
    from collections import defaultdict
    dat=InputDataImpl.full_data_load()
    d=1
    dat._unrel_profit_adjusted = defaultdict(InputDataImpl.init_func)
    self=dat
    s=set(dat._alldates.keys())
    for k in s:
        if k!='LUMI':
            dat._alldates.pop(k)
            dat._alldates_adjusted.pop(k)
    dat.symbol_info['LUMI']['currency'] = 'ILS' #fix
    s= set(dat.symbol_info)
    for k in s:
        if k!='LUMI':
            dat.symbol_info.pop(k)
    dat._alldates_adjusted=defaultdict(InputDataImpl.init_func)
    self._adjusted_value = defaultdict(InputDataImpl.init_func)
    self._unrel_profit = defaultdict(InputDataImpl.init_func)
    self._value = defaultdict(InputDataImpl.init_func)  # how much we hold
    self._avg_cost_by_stock = defaultdict(InputDataImpl.init_func)  # cost per unit
    self._rel_profit_by_stock = defaultdict(InputDataImpl.init_func)  # re
    self._tot_profit_by_stock = defaultdict(InputDataImpl.init_func)
    self._holding_by_stock = defaultdict(InputDataImpl.init_func)
    self._unrel_profit_adjusted = defaultdict(InputDataImpl.init_func)
    self._split_by_stock = defaultdict(InputDataImpl.init2)
    self._avg_cost_by_stock_adjusted = defaultdict(InputDataImpl.init_func)
    pickle.dump(self,open(r'c:\users\ekarni\compare-my-stocks\testlumi.bin', 'wb'))
    #
#@pytest.mark.parametrize("realenghookinp",[r'c:\users\ekarni\compare-my-stocks\testlumi.bin'],indirect=True)
def test_lumi(realenghookinp):
    #dat : InputDataImpl= pickle.load(open(r'c:\users\ekarni\compare-my-stocks\testlumi.bin', 'rb'))
    eng=realenghookinp
    inp=eng._inp
    #inp.data=dat
    fil = r'c:\users\ekarni\compare-my-stocks\testlumi.bin'
    #inp._initial_process_done=True
    def xx():
        return  pickle.load(open(fil, 'rb'))
        #return InputDataImpl()



    with patch.object(InputDataImpl, 'full_data_load', xx),patch.object( InputProcessor,'process_transactions',lambda x:None), \
        patch.object(InputDataImpl, 'save_data', lambda x:None):
        config.config.Input.FULLCACHEUSAGE=UseCache.FORCEUSE
        inp.transaction_handler._ib.need_to_save=False

        inp.process(params=Parameters(use_groups=False, use_cache=UseCache.DONT,_selected_stocks=["LUMI"]))
        inp.data.symbol_info['LUMI']['currency'] = 'ILS'  # f
        fromdt=dateutil.parser.parse('2023-01-15')
        todt=dateutil.parser.parse('2023-01-20')
        inp.transaction_handler._buydic = collections.OrderedDict(
            [(fromdt, BuyDictItem(Qty=200, Cost=2900, Symbol='LUMI')),

             (todt,
              BuyDictItem(Qty=-100, Cost=2800, Symbol='LUMI'))])

        p=Parameters(use_groups=False, use_cache=UseCache.DONT,_selected_stocks=["LUMI"])
        p.fromdate=fromdt
        p.todate=todt+datetime.timedelta(days=4)
        inp.data._symbols_wanted= set()
        inp.process(params=p, partial_symbol_update=["LUMI"])
        #pickle.dump(inp.data, open(r'c:\users\ekarni\compare-my-stocks\testlumi.bin', 'wb'))
        a=1





# @patch.object(config.config.File, 'HIST_F',new='./data/hist_file.cache')
# def test_org_histdic(inpb):
#     tmpinp = inpb
#     tmpinp.data
#     assert 1==1

