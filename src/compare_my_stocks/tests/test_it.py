import sys
import os
from pathlib import Path

from ib_async import Contract, Index

sys.path.insert(0,
    str(Path(os.path.dirname(os.path.abspath(__file__))).parent) )

#__builtins__.SILENT=False
import datetime
import logging

import numpy as np

from graph.graphgenerator import GraphGenerator, StringPointer
import pytest

from tests.testtools import UseInput
import config
import numpy
#config.STOP_EXCEPTION_IN_DEBUG=True

from unittest.mock import patch

from tests.testtools import *
@pytest.mark.parametrize("useinp", [UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT, UseInput.WITHINPUT,
                                    UseInput.LOADDEFAULTCONFIG])
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
            assert df.shape[1] >= 2
        else:
            assert df.shape [0]>= (22)
    finally:
        if useinp & UseInput.WITHINPUT:
            eng.input_processor.InputSource.disconnect()
# def test_earnings(realeng):
#     eng= realeng
#     eng._inp.

def test_adjust_currency(realeng):
    eng = realeng
    p =Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE
        , isline=True,use_groups=False, groups=['FANG'], use_cache=UseCache.FORCEUSE,
        show_graph=False,adjust_to_currency=True,currency_to_adjust='ILS')

    p.fromdate=datetime.datetime.now()-datetime.timedelta(days=5)
    p.todate=datetime.datetime.now()
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


#pytest.
def test_get_currency(inp):
    tmpinp = inp
    df= tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now())
    assert len(df)>=2
def test_get_currency_adv(inp):
    tmpinp = inp
    df2 = tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=7),
                                   datetime.datetime.now() - datetime.timedelta(days=2))

    df= tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=5), datetime.datetime.now())

    #df = tmpinp.get_currency_hist('ILS', datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now())
    assert len(df)>=3

def test_resolve(IBSourceSess):
    x= IBSourceSess
    x : IBSource
    #ls = x.get_matching_symbols('NDX')
    #ls=list(ls)
    #ls[0]['exchange']='NASDAQ'
    #ls[0]['primaryExchange']=''
    contract= Contract()
    contract.conId=416843
    # #contract =  Contract();
    # #contract.SecType = "NEWS";
    # #contract.Exchange = "BRF";
    zz=x.ibrem.ib.reqContractDetails(contract)
    x.get_right_contract_bars.cache_remove_if(lambda x, y, z: True)
    uu=x.get_right_contract_bars(ls[0]['contract'],datetime.datetime.now(),3)
    assert len(uu)>0




def test_get_currentcurrency(inp):
    tmpinp = inp
    contract = Contract()
    contract.conId = 416843
    zz = tmpinp._inputsource.ibrem.ib.reqContractDetails(contract)
    x= tmpinp.get_relevant_currency('ILS')
    assert x>0

def test_example_inp(inp):
    tmpinp= inp

def test_ibsrvils(getremibsrv):
    x= getremibsrv
    ls = x.get_matching_symbols('LUMI')
    ls=list(ls)

def test_ibsrv(getremibsrv):
    x= getremibsrv
    ls = x.get_matching_symbols('CRWD')
    ls=list(ls)
    assert len(ls)>0
    l=list(x.get_symbol_history(ls[0],datetime.datetime.now()-datetime.timedelta(days=3),datetime.datetime.now()))
    assert len(l) > 0
    assert True


#y()

#Mock config.config to use other config file


from common.common import Types, UniteType, UseCache
from engine.parameters import Parameters

def test_basic_poly(PolySource):
    x = PolySource
    basic(x)
def test_basic(IBSourceSess):
    x = IBSourceSess
    basic(x)
def n(x):
    pass
def basic(x):


    ls = x.get_matching_symbols('CRWD')

    ls = list(ls)
    l = list(
        x.get_symbol_history(ls[0], datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now()))
    assert len(l) > 0
    assert True #len(ls)>0

def basicb(x):


    ls = x.get_matching_symbols('BYDDY')

    ls = list(ls)
    l = list(
        x.get_symbol_history(ls[0], datetime.datetime.now() - datetime.timedelta(days=3), datetime.datetime.now()))
    assert len(l) > 0
    assert True #len(ls)>0


def test_inp_cur(inp):
    inp =inp
    inp.get_currency_on_certain_time('GBP', datetime.datetime.now() - datetime.timedelta(days=3))
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
