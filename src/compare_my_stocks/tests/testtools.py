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
    # Force File.HistF / JsonFilename to point at the in-tree
    # src/compare_my_stocks/data/ directory and assert nothing in that
    # directory is modified during the test. Same contract as
    # startvenv11_curdat.ps1, which copies the data dir to C:\temp\data
    # so the live install never touches the in-tree files.
    USEDATADIR=auto()
    # Replace the engine's IBSource with a deterministic synthetic source
    # (no IB Gateway required). Composable with USEDATADIR / LOADDEFAULTCONFIG
    # so the rest of the stack — config, groups.json, transaction handlers,
    # InputProcessor, DataGenerator, GraphGenerator — runs against real code
    # paths but with fake price data. Mirrors make_synthetic_prices in
    # test_generic_graph and the mocked-client style of test_ib_integration.
    MOCKIB=auto()


# Absolute path to src/compare_my_stocks/data/ (the in-tree default data
# dir). Tests that pin File paths here MUST NOT mutate these files.
DATADIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
)


def _hash_datadir(data_dir=DATADIR):
    """Return {relpath: sha256-hex} for every file currently in data_dir.
    Subdirs (e.g. data/jupyter) are walked too."""
    import hashlib
    out = {}
    for root, _dirs, files in os.walk(data_dir):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, data_dir)
            with open(full, "rb") as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


def make_synthetic_ibsource(seed: int = 0, base_price: float = 100.0,
                            daily_vol: float = 0.02):
    """Deterministic stand-in for IBSource. ``get_symbol_history(sym, start,
    end, iscrypto)`` returns ``(meta, ohlcv_df)`` for any symbol — the price
    series is a per-symbol seeded random walk with business-day frequency,
    same shape as IBSource.historicalhelper output (Open/High/Low/Close/
    volume + datetime index).

    Composable with the rest of the engine path: drop into
    ``eng.input_processor._inputsource`` (or pass via UseInput.MOCKIB) and
    the InputProcessor → DataGenerator → GraphGenerator chain runs end-to-end
    without an IB Gateway. Mirrors the synthetic-data pattern in
    ``tests/test_generic_graph.py::make_synthetic_prices`` and the
    mocked-client pattern in ``tests/test_ib_integration.py``."""
    import hashlib
    import datetime as _dt
    import numpy as _np
    import pandas as _pd
    from unittest.mock import MagicMock

    def _seed_for(sym: str) -> int:
        h = hashlib.sha1(sym.encode()).digest()
        return seed ^ int.from_bytes(h[:4], "big")

    def get_symbol_history(sym, startdate, enddate, iscrypto=False):
        if hasattr(startdate, "to_pydatetime"):
            startdate = startdate.to_pydatetime()
        if hasattr(enddate, "to_pydatetime"):
            enddate = enddate.to_pydatetime()
        idx = _pd.bdate_range(startdate, enddate)
        if len(idx) == 0:
            idx = _pd.bdate_range(startdate, startdate + _dt.timedelta(days=2))
        n = len(idx)
        rng = _np.random.default_rng(_seed_for(str(sym)))
        steps = rng.normal(loc=0.0005, scale=daily_vol, size=n)
        close = base_price * _np.exp(_np.cumsum(steps))
        open_ = _np.r_[close[0], close[:-1]]
        high = _np.maximum(open_, close) * (1 + rng.uniform(0, 0.005, n))
        low = _np.minimum(open_, close) * (1 - rng.uniform(0, 0.005, n))
        vol = rng.integers(1_000_000, 5_000_000, n).astype(float)
        df = _pd.DataFrame(
            {"Open": open_, "High": high, "Low": low, "Close": close, "volume": vol},
            index=idx,
        )
        meta = {
            "currency": "USD",
            "conId": str(abs(hash(str(sym))) % 10**8),
            "exchange": "NASDAQ",
            "secType": "STK",
            "symbol": str(sym),
            "contract": {"symbol": str(sym), "exchange": "NASDAQ", "currency": "USD"},
        }
        return meta, df

    src = MagicMock(name="SyntheticIBSource")
    src.get_symbol_history.side_effect = get_symbol_history
    src.get_current_currency.return_value = 1.0
    src.get_currency_history.return_value = None
    src.get_positions.return_value = []
    src.disconnect.return_value = None
    return src


