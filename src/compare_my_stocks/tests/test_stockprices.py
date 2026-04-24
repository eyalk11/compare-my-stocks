"""Focused unit tests for StockPrices.populate_buydic / get_hist_split."""
from collections import OrderedDict
from unittest.mock import patch

import pytest

from transactions.stockprices import StockPrices

try:
    import yfinance  # noqa: F401
    _HAS_YF = True
except ImportError:
    _HAS_YF = False


def _make_sp(tickers, ignore=frozenset(), buydic=None):
    """Build a StockPrices instance without running its __init__ / manager wiring."""
    sp = object.__new__(StockPrices)
    sp._tickers = list(tickers)
    sp._buydic = {} if buydic is None else buydic
    sp.IgnoreSymbols = set(ignore)
    return sp


def test_populate_buydic_skips_ignored():
    sp = _make_sp(["AAPL", "BAD"], ignore={"BAD"})
    with patch.object(StockPrices, "get_hist_split", return_value=iter([])):
        sp.populate_buydic()
    assert "AAPL" in sp._buydic
    assert "BAD" not in sp._buydic


def test_populate_buydic_skips_already_cached():
    preset = OrderedDict({"AAPL": OrderedDict({"x": 1})})
    sp = _make_sp(["AAPL"], buydic=preset)
    with patch.object(StockPrices, "get_hist_split") as m:
        sp.populate_buydic()
    m.assert_not_called()
    assert sp._buydic["AAPL"] == {"x": 1}


def test_populate_buydic_handles_get_hist_split_exception():
    """Regression: exception in get_hist_split used to leave `s` unbound
    and crash at s.sort(). It must now be swallowed and loop continues."""
    sp = _make_sp(["AAPL", "MSFT"])

    def raiser(sym):
        if sym == "AAPL":
            raise RuntimeError("boom")
        return iter([])

    with patch.object(StockPrices, "get_hist_split", side_effect=raiser):
        sp.populate_buydic()

    assert "AAPL" not in sp._buydic
    assert "MSFT" in sp._buydic


def test_populate_buydic_adds_splits_sorted():
    sp = _make_sp(["TSLA"])
    splits = [("2022-08-25", 3), ("2020-08-31", 5)]
    with patch.object(StockPrices, "get_hist_split", return_value=iter(splits)):
        sp.populate_buydic()
    dates = list(sp._buydic["TSLA"].keys())
    assert dates == ["2020-08-31", "2022-08-25"]


def test_filter_bad_removes_ignored_from_buydic():
    preset = {"AAPL": OrderedDict(), "BAD": OrderedDict({"d": 1})}
    sp = _make_sp([], ignore={"BAD"}, buydic=preset)
    sp.filter_bad()
    assert "BAD" not in sp._buydic
    assert "AAPL" in sp._buydic


def test_get_hist_split_empty_when_no_splits(monkeypatch):
    """When yfinance returns an empty Series, get_hist_split yields nothing."""
    import pandas as pd
    sp = _make_sp([])

    class _FakeTicker:
        splits = pd.Series(dtype="float64")

    import yfinance
    monkeypatch.setattr(yfinance, "Ticker", lambda sym: _FakeTicker())
    assert list(sp.get_hist_split("NOSPLITS")) == []


@pytest.mark.skipif(not _HAS_YF, reason="yfinance not installed")
def test_get_hist_split_live_tsla():
    """Live test: yfinance must return the two well-known TSLA splits:
    5-for-1 on 2020-08-31 and 3-for-1 on 2022-08-25."""
    sp = _make_sp([])
    splits = list(sp.get_hist_split("TSLA"))
    by_date = {dt.date().isoformat(): ratio for dt, ratio in splits}
    assert by_date.get("2020-08-31") == 5.0
    assert by_date.get("2022-08-25") == 3.0


@pytest.mark.skipif(not _HAS_YF, reason="yfinance not installed")
def test_populate_buydic_live_tsla():
    """End-to-end: populate_buydic on TSLA should yield both splits, sorted."""
    sp = _make_sp(["TSLA"])
    sp.populate_buydic()
    dates = [d.date().isoformat() for d in sp._buydic["TSLA"].keys()]
    assert "2020-08-31" in dates
    assert "2022-08-25" in dates
    assert dates == sorted(dates)
