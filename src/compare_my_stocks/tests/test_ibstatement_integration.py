"""End-to-end integration test for the IBStatement source.

Drives the full ``TransactionHandlerManager`` pipeline with
``TransactionSource = IBStatement`` against a real IB Activity Statement
CSV pointed at by ``IB_STATEMENT_CSV``. The CSV is *not* committed
(it includes an account number).
"""
import collections
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import TransactionSourceType, UseCache
from config import config
from transactions.transactionhandlermanager import TransactionHandlerManager


_REAL_PATH = os.environ.get("IB_STATEMENT_CSV")
REAL_STATEMENT = Path(_REAL_PATH) if _REAL_PATH else None


@pytest.fixture
def ibstatement_only_config():
    """Switch the global config to IBStatement-as-sole-source for this test
    and restore on teardown."""
    saved = (
        config.TransactionHandlers.TransactionSource,
        config.TransactionHandlers.SaveCaches,
        config.TransactionHandlers.IBStatement.Use,
        config.TransactionHandlers.IBStatement.SrcFile,
    )
    config.TransactionHandlers.TransactionSource = TransactionSourceType.IBStatement
    config.TransactionHandlers.SaveCaches = False
    config.TransactionHandlers.IBStatement.Use = UseCache.DONT
    config.TransactionHandlers.IBStatement.SrcFile = str(REAL_STATEMENT)
    try:
        yield
    finally:
        (
            config.TransactionHandlers.TransactionSource,
            config.TransactionHandlers.SaveCaches,
            config.TransactionHandlers.IBStatement.Use,
            config.TransactionHandlers.IBStatement.SrcFile,
        ) = saved


@pytest.mark.skipif(
    not (REAL_STATEMENT and REAL_STATEMENT.exists()),
    reason="set IB_STATEMENT_CSV to an IB Activity Statement CSV to run",
)
def test_ibstatement_only_pipeline(ibstatement_only_config):
    """With TransactionSource=IBStatement, process_transactions should yield
    a buydict populated solely from the statement's Open Positions section."""
    inp = MagicMock()
    inp.symbol_info = collections.defaultdict(dict)

    mgr = TransactionHandlerManager(inp)

    # IB / MyStock handlers must be disabled; IBStatement handler must be wired.
    assert mgr._ib is None
    assert mgr._stock is None
    assert mgr._ibstatement is not None

    # Skip the StockPrices/Earnings post-processing (needs real input data).
    mgr._StockPrices.process_transactions = lambda: None
    mgr._earnings.process_transactions = lambda: None

    mgr.process_transactions()

    # All buydict entries originate from the statement.
    assert len(mgr.buydic) >= 1
    for _, v in mgr.buydic.items():
        assert v.Notes.startswith("IBStatement:")

    # Some recognisable holdings from the env-pointed statement.
    assert mgr.buysymbols  # non-empty
