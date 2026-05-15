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


# ============================================================================
# InputProcessor.return_df — time-interpolated earnings spread.
# Replaces the previous monthly bfill/ffill step function with a time-
# weighted linear interpolation between known earnings anchors, ffilled
# past the last anchor and left NaN before the first (no look-ahead).
# ============================================================================

def _build_panels(price_dates, prices_by_sym, earnings_dates, earnings_by_sym):
    """Helper: build the (mpl-num indexed) daily price panel and the
    Timestamp-indexed quarterly earnings panel that return_df expects."""
    import numpy as np
    from matplotlib.dates import date2num
    idx = [date2num(d.to_pydatetime()) for d in pd.bdate_range(*price_dates)]
    prices = pd.DataFrame(
        {sym: np.linspace(*span, num=len(idx))
         for sym, span in prices_by_sym.items()},
        index=idx,
    )
    earnings = pd.DataFrame(
        earnings_by_sym, index=pd.to_datetime(earnings_dates),
    )
    return prices, earnings


def test_return_df_time_interpolates_between_anchors():
    """Between two known earnings reports, the divisor must follow a straight
    time-weighted line from the earlier anchor to the later one — not a step
    at month boundaries. Probe a date roughly 1/3 of the way from Mar to Jun
    and assert the divisor matches the time-weighted blend."""
    from matplotlib.dates import date2num
    prices, earnings = _build_panels(
        ("2026-01-01", "2026-08-31"),
        {"AAPL": (150.0, 200.0)},
        ["2026-03-01", "2026-06-01"],   # 92 days apart
        {"AAPL": [25.0, 28.0]},          # +3.0 over 92 days
    )

    out = InputProcessor.return_df(prices, earnings, "peratio")

    # Mid-April: ~45 days past Mar-1 anchor, ~47 days before Jun-1.
    # Expected divisor = 25 + (45/92) * 3
    probe = pd.Timestamp("2026-04-15")
    days_from_mar = (probe - pd.Timestamp("2026-03-01")).days
    span = (pd.Timestamp("2026-06-01") - pd.Timestamp("2026-03-01")).days
    expected_divisor = 25.0 + (days_from_mar / span) * (28.0 - 25.0)

    probe_mpl = date2num(probe.to_pydatetime())
    nearest = min(out.index, key=lambda x: abs(x - probe_mpl))
    expected_ratio = prices.loc[nearest, "AAPL"] / expected_divisor
    assert out.loc[nearest, ("peratio", "AAPL")] == pytest.approx(
        expected_ratio, rel=1e-3
    ), "interpolation between anchors must be time-weighted linear"


def test_return_df_leaves_pre_first_anchor_nan():
    """Dates before the first reported quarter must stay NaN — no bfill, so
    we never silently borrow a future-reported earnings figure (no look-ahead)."""
    from matplotlib.dates import date2num
    prices, earnings = _build_panels(
        ("2026-01-01", "2026-08-31"),
        {"AAPL": (150.0, 200.0)},
        ["2026-03-01", "2026-06-01"],
        {"AAPL": [25.0, 28.0]},
    )

    out = InputProcessor.return_df(prices, earnings, "peratio")

    probe = date2num(pd.Timestamp("2026-01-15").to_pydatetime())
    nearest = min(out.index, key=lambda x: abs(x - probe))
    assert pd.isna(out.loc[nearest, ("peratio", "AAPL")]), \
        "pre-first-anchor dates must be NaN (no look-ahead bfill)"


def test_return_df_ffills_past_last_anchor():
    """After the last reported quarter, the last known earnings figure
    carries forward (constant divisor) — interpolation can't extrapolate
    so ffill is the safe default."""
    from matplotlib.dates import date2num
    prices, earnings = _build_panels(
        ("2026-01-01", "2026-08-31"),
        {"AAPL": (150.0, 200.0)},
        ["2026-03-01", "2026-06-01"],
        {"AAPL": [25.0, 28.0]},
    )

    out = InputProcessor.return_df(prices, earnings, "peratio")

    probe = date2num(pd.Timestamp("2026-08-15").to_pydatetime())
    nearest = min(out.index, key=lambda x: abs(x - probe))
    expected = prices.loc[nearest, "AAPL"] / 28.0
    assert out.loc[nearest, ("peratio", "AAPL")] == pytest.approx(expected, rel=1e-9), \
        "past-last-anchor must ffill the last known earnings value"


def test_return_df_clamps_negative_ratios_to_zero():
    """Negative earnings (loss period) → ratio clamped to 0 by `cur[cur<0]=0`."""
    from matplotlib.dates import date2num
    prices, earnings = _build_panels(
        ("2026-01-01", "2026-08-31"),
        {"LOSS": (100.0, 100.0)},
        ["2026-03-01", "2026-06-01"],
        {"LOSS": [-5.0, -3.0]},
    )
    out = InputProcessor.return_df(prices, earnings, "peratio")
    interior_idx = [
        i for i in out.index
        if date2num(pd.Timestamp("2026-04-01").to_pydatetime())
        <= i
        <= date2num(pd.Timestamp("2026-06-01").to_pydatetime())
    ]
    interior = out.loc[interior_idx, ("peratio", "LOSS")]
    assert (interior == 0).all(), \
        f"negative earnings must clamp to 0, got {interior.unique()}"


def test_return_df_output_shape_and_columns():
    """Structural sanity: MultiIndex columns, output reindexed onto every
    original price date, and the symbol set preserved."""
    prices, earnings = _build_panels(
        ("2026-01-01", "2026-08-31"),
        {"AAPL": (150.0, 200.0), "MSFT": (400.0, 450.0)},
        ["2026-03-01", "2026-06-01"],
        {"AAPL": [25.0, 28.0], "MSFT": [80.0, 85.0]},
    )

    out = InputProcessor.return_df(prices, earnings, "pricesells")

    assert isinstance(out.columns, pd.MultiIndex)
    assert list(out.columns.get_level_values(0).unique()) == ["pricesells"]
    assert set(out.columns.get_level_values(1)) == {"AAPL", "MSFT"}
    assert list(out.index) == list(prices.index), \
        "output must be reindexed onto original daily price dates"