@pytest.fixture
def assert_datadir_unchanged():
    """Snapshot hashes of every file under DATADIR before the test, then
    on teardown assert nothing in that tree was added/removed/modified."""
    before = _hash_datadir()
    yield before
    after = _hash_datadir()
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in (set(before) & set(after)) if before[k] != after[k])
    assert not (added or removed or changed), (
        f"DATADIR was modified during the test:\n"
        f"  added={added}\n  removed={removed}\n  changed={changed}"
    )


@pytest.fixture
def mock_config_to_default(useinp : UseInput):
    ConfigLoader.config.update_from(generate_config(useinp),all=True)

    #with mock_patch('config.newconfig.ConfigLoader.config' ,generate_config(useinp)):
    #    yield


@pytest.fixture(scope="session")
def mock_config_to_default_alt():
    ConfigLoader.config.update_from(generate_config(UseInput.LOADDEFAULTCONFIG),all=True)

@pytest.fixture(scope="session")
def mock_config_to_default_sess():
    ConfigLoader.config.update_from(generate_config(UseInput.Nothing),all=True)


@pytest.fixture(scope="session")
def IBSourceSess():
    x = IBSource(host='127.0.0.1', port=config.Sources.IBSource.PortIB,proxy=False)
    return x


@pytest.fixture(scope="session")
@pytest.mark.usefixtures("mock_config_to_default_sess")
def inp(IBSourceSess):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = IBSourceSess
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,InputSource)
    tmpinp.data= InputDataImpl(semaphore=tmpinp._semaphore)
    tr._inp=tmpinp
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
    #tmpinp.save_data = Mock(return_value=None)
    return tmpinp

@pytest.fixture
def inpb(IBSourceSess):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = IBSourceSess
    config.TransactionHandlers.SaveCaches=False
    tr=TransactionHandlerManager(None)
    tmpinp = InputProcessor(eng, tr,InputSource)
    tmpinp.data= InputDataImpl(semaphore=tmpinp._semaphore)
    tr._inp=tmpinp
    tmpinp.process_params= copy(eng.params)
    tmpinp.process_params.use_cache=UseCache.FORCEUSE
    tmpinp.save_data = Mock(return_value=None)
    return tmpinp
@pytest.fixture
def PolySourceFix():
    return PolySource()

@pytest.fixture
def inp_poly(PolySourceFix):
    eng=MagicMock()
    eng.params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
        show_graph=False)
    InputSource = PolySourceFix
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
    eng = get_eng()

    return eng


def get_eng(have_graph_gen=False,params : Parameters=None):
    eng = CompareEngine(None)
    eng.transaction_handler.save_cache = Mock(return_value=None)
    eng.transaction_handler._ib.save_cache = Mock(return_value=None)
    eng.transaction_handler._stock.save_cache = Mock(return_value=None)
    eng.transaction_handler._StockPrices.save_cache = Mock(return_value=None)
    if params is None:
        eng.params = Parameters(
            type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True, groups=['FANG'], use_cache=UseCache.DONT,
            show_graph=False)
    else:
        eng.params=params
    if not have_graph_gen:
        eng.call_graph_generator = Mock(return_value=None)
        # Without real axes, gen_graph() bails on `if not self._generator.active`
        # (added in d160805) and never reaches call_graph_generator, so the Mock
        # never records. Plant a sentinel _axes so .active returns True for tests.
        eng._generator._axes = Mock()
        eng._generator._plot = Mock()  # pyqtgraph backend reads _plot, not _axes
    eng.input_processor.save_data = Mock(
        return_value=None)  # Dont save anything please . Because loading data like that is not nice.
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
            c.Sources.IBSource.AddProcess =testingconf.ADDPROCESS
        except:
            c.Sources.IBSource.AddProcess=c.Testing.AddProcess
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
    c.TransactionHandlers.IB.PromptOnQueryFail=False
    c.Sources.IBSource.PromptOnConnectionFail=False
    if useinp & UseInput.WITHINPUT == UseInput.Nothing :
        c.Input.InputSource=None
    else:
        c.Input.InputSource=InputSourceType.IB

    if useinp & UseInput.USEDATADIR:
        # Pin file paths at the in-tree data dir (absolute), regardless of
        # which config branch above ran. The matching assert_datadir_unchanged
        # fixture guarantees nothing here is mutated by the test.
        c.File.HistF = os.path.join(DATADIR, "HistFile.cache")
        c.File.JsonFilename = os.path.join(DATADIR, "groups.json")

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
