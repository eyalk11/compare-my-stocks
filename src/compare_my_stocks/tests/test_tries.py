

from inspect import signature
import math
import sys
import os
from pathlib import Path

from common.common import neverthrow
from compare_my_stocks.common.simpleexceptioncontext import SimpleExceptionContext

sys.path.insert(0,
    str(Path(os.path.dirname(os.path.abspath(__file__))).parent) )

import collections
import datetime
import logging
import pickle
from unittest.mock import MagicMock, patch, call

import dateutil
import pandas
import pytest
from ib_insync import Forex
from numpy import nan
from pandas import DataFrame, Timestamp

from common.common import dictnfilt, UseCache, VerifySave, InputSourceType
from config import config as cfg
from engine.parameters import Parameters
from input.earningsproc import EarningProcessor
from input.inputdata import InputDataImpl
from input.inputprocessor import InputProcessor
from transactions.IBtransactionhandler import IBTransactionHandler
from transactions.parsecsv import return_trades
import config
from tests.testtools import inp, realeng, ibsource, inpb, realenghookinp
from transactions.transactioninterface import BuyDictItem

cfg.STOP_EXCEPTION_IN_DEBUG = True


def test_fix_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    nv = collections.defaultdict(dict)
    for k, dic in tmpinp._hist_by_date.items():
        for sym, v in dic.items():
            z = pandas.DataFrame.from_dict(v[0])
            u = pandas.DataFrame.from_dict(v[1])

        nv[k][sym] = (z, u)


def y():
    e = EarningProcessor()
    zz = e._pr.get_hist_split(["TSLA"])  # get_earnings(['TSLA'])
    zz = zz


def test_var():
    from common.refvar import GenRefVar
    import typing

    g = GenRefVar[bool]()()
    g.value = True
    assert g
    g.value = False
    assert not g


def test_basic_sym(ibsource):
    x = ibsource
    pair = ("ILS", "USD")
    f = pair[1] + pair[0]
    contract = Forex(f)

    ls = x.historicalhelper(
        datetime.datetime.now() - datetime.timedelta(days=3),
        datetime.datetime.now(),
        contract,
    )

    # ls = x.get_matching_symbols('GBPUSD')

    assert len(ls) >= 1


