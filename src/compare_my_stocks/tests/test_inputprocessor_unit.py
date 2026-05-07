"""Unit tests for InputProcessor.get_status_df and InputProcessor.get_hist_sym.

Both functions are exercised without spinning up the full engine — we build an
InputProcessor via __new__ and stub the few dependencies they touch.
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from input.inputprocessor import InputProcessor
from common.common import InputSourceType
from config import config


# ============================================================================
# helpers
# ============================================================================

def _bare_inp():
    """Build an InputProcessor without running __init__ — only the attributes
    referenced by the tested method are populated."""
    inp = object.__new__(InputProcessor)
    return inp


# ============================================================================
# get_status_df
# ============================================================================

def test_get_status_df_non_ib_returns_current_status(monkeypatch):
    """When InputSource is not IB, get_status_df just returns _data._current_status."""
    inp = _bare_inp()
    df = pd.DataFrame({"name": ["AAA"], "shares": [10]}).set_index("name")
    inp.data = SimpleNamespace(_current_status=df)
    inp._inputsource = None
    monkeypatch.setattr(config.Input, "InputSource", InputSourceType.Cache, raising=False)
    out = inp.get_status_df()
    assert out is df


def test_get_status_df_ib_no_inputsource_returns_current_status(monkeypatch):
    """IB configured but inputsource is None → still falls back to current_status."""
    inp = _bare_inp()
    df = pd.DataFrame({"name": ["AAA"], "shares": [10]}).set_index("name")
    inp.data = SimpleNamespace(_current_status=df)
    inp._inputsource = None
    monkeypatch.setattr(config.Input, "InputSource", InputSourceType.IB, raising=False)
    out = inp.get_status_df()
    assert out is df


def test_get_status_df_ib_empty_port_returns_current_status(monkeypatch):
    """If get_port_stock_ex() yields an empty list, return original df unmodified."""
    inp = _bare_inp()
    df = pd.DataFrame({"name": ["AAA"], "shares": [10]}).set_index("name")
    inp.data = SimpleNamespace(_current_status=df)
    inp._inputsource = MagicMock()
    inp.get_port_stock_ex = MagicMock(return_value=[])
    monkeypatch.setattr(config.Input, "InputSource", InputSourceType.IB, raising=False)
    out = inp.get_status_df()
    assert out is df


def test_get_status_df_ib_joins_position(monkeypatch):
    """With IB and a populated portfolio, the result joins IB Position/AvgConst columns."""
    inp = _bare_inp()
    df = pd.DataFrame({"name": ["AAA", "BBB"], "shares": [10, 20]}).set_index("name")
    inp.data = SimpleNamespace(_current_status=df)
    inp._inputsource = MagicMock()
    inp.get_port_stock_ex = MagicMock(return_value=[
        {"symbol": "AAA", "position": 100, "avgCost": 1.5, "currency": "USD"},
        {"symbol": "BBB", "position": 50, "avgCost": 2.0, "currency": "USD"},
    ])
    monkeypatch.setattr(config.Input, "InputSource", InputSourceType.IB, raising=False)
    out = inp.get_status_df()
    assert "IB Position" in out.columns
    assert "IB AvgConst" in out.columns
    assert out.loc["AAA", "IB Position"] == 100
    assert out.loc["BBB", "IB AvgConst"] == 2.0


# ============================================================================
# get_hist_sym
# ============================================================================

def _hist_df():
    idx = pd.DatetimeIndex([
        datetime.datetime(2024, 1, 2),
        datetime.datetime(2024, 1, 3),
        datetime.datetime(2024, 1, 4),
    ])
    return pd.DataFrame(
        {"Open": [100.0, 101.0, 102.0], "Close": [101.0, 102.0, 103.0]},
        index=idx,
    )


def test_get_hist_sym_no_inputsource_returns_zero():
    inp = _bare_inp()
    inp._inputsource = None
    assert inp.get_hist_sym(
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 5),
        "AAA", "AAA",
    ) == 0


def test_get_hist_sym_none_history_returns_zero(monkeypatch):
    inp = _bare_inp()
    inp._inputsource = MagicMock()
    inp._inputsource.get_symbol_history.return_value = ({}, None)
    inp.data = SimpleNamespace(symbol_info={}, _hist_by_date={}, _usable_symbols=set())
    monkeypatch.setattr(config.Symbols, "Crypto", set(), raising=False)
    out = inp.get_hist_sym(
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 5),
        "AAA", "AAA",
    )
    assert out == 0


def test_get_hist_sym_empty_history_returns_zero(monkeypatch):
    inp = _bare_inp()
    inp._inputsource = MagicMock()
    inp._inputsource.get_symbol_history.return_value = ({}, pd.DataFrame())
    inp.data = SimpleNamespace(symbol_info={}, _hist_by_date={}, _usable_symbols=set())
    monkeypatch.setattr(config.Symbols, "Crypto", set(), raising=False)
    out = inp.get_hist_sym(
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 5),
        "AAA", "AAA",
    )
    assert out == 0


def test_get_hist_sym_populates_hist_by_date(monkeypatch):
    """Happy path: real DataFrame returned → days written into _hist_by_date and
    okdays returned (non-NaN Open count)."""
    inp = _bare_inp()
    inp._inputsource = MagicMock()
    info = {"exchange": "NASDAQ", "currency": "USD"}
    inp._inputsource.get_symbol_history.return_value = (info, _hist_df())

    class _Data:
        def __init__(self):
            self.symbol_info = {}
            self._hist_by_date = {}
            self._usable_symbols = set()

        def get_currency_for_sym(self, sym):
            return "USD"

    inp.data = _Data()
    monkeypatch.setattr(config.Symbols, "Crypto", set(), raising=False)
    monkeypatch.setattr(config.Symbols, "ExchangeCurrency", {}, raising=False)
    monkeypatch.setattr(config.Symbols, "Basecur", "USD", raising=False)

    okdays = inp.get_hist_sym(
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 5),
        "AAA", "AAA",
    )
    assert okdays == 3
    assert "AAA" in inp.data._usable_symbols
    # All three days written
    assert len(inp.data._hist_by_date) == 3
    for date, syms in inp.data._hist_by_date.items():
        assert "AAA" in syms
        # base currency USD → adjusted side is None
        dic, adjusted = syms["AAA"]
        assert adjusted is None


def test_get_hist_sym_applies_exchange_currency_override(monkeypatch):
    """ExchangeCurrency override (e.g. LSE pence) takes precedence over IB info."""
    inp = _bare_inp()
    inp._inputsource = MagicMock()
    info = {"exchange": "LSE", "currency": "GBP"}
    inp._inputsource.get_symbol_history.return_value = (info, _hist_df())

    class _Data:
        def __init__(self):
            self.symbol_info = {}
            self._hist_by_date = {}
            self._usable_symbols = set()

        def get_currency_for_sym(self, sym):
            return None

    inp.data = _Data()
    inp.get_adjusted_df_for_currency = MagicMock(return_value=_hist_df())
    monkeypatch.setattr(config.Symbols, "Crypto", set(), raising=False)
    monkeypatch.setattr(config.Symbols, "ExchangeCurrency", {"LSE": "GBp"}, raising=False)
    monkeypatch.setattr(config.Symbols, "Basecur", "USD", raising=False)

    inp.get_hist_sym(
        datetime.datetime(2024, 1, 1),
        datetime.datetime(2024, 1, 5),
        "AAA", "AAA",
    )
    # currency override stored
    assert inp.data.symbol_info["AAA"]["currency"] == "GBp"
    # And adjusted_df was requested (because GBp != USD base)
    inp.get_adjusted_df_for_currency.assert_called_once()
