#__builtins__.SILENT=False
import collections
import datetime
import logging
import os.path
import time
from enum import Flag, auto
from functools import partial

import numpy as np
import pandas

from common.common import Types, UniteType, UseCache, checkIfProcessRunning, InputSourceType
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from graph.graphgenerator import GraphGenerator, StringPointer
from ib.remoteprocess import RemoteProcess
from input.earningsproc import EarningProcessor
from input.ibsource import IBSource
import pytest

from input.inputprocessor import InputProcessor
from input.inputsource import InputSource
from transactions.IBtransactionhandler import IBTransactionHandler
from transactions.parsecsv import return_trades
from transactions.transactionhandlermanager import TransactionHandlerManager
from config import config
import numpy
config.STOP_EXCEPTION_IN_DEBUG=True
@pytest.fixture(scope="session")
def ibsource():
    x = IBSource(host='127.0.0.1', port=config.IBConnection.PORTIB,proxy=False)
    return x

from unittest.mock import MagicMock, Mock, patch


@pytest.fixture(scope="session")
def inp(ibsource):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    input_source = ibsource
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,input_source)
    tr._inp=tmpinp
    return tmpinp



@pytest.fixture(scope="session")
def additional_process():
    RemoteProcess().run_additional_process()

@pytest.fixture
def realeng(additional_process):
    a=additional_process
    eng= CompareEngine(None)
    eng.transaction_handler.save_cache = Mock(return_value=None)
    eng.transaction_handler._ib.save_cache =Mock(return_value=None)
    eng.transaction_handler._stock.save_cache =Mock(return_value=None)
    eng.transaction_handler._stockprices.save_cache =Mock(return_value=None)


    eng.call_graph_generator = Mock(return_value=None)
    eng.input_processor.save_data = Mock(return_value=None) #Dont save anything please . Because loading data like that is not nice.

    return eng
#make useinp a flag
class UseInput(Flag):
    Nothing=0
    WITHINPUT=auto()
    LOADDEFAULTCONFIG=auto()



@pytest.mark.parametrize("useinp",  [UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT,UseInput.WITHINPUT,UseInput.LOADDEFAULTCONFIG])
def test_realengine(mock_config_to_default,realeng,useinp):
    logging.info("Starting test_realengine, useinp=%s",useinp)
    try:
        eng = realeng
        p =Parameters(
            type=Types.PRICE, unite_by_group=UniteType.NONE
            , isline=True,use_groups=True, groups=['FANG'], use_cache=UseCache.FORCEUSE,
            show_graph=False)
        if  useinp & UseInput.WITHINPUT:
            p.fromdate=datetime.datetime.now()-datetime.timedelta(days=5)
            p.todate=datetime.datetime.now()
        else:
            p.fromdate= datetime.datetime(2022, 11, 1)
            p.todate = datetime.datetime(2022, 12, 1)

        eng.gen_graph(p)
        assert eng.call_graph_generator.call_args is not None
        df= eng.call_graph_generator.call_args.args[0]
        if useinp & UseInput.WITHINPUT:
            assert df.shape[0] >=1 #at least one good day
            assert df.shape[1] == 2
        else:
            assert df.shape == (27,4)
    finally:
        if useinp & UseInput.WITHINPUT:
            eng.input_processor.inputsource.disconnect()

def test_adjust_currency(realeng):
    eng = realeng
    p =Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE
        , isline=True,use_groups=False, groups=['FANG'], use_cache=UseCache.FORCEUSE,
        show_graph=False,adjust_to_currency=True,currency_to_adjust='ILS')

    p.fromdate=datetime.datetime.now()-datetime.timedelta(days=5)
    p.todate=None
    eng.params=p
    eng.to_use_ext = eng.params.use_ext
    eng.used_unitetype = eng.params.unite_by_group
    eng.process()
    eng.call_data_generator()
    arr = numpy.isnan(eng._datagen.orig_df).all(axis=1)
    assert(arr.loc[arr==False].size>=3)
    a=1
    #df= eng.call_graph_generator.call_args.args[0]
    #assert df.shape == (3,2)




@pytest.fixture(scope="session")
def getremibsrv():
    #if tws.exe process is not running, warn.
    # use process_iter to find the process
    RemoteProcess().run_additional_process()
    if not checkIfProcessRunning(config.Running.TWS_PROCESS_NAME):
         logging.warning("TWS is not running. Please run it before running tests")


    time.sleep(3)
    return IBSource(host='127.0.0.1', port=config.IBConnection.PORTIB, proxy=True)
#pytest.
def test_get_currency(inp):
    tmpinp = inp
    df= tmpinp.get_currency_hist('ILS',datetime.datetime.now()-datetime.timedelta(days=3),datetime.datetime.now())
    assert len(df)==3
def test_get_currency_adv(inp):
    tmpinp = inp
    df2 = tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=7),
                                   datetime.datetime.now() - datetime.timedelta(days=2))

    df= tmpinp.get_currency_hist('ILS',datetime.datetime.now()-datetime.timedelta(days=5),datetime.datetime.now())

    #df = tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now())
    assert len(df)>=3