def test_fix_transactions(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    inp: InputProcessor
    inp.process_transactions()
    ibc: IBTransactionHandler = inp.transaction_handler._ib
    ntrades = return_trades(r"C:\temp\IBtradesx.csv")
    ss = set(
        [
            (t.quantity, t.tradePrice, t.tradeDate, t.fxRateToBase)
            for t in ibc._tradescache.values()
        ]
    )
    wss = set([(t.quantity, t.tradePrice) for t in ibc._tradescache.values()])
    n = 0
    for t in ntrades:
        if t.tradeID in ibc._tradescache:
            logging.info("already there")
            continue
        if (t.quantity, t.tradePrice, t.tradeDate, t.fxRateToBase) not in ss:
            logging.info(t)
            if (t.quantity, t.tradePrice) in wss:
                logging.info("strangge")
                continue

            ibc._tradescache[t.tradeID] = t
            n += 1
        else:
            logging.info(f"found {t}")
    logging.info(f"added {n} trades")
    a = 1
    ibc.need_to_save = True
    ibc.save_cache()


def test_normal_histdic(inpb):
    tmpinp = inpb
    tmpinp.load_cache(
        True,
    )
    tmpinp.load_cache(False, process_params=tmpinp.process_params)

    tmpinp.data: InputDataImpl
    for k, v in tmpinp.data.symbol_info.items():
        if v.get("currency") in ["ILA", "ILS"]:
            try:
                tmpinp.data._alldates_adjusted.pop(k)
            except:
                pass

    config.config.Running.VERIFY_SAVING = VerifySave.ForceSave
    tmpinp.save_data()


@patch.object(config.config.File, "HIST_F", new="./data/hist_file.cache")
def test_org_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    assert 1 == 1


@pytest.mark.parametrize('stock_name',["TSLA"])
def test_aa(stock_name: str):
    from collections import defaultdict

    save_path = f"c:/users/ekarni/compare-my-stocks/{stock_name}.bin"

    config.config.Input.FULLCACHEUSAGE = UseCache.FORCEUSE
    dat = InputDataImpl.full_data_load()
    inp=InputProcessor(None,None,None)
    inp.data=dat
    zz = inp.get_status_for_cur('TSLA')
    d = 1
    dat._unrel_profit_adjusted = defaultdict(InputDataImpl.init_func)
    self = dat
    s = set(dat._alldates.keys())
    for k in s:
        if k != stock_name:
            dat._alldates.pop(k)
            dat._alldates_adjusted.pop(k)
            try:
                dat._split_by_stock.pop(k)
            except:
                pass
    #dat.symbol_info[stock_name]["currency"] = stock_currency
    s = set(dat.symbol_info)
    for k in s:
        if k != stock_name:
            dat.symbol_info.pop(k)
    self._adjusted_value = defaultdict(InputDataImpl.init_func)
    self._unrel_profit = defaultdict(InputDataImpl.init_func)
    self._value = defaultdict(InputDataImpl.init_func)
    self._avg_cost_by_stock = defaultdict(InputDataImpl.init_func)
    self._rel_profit_by_stock = defaultdict(InputDataImpl.init_func)
    self._tot_profit_by_stock = defaultdict(InputDataImpl.init_func)
    self._holding_by_stock = defaultdict(InputDataImpl.init_func)
    self._unrel_profit_adjusted = defaultdict(InputDataImpl.init_func)

    self._avg_cost_by_stock_adjusted = defaultdict(InputDataImpl.init_func)
    self._adjusted_panel = DataFrame()
    self._reg_panel   = DataFrame()
    pickle.dump(self, open(save_path, "wb"))

    #


# @pytest.mark.parametrize("realenghookinp",[r'c:\users\ekarni\compare-my-stocks\testlumi.bin'],indirect=True)
def test_realprofit(realenghookinp):
    # dat : InputDataImpl= pickle.load(open(r'c:\users\ekarni\compare-my-stocks\testlumi.bin', 'rb'))
    eng = realenghookinp
    inp = eng._inp
    # inp.data=dat
    fil = r"c:\users\ekarni\compare-my-stocks\testlumi.bin"

    # inp._initial_process_done=True

        # return InputDataImpl()


    dates_set = set(
        [
            dateutil.parser.parse("2023-01-17").date(),
            dateutil.parser.parse("2023-01-21").date(),
        ]
    )
    fromdt = dateutil.parser.parse("2023-01-15")
    todt = dateutil.parser.parse("2023-01-20")
    calls = [call(BuyDictItem(Qty=200, Cost=2900, Symbol='LUMI', Notes=None, IBContract=None, Source=None, AdjustedPrice=None), 
           Timestamp('2023-01-15 00:00:00+0000', tz='UTC'), 'LUMI', 200, 2900.0, 8.502429056025143, 1.0, 0, 0.0, 0.0, 2900.0, 8.502429056025143, 3003.5, 8.77104481860115, 0.2931872088284532),
call(BuyDictItem(Qty=400, Cost=2300, Symbol='LUMI', Notes=None, IBContract=None, Source=None, AdjustedPrice=None), Timestamp('2023-01-16 00:00:00+0000', tz='UTC'), 'LUMI', 600, 2500.0, 7.32968022071133, 
1.0, 0, 347.0, nan, 2500.0, 7.32968022071133, 3073.5, nan, 0.2931872088284532),
call('', Timestamp('2023-01-17 00:00:00+0000', tz='UTC'), 'LUMI', 600, 2500.0, 7.32968022071133, 1.0, 0, 3885.0, 1149.957106144072, 2500.0, 7.32968022071133, 3147.5, 9.246275397618117, None),
call(BuyDictItem(Qty=-100, Cost=2800, Symbol='LUMI', Notes=None, IBContract=None, Source=None, AdjustedPrice=None), 
  Timestamp('2023-01-22 00:00:00+0000', tz='UTC'), 'LUMI', 500, 2500.0, 7.32968022071133, 1.0, 300.0, 2959.5, 885.6947532939876, 2500.0, 7.32968022071133, 2993.25, 8.805838142867975, 0.29382921911212156)
]
    stock="LUMI"
    buydict = [
        (fromdt, BuyDictItem(Qty=200, Cost=2900, Symbol=stock)),
        (
            fromdt + datetime.timedelta(days=1),
            BuyDictItem(Qty=400, Cost=2300, Symbol=stock),
        ),
        (todt, BuyDictItem(Qty=-100, Cost=2800, Symbol=stock)),
    ]
    verify_profit_calc(calls, buydict,dates_set, fromdt, inp, stock, todt+ datetime.timedelta(days=4),fil)

def test_split_profit(realenghookinp):
    eng = realenghookinp
    inp = eng._inp
    stock= "TSLA"
    #zz=inp.get_status_for_cur('TSLA')
    fil = r"c:\users\ekarni\compare-my-stocks\TSLA.bin"
    fromdt = dateutil.parser.parse("2020-07-19")
    todt = dateutil.parser.parse("2023-01-19")
    #OrderedDict([(datetime.datetime(2020, 8, 31, 0, 0, tzinfo=<UTC>), 5.0),
    #(datetime.datetime(2022, 8, 25, 0, 0, tzinfo=<UTC>), 3.0)])
#     datetime.date(2021, 6, 14)
    buydict = [
        (fromdt, BuyDictItem(Qty=1, Cost=140, Symbol=stock)),
        (dateutil.parser.parse("2022-06-17"), BuyDictItem(Qty=3, Cost=640, Symbol=stock)),
        (
            dateutil.parser.parse("2022-8-31"),
            BuyDictItem(Qty=-4, Cost=280, Symbol=stock),
        ),
        (todt, BuyDictItem(Qty=-20, Cost=127, Symbol=stock)),
    ]
    dates_set = set(
        [
            dateutil.parser.parse("2020-07-22").date(),
            dateutil.parser.parse("2022-07-18").date(),
            dateutil.parser.parse("2022-09-19").date(),
            dateutil.parser.parse("2023-01-21").date(),
            dateutil.parser.parse("2023-01-23").date(),
            dateutil.parser.parse("2023-01-25").date(),
        ]
    )
    with SimpleExceptionContext(err_description="aa",never_throw=True):
        verify_profit_calc([], buydict, dates_set, fromdt, inp, stock, todt+ datetime.timedelta(days=8), fil)

def verify_profit_calc(calls, buydict,dates_set, fromdt, inp, stock, todt,fil):
    def xx():
        return pickle.load(open(fil, "rb"))

    sig = signature(InputProcessor.log_info)
    orig = InputProcessor.log_info
    InputProcessor.log_info = MagicMock(wraps=orig)


    with patch.object(InputDataImpl, "full_data_load", xx), patch.object(
            InputProcessor, "process_transactions", lambda x: None
    ), patch.object(InputProcessor, "save_data", lambda x: None):
        config.config.Input.FULLCACHEUSAGE = UseCache.FORCEUSE
        config.config.TransactionHandlers.TrackStockDict[stock] = dates_set
        inp.transaction_handler._ib.need_to_save = False
        
        

        inp.process(
            params=Parameters(
                use_groups=False, use_cache=UseCache.DONT, _selected_stocks=[stock]
            )
        )
        inp.transaction_handler._stockprices.process_transactions()
        inp.transaction_handler._buydic = collections.OrderedDict(
            buydict
        )

        p = Parameters(
            use_groups=False, use_cache=UseCache.DONT, _selected_stocks=[stock]
        )
        p.fromdate = fromdt
        p.todate = todt 
        inp.data._symbols_wanted = set()
        inp.process(params=p, partial_symbol_update=[stock])
        df = DataFrame()
        for c in InputProcessor.log_info.call_args_list:
            ser=pandas.Series(list(map(str, c.args)), index=sig._parameters.keys())
            try:
                ser['Cost'] = c.args[0].Cost
                ser['Qty'] = c.args[0].Qty
            except:
                ser['Cost']= 0
                ser['Qty']= 0
            
            df = df.append(ser, ignore_index=True)
        df.to_clipboard()

        logging.debug(df)
            
        
        with SimpleExceptionContext(err_description="aa", never_throw=True):
            for c in calls:
                df = df.append(pandas.Series(list(map(str, c.args)), index=df.columns), ignore_index=True)
                k = c.args

                if c in InputProcessor.log_info.call_args_list:
                    continue
                for d in InputProcessor.log_info.call_args_list:
                    if c.args[0] == d.args[0] and c.args[1] == d.args[1]:
                        for k, l in zip(c.args, d.args):
                            if not (k == l or (neverthrow(lambda: abs(k - l) <= abs(k) / 1000)) or (
                                    math.isnan(k) and math.isnan(l))):
                                logging.debug("mismatch %s %s" % (k, l))
                                assert 0 

        # InputProcessor.log_info.assert_has_calls(calls)

        # pickle.dump(inp.data, open(r'c:\users\ekarni\compare-my-stocks\testlumi.bin', 'wb'))
        a = 7
    assert 1

