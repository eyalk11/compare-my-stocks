"""Tests for the IB Activity Statement CSV importer.

The real-statement tests are gated on the ``IB_STATEMENT_CSV`` env var
(point it at any IB Activity Statement export) — the file itself is not
committed because it contains an account number. A synthetic fixture
covers the closed-out L/T-realized fallback path unconditionally.
"""
import datetime
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from transactions.ibstatementhandler import parse_ib_statement


_REAL_PATH = os.environ.get("IB_STATEMENT_CSV")
REAL_STATEMENT = Path(_REAL_PATH) if _REAL_PATH else None


@pytest.mark.skipif(not (REAL_STATEMENT and REAL_STATEMENT.exists()), reason="real IB statement not present")
class TestRealStatementParse:
    """Parse the env-pointed real statement and verify the structural claims
    we make in the importer."""

    @classmethod
    def setup_class(cls):
        cls.period, cls.opens, cls.realized = parse_ib_statement(str(REAL_STATEMENT))

    def test_period_extracted(self):
        assert self.period.date() == datetime.date(2026, 4, 29)

    def test_only_stocks_in_open_positions(self):
        # Real file has Stocks + Equity-and-Index-Options; we keep only stocks.
        assert len(self.opens) == 36
        assert all(o.asset_category == "Stocks" for o in self.opens)
        # Options line "CRWV 18SEP26 110 C" must not be present.
        assert not any("18SEP26" in o.symbol for o in self.opens)

    def test_specific_open_position(self):
        amd = next(o for o in self.opens if o.symbol == "AMD")
        assert amd.currency == "USD"
        assert float(amd.quantity) == 70
        assert float(amd.cost_price) == pytest.approx(120.284320714)
        assert float(amd.cost_basis) == pytest.approx(8419.90245)

    def test_non_usd_currency_preserved(self):
        wizz = next(o for o in self.opens if o.symbol == "WIZZ")
        assert wizz.currency == "GBP"

    def test_realized_section_stocks_only(self):
        assert len(self.realized) == 36
        assert all(r.asset_category == "Stocks" for r in self.realized)

    def test_no_lt_realized_in_this_period(self):
        # All stocks in this statement are unrealized — sanity-check that
        # the closed-out branch produces nothing here.
        assert all(
            float(r.lt_profit or 0) + float(r.lt_loss or 0) == 0
            for r in self.realized
        )


@pytest.mark.skipif(not (REAL_STATEMENT and REAL_STATEMENT.exists()), reason="real IB statement not present")
class TestRealStatementBuydict:
    """End-to-end: real CSV -> populated buydict via the handler.

    The handler subclasses TrasnasctionHandler whose __init__ pulls config
    via config.TransactionHandlers.IBStatement. We bypass __init__ and
    populate just the fields populate_buydic actually uses.
    """

    @classmethod
    def setup_class(cls):
        from transactions.ibstatementhandler import IBStatementTransactionHandler

        h = IBStatementTransactionHandler.__new__(IBStatementTransactionHandler)
        h._buydic = {}
        h._buysymbols = set()
        h._manager = _StubManager()
        h.read_statement(str(REAL_STATEMENT))
        cls.handler = h

    def test_buydic_size_matches_open_stock_count(self):
        # 36 open-position stocks; no closed-out L/T entries in this file.
        assert len(self.handler._buydic) == 36

    def test_buy_symbols_include_known_holdings(self):
        for sym in ["AMD", "AMZN", "GOOGL", "WIZZ", "TSLA"]:
            assert sym in self.handler._buysymbols

    def test_amd_buydict_entry(self):
        amd_entries = [
            (k, v) for k, v in self.handler._buydic.items() if v.Symbol == "AMD"
        ]
        assert len(amd_entries) == 1
        _, item = amd_entries[0]
        assert item.Qty == 70.0
        assert item.Cost == pytest.approx(120.284320714)
        assert "open position" in item.Notes

    def test_no_zero_qty_entries_in_this_file(self):
        # No closed-out positions in this period -> no Qty=0 entries.
        assert all(v.Qty != 0 for v in self.handler._buydic.values())

    def test_currency_property_recorded(self):
        info = self.handler._manager.symbol_info
        assert info.get("AMD", {}).get("currency") == "USD"
        assert info.get("WIZZ", {}).get("currency") == "GBP"


class TestClosedOutLTRealized:
    """Synthetic fixture: a closed-out stock with L/T realized profit must
    be emitted as a Qty=0 sell carrying the net L/T amount in Cost."""

    @classmethod
    def setup_class(cls):
        cls.csv = (
            'Statement,Header,Field Name,Field Value\n'
            'Statement,Data,Period,"April 29, 2026"\n'
            'Open Positions,Header,DataDiscriminator,Asset Category,Currency,Symbol,Quantity,Mult,Cost Price,Cost Basis,Close Price,Value,Unrealized P/L,Code\n'
            'Open Positions,Data,Summary,Stocks,USD,AMD,10,1,100,1000,150,1500,500,\n'
            'Realized & Unrealized Performance Summary,Header,Asset Category,Symbol,Cost Adj.,Realized S/T Profit,Realized S/T Loss,Realized L/T Profit,Realized L/T Loss,Realized Total,Unrealized S/T Profit,Unrealized S/T Loss,Unrealized L/T Profit,Unrealized L/T Loss,Unrealized Total,Total,Code\n'
            'Realized & Unrealized Performance Summary,Data,Stocks,AMD,0,0,0,0,0,0,0,0,500,0,500,500,\n'
            'Realized & Unrealized Performance Summary,Data,Stocks,GOOG,0,0,0,1234.5,-100,1134.5,0,0,0,0,0,1134.5,\n'
            'Realized & Unrealized Performance Summary,Data,Stocks,FLAT,0,0,0,0,0,0,0,0,0,0,0,0,\n'
        )

    def test_closed_out_emits_zero_qty_with_net_lt(self, tmp_path):
        path = tmp_path / "stmt.csv"
        path.write_text(self.csv, encoding="utf-8")

        from transactions.ibstatementhandler import IBStatementTransactionHandler

        h = IBStatementTransactionHandler.__new__(IBStatementTransactionHandler)
        h._buydic = {}
        h._buysymbols = set()
        h._manager = _StubManager()
        h.read_statement(str(path))

        amd = [v for v in h._buydic.values() if v.Symbol == "AMD"]
        goog = [v for v in h._buydic.values() if v.Symbol == "GOOG"]
        flat = [v for v in h._buydic.values() if v.Symbol == "FLAT"]

        # AMD has open position → real qty entry, no closed-out duplicate.
        assert len(amd) == 1 and amd[0].Qty == 10

        # GOOG has only realized L/T (1234.5 + (-100) = 1134.5), no open
        # position → synthetic Qty=0 entry with Cost == net L/T.
        assert len(goog) == 1
        assert goog[0].Qty == 0
        assert goog[0].Cost == pytest.approx(1134.5)
        assert "closed L/T" in goog[0].Notes

        # FLAT has zero realized → no entry at all.
        assert flat == []


import collections


class _StubManager:
    """Minimal stand-in for TransactionHandlerManager — read_statement only
    touches symbol_info via update_sym_property, which performs
    ``self._manager.symbol_info[symbol][prop] = value``."""
    def __init__(self):
        self.symbol_info = collections.defaultdict(dict)