def test_fix_histdic(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    nv=collections.defaultdict(dict)
    for k,dic in tmpinp._hist_by_date.items():
        for sym, v in dic.items():
            z=pandas.DataFrame.from_dict(v[0])
            u=pandas.DataFrame.from_dict(v[1])

        nv[k][sym]=(z,u)




def test_get_currentcurrency(inp):
    tmpinp = inp
    x= tmpinp.get_relevant_currency('ILS')
    assert x>0


def test_basic(ibsource):
    x = ibsource
    ls = x.get_matching_symbols('CRWD')
    ls = list(ls)
    assert True

def test_ibsrv(getremibsrv):
    x= getremibsrv
    ls = x.get_matching_symbols('CRWD')
    ls=list(ls)
    assert len(ls)>0
    l=list(x.get_symbol_history('CRWD',datetime.datetime.now()-datetime.timedelta(days=3),datetime.datetime.now()))
    assert len(l) > 0
    assert True
# def x():
#     x=IBSource(host='127.0.0.1',port=7596)
#     try:
#         ls=x.get_matching_symbols('CRWD')
#         ls = list(ls)
#         ls=ls
#     except:
#         try:
#             import Pyro5
#
#             logging.debug(("".join(Pyro5.errors.get_pyro_traceback())))
#         except:
#             pass
#         import traceback
#         traceback.print_exc()
#
#     ls=list(ls)
#     ls=ls
def y():
    e=EarningProcessor()
    zz=e._pr.get_hist_split(['TSLA']) #get_earnings(['TSLA'])
    zz=zz

#y()

#Mock config.config to use other config file

import config
import pytest
from unittest.mock import patch as mock_patch

from config.newconfig import Config,FILE_LIST_TO_RES,ConfigLoader

@pytest.fixture
def mock_config_to_default(useinp):
    ConfigLoader.config.update_from(generate_config(useinp),all=True)

    #with mock_patch('config.newconfig.ConfigLoader.config' ,generate_config(useinp)):
    #    yield

def generate_config(useinp):
    if useinp & UseInput.LOADDEFAULTCONFIG:
        c=ConfigLoader.main(use_alternative=True) #'./data/myconfig.yaml')
        #TODO: to fix
        try:
            #The idea is that the file is not in the repo, and it would be for my computer only (without changing original conf/ example conf)
            #currently :
            # testingconf.py
            # ADDPROCESS = [process]
            from config import testingconf
            c.IBConnection.ADDPROCESS =testingconf.ADDPROCESS
        except:
            c.IBConnection.ADDPROCESS=c.Testing.ADDPROCESS
    else:
        c= Config()
        c.Running.TZINFO=datetime.timezone(datetime.timedelta(hours=-3),'GMT3')
        for k,attr in enumerate( FILE_LIST_TO_RES):
            setattr(c,attr,os.path.abspath(f'./tmp/{k}' ))

        c.File.HIST_F=os.path.abspath('./data/hist_file.cache')
        c.File.JSONFILENAME=os.path.abspath('./data/groups.json')
        c.File.HIST_F_STOCK=os.path.abspath('./data/hist_file_stock.cache')
    c.TransactionHandlers.SaveCaches=False
    c.File.LOGFILE=None
    c.File.LOGERRORFILE=None
    c.Running.IS_TEST=True
    if useinp & UseInput.WITHINPUT == UseInput.Nothing :
        c.Input.INPUTSOURCE=None
    else:
        c.Input.INPUTSOURCE=InputSourceType.IB


    return c




from config import config
from common.common import Types, UniteType, UseCache
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from input.earningsproc import EarningProcessor
from input.ibsource import IBSource

def test_basic(ibsource):
    x = ibsource

    ls = x.get_matching_symbols('CRWD')

    ls = list(ls)
    assert True #len(ls)>0

def test_fix_transactions(inp):
    tmpinp = inp
    tmpinp.load_cache(False)
    inp : InputProcessor
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


def my_diff_func(self, xa, xb, ya, yb):
    diffy = abs(ya - yb)
    diffx = abs(xa - xb)
    vec = np.array([diffx, diffy])
    distance = np.linalg.norm(vec, ord=2)  # distange on display node
    return distance

@patch.object(GraphGenerator, 'diff_func',new=my_diff_func)
def test_unite_blobs():
    blob_manager = GraphGenerator(None,None)

    # Initialize data for testing
    test_data = [((1, 2), 4), ((3, 4), 14), ((5, 6), 16), ((700, 8), 1),((700, 7), 13)]
    blob_manager.tmp_point_to_annotation = {
        (1, 2): {StringPointer(originalLocation=(1,2),string="item1")},
        (3, 4): {StringPointer(originalLocation=(3,4),string="item2")},
        (5, 6): {StringPointer(originalLocation=(5,6),string="item3")},
        (700, 8): {StringPointer(originalLocation=(700,8),string="item4")},
        (700, 7): {StringPointer(originalLocation=(700,7),string="item5")},

    }

    blob_manager.unite_blobs(test_data)

    # Validate the expected output
    assert len(blob_manager.tmp_point_to_annotation) == 0
    DESTDIC= {(1, 2): 'item2\nitem3\nitem1', (3, 4): 'item2\nitem3\nitem1', (5, 6): 'item2\nitem3\nitem1',
     (700, 8): 'item4\nitem5', (700, 7): 'item4\nitem5'}
    for k,v in blob_manager.point_to_annotation.items():
        assert sorted(DESTDIC[k].split('\n')) == sorted(v.split('\n'))
