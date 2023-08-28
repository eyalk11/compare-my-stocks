import datetime
import logging
import time
from copy import copy
from enum import Flag, auto
from unittest.mock import MagicMock, Mock

import pytest

from common.common import Types, UniteType, UseCache, InputSourceType, checkIfProcessRunning
from config import config, ConfigLoader, Config
from config.newconfig import FILE_LIST_TO_RES
from engine.compareengine import CompareEngine
from engine.parameters import Parameters
from ib.remoteprocess import RemoteProcess
from input.ibsource import IBSource
from input.inputprocessor import InputProcessor
from transactions.transactionhandlermanager import TransactionHandlerManager


@pytest.fixture(scope="session")
def ibsource():
    x = IBSource(host='127.0.0.1', port=config.IBConnection.PORTIB,proxy=False)
    return x


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
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
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


class UseInput(Flag):
    Nothing=0
    WITHINPUT=auto()
    LOADDEFAULTCONFIG=auto()


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


@pytest.fixture(scope="session")
def getremibsrv():
    #if tws.exe process is not running, warn.
    # use process_iter to find the process
    RemoteProcess().run_additional_process()
    if not checkIfProcessRunning(config.Running.TWS_PROCESS_NAME):
         logging.warning("TWS is not running. Please run it before running tests")


    time.sleep(3)
    return IBSource(host='127.0.0.1', port=config.IBConnection.PORTIB, proxy=True)
