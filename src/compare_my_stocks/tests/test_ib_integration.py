"""Integration test for IBTransactionHandler with a mocked ibflex client.

Builds a non-trivial set of fake Trade objects (multiple symbols, currencies,
duplicate timestamps to exercise the `+= timedelta(seconds=1)` dedup branch,
and one cross-listed conid) and runs the handler end-to-end with both
download + parser mocked. No network and no on-disk cache file is touched.
"""
import collections
import datetime as _dt
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import UseCache
from transactions.IBtransactionhandler import IBTransactionHandler
from transactions.transactioninterface import TransactionSource


def _trade(tid, dt, sym, qty, price, currency="USD", conid="100", exchange="NASDAQ"):
    return SimpleNamespace(
        tradeID=tid,
        dateTime=dt,
        symbol=sym,
        quantity=qty,
        tradePrice=price,
        currency=currency,
        conid=conid,
        exchange=exchange,
    )


@pytest.fixture
def fake_trades():
    base = _dt.datetime(2026, 1, 15, 14, 30, 0)
    return [
        _trade("T1", base, "AAPL", 10, 150.5, "USD", "265598", "NASDAQ"),
        # Same symbol, later trade
        _trade("T2", base + _dt.timedelta(days=2), "AAPL", -4, 162.0, "USD", "265598", "NASDAQ"),
        # GBP-denominated
        _trade("T3", base + _dt.timedelta(days=5), "WIZZ", 100, 22.75, "GBP", "126539083", "LSE"),
        # Two trades at the EXACT SAME timestamp -> exercises the +=1s dedup
        _trade("T4", base + _dt.timedelta(days=10), "MSFT", 5, 380.0, "USD", "272093", "NASDAQ"),
        _trade("T5", base + _dt.timedelta(days=10), "GOOGL", 2, 140.0, "USD", "208813720", "NASDAQ"),
        # Sell of MSFT
        _trade("T6", base + _dt.timedelta(days=20), "MSFT", -2, 410.0, "USD", "272093", "NASDAQ"),
    ]


def _make_handler(manager):
    h = IBTransactionHandler.__new__(IBTransactionHandler)
    h._manager = manager
    h._buydic = {}
    h._buysymbols = set()
    h._tradescache = {}
    h._cache_date = None
    h.need_to_save = False
    h.DoQuery = True
    h.query_id = "FAKE_QUERY"
    h.token_id = "FAKE_TOKEN"
    h.Use = UseCache.DONT
    h.CacheSpan = _dt.timedelta(hours=5)
    h.TryToQueryAnyway = True
    h.QueryIfOlderThan = _dt.timedelta(days=3)
    h.NAME = "IB"
    # Bypass the OnlyNewerThanIBStatement filter so synthetic trades aren't
    # silently dropped by the WhenGenerated cutoff.
    h._ibstatement_cutoff = lambda: None
    return h


def test_ib_populate_buydic_with_mocked_client(fake_trades):
    manager = MagicMock()
    manager.symbol_info = collections.defaultdict(dict)

    handler = _make_handler(manager)

    fake_response = b"<FlexQueryResponse/>"
    fake_parsed = SimpleNamespace(
        FlexStatements=[SimpleNamespace(Trades=fake_trades)]
    )

    with patch(
        "transactions.IBtransactionhandler.client.download",
        return_value=fake_response,
    ) as m_download, patch(
        "transactions.IBtransactionhandler.parser.parse",
        return_value=fake_parsed,
    ) as m_parse:
        handler.populate_buydic()

    m_download.assert_called_once_with("FAKE_TOKEN", "FAKE_QUERY")
    m_parse.assert_called_once_with(fake_response)

    # All trades cached and emitted
    assert len(handler._tradescache) == len(fake_trades)
    assert len(handler._buydic) == len(fake_trades)
    assert handler._buysymbols == {"AAPL", "WIZZ", "MSFT", "GOOGL"}

    # Source + symbol fidelity
    for item in handler._buydic.values():
        assert item.Source == TransactionSource.IB
        assert item.Notes == "IB"
        assert item.Symbol in handler._buysymbols

    # AAPL buy + sell preserved with their own qty/price
    aapl = sorted(
        (k, v) for k, v in handler._buydic.items() if v.Symbol == "AAPL"
    )
    assert len(aapl) == 2
    assert aapl[0][1].Qty == 10 and aapl[0][1].Cost == 150.5
    assert aapl[1][1].Qty == -4 and aapl[1][1].Cost == 162.0

    # The same-timestamp pair (MSFT buy + GOOGL buy at base+10d) collide:
    # populate_buydic shifts the second by +1s so both are kept.
    base = _dt.datetime(2026, 1, 15, 14, 30, 0)
    collision = base + _dt.timedelta(days=10)
    keys_at_collision = sorted(
        k for k, v in handler._buydic.items()
        if k in (collision, collision + _dt.timedelta(seconds=1))
    )
    assert keys_at_collision == [collision, collision + _dt.timedelta(seconds=1)]

    # symbol_info populated for currency / conId / exchange
    info = manager.symbol_info
    assert info["AAPL"]["currency"] == "USD"
    assert info["AAPL"]["conId"] == "265598"
    assert info["AAPL"]["exchange"] == "NASDAQ"
    assert info["WIZZ"]["currency"] == "GBP"
    assert info["WIZZ"]["exchange"] == "LSE"


def test_ib_populate_buydic_uses_existing_cache(fake_trades):
    """When useable cache is present and TryToQueryAnyway is off, the
    download path is not hit but the cached trades still feed buydict."""
    manager = MagicMock()
    manager.symbol_info = collections.defaultdict(dict)

    handler = _make_handler(manager)
    handler.TryToQueryAnyway = False
    handler.Use = UseCache.FORCEUSE
    handler._cache_date = _dt.datetime.now()
    handler._tradescache = {t.tradeID: t for t in fake_trades}

    with patch(
        "transactions.IBtransactionhandler.client.download"
    ) as m_download:
        handler.populate_buydic()

    m_download.assert_not_called()
    assert len(handler._buydic) == len(fake_trades)
    assert handler._buysymbols == {"AAPL", "WIZZ", "MSFT", "GOOGL"}
