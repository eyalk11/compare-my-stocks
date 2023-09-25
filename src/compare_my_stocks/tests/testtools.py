import datetime
import logging
import pickle
import time
from copy import copy
from enum import Flag, auto
from unittest import mock
from unittest.mock import MagicMock, Mock, patch

import pytest
import os
from common.common import Types, UniteType, UseCache, InputSourceType, checkIfProcessRunning, VerifySave
from config import config, ConfigLoader, Config
from config.newconfig import FILE_LIST_TO_RES
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from ib.remoteprocess import RemoteProcess
from input.ibsource import IBSource
from input.inputdata import InputDataImpl
from input.inputprocessor import InputProcessor
from input.polygon import PolySource
from transactions.transactionhandlermanager import TransactionHandlerManager



class UseInput(Flag):
    Nothing=0
    WITHINPUT=auto()
    LOADDEFAULTCONFIG=auto()


@pytest.fixture
def mock_config_to_default(useinp : UseInput):
    ConfigLoader.config.update_from(generate_config(useinp),all=True)

    #with mock_patch('config.newconfig.ConfigLoader.config' ,generate_config(useinp)):
    #    yield


@pytest.fixture(scope="session")
def mock_config_to_default_sess():
    ConfigLoader.config.update_from(generate_config(UseInput.Nothing),all=True)


@pytest.fixture(scope="session")
def IBSource():
    x = IBSource(host='127.0.0.1', port=config.Sources.IBSource.PortIB,proxy=False)
    return x


@pytest.fixture(scope="session")
@pytest.mark.usefixtures("mock_config_to_default_sess")
def inp(IBSource):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = IBSource
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,InputSource)
    tmpinp.data= InputDataImpl()
    tr._inp=tmpinp
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
    #tmpinp.save_data = Mock(return_value=None)
    return tmpinp

@pytest.fixture
def inpb(IBSource):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = IBSource
    config.TransactionHandlers.SaveCaches=False
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,InputSource)
    tmpinp.data= InputDataImpl()
    tr._inp=tmpinp
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
    tmpinp.save_data = Mock(return_value=None)
    return tmpinp
@pytest.fixture
def PolySource():
    return PolySource()

@pytest.fixture
def inp_poly(PolySource):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = PolySource
    config.TransactionHandlers.SaveCaches=False
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,InputSource)
    tmpinp.data= InputDataImpl()
    tr._inp=tmpinp
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
    tmpinp.save_data = Mock(return_value=None)
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
    eng.transaction_handler._StockPrices.save_cache =Mock(return_value=None)

    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)


    eng.call_graph_generator = Mock(return_value=None)
    eng.input_processor.save_data = Mock(return_value=None) #Dont save anything please . Because loading data like that is not nice.

    return eng



#patch get_ibsource to return IBSource instead of None

@pytest.fixture

@pytest.mark.usefixtures("mock_config_to_default_sess")
def realenghookinp():
    config.Sources.IBSource.AddProcess=None
    config.Input.InputSource = InputSourceType.Cache
    
    #with mock.patch('input.ibsource.get_ibsource',new_callable=lambda : IBSource):
    eng= CompareEngine(None)
    eng.transaction_handler.save_cache = Mock(return_value=None)
    eng.transaction_handler._ib.save_cache =Mock(return_value=None)
    eng.transaction_handler._stock.save_cache =Mock(return_value=None)
    eng.transaction_handler._StockPrices.save_cache =Mock(return_value=None)

    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)

    eng.call_graph_generator = Mock(return_value=None)

    #eng.input_processor.save_data = Mock(return_value=None) #Dont save anything please . Because loading data like that is not nice.
    tmpinp = eng._inp
    tmpinp.process_params = copy(eng.params)
    tmpinp.process_params.use_cache = UseCache.FORCEUSE
    #tmpinp.data.save_data = Mock(return_value=None)
    return eng

def generate_config(useinp):
    if useinp & UseInput.LOADDEFAULTCONFIG:
        c=ConfigLoader.main(use_alternative=True) #'./data/myconfig.yaml')
        #TODO: to fix
        try:
            #The idea is that the file is not in the repo, and it would be for my computer only (without changing original conf/ example conf)
            #currently :
            # testingconf.py
            # AddProcess = [process]
            from config import testingconf
            c.IBConnection.AddProcess =testingconf.ADDPROCESS
        except:
            c.IBConnection.AddProcess=c.Testing.AddProcess
    else:
        c= Config()
        c.Running.TZINFO=datetime.timezone(datetime.timedelta(hours=-3),'GMT3')
        for k,attr in enumerate( FILE_LIST_TO_RES):
            setattr(c,attr,os.path.abspath(f'./tmp/{k}' ))

        c.File.HistF=os.path.abspath('./data/HistFile.cache')
        c.File.JsonFilename=os.path.abspath('./data/groups.json')

    c.TransactionHandlers.SaveCaches=False
    c.File.LogFile=None
    c.File.LogErrorFile=None
    c.Running.IsTest=True
    c.Running.VerifySaving=VerifySave.DONT
    if useinp & UseInput.WITHINPUT == UseInput.Nothing :
        c.Input.InputSource=None
    else:
        c.Input.InputSource=InputSourceType.IB


    return c


@pytest.fixture(scope="session")
def getremibsrv():
    #if tws.exe process is not running, warn.
    # use process_iter to find the process
    RemoteProcess().run_additional_process()
    if not checkIfProcessRunning(config.Running.TwsProcessName):
         logging.warning("TWS is not running. Please run it before running tests")


    time.sleep(3)
    return IBSource(host='127.0.0.1', port=config.Sources.IBSource.PortIB, proxy=True)
