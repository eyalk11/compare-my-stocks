"""Focused unit tests for StockPrices.populate_buydic / get_hist_split."""
from collections import OrderedDict
from unittest.mock import patch

import pytest

from transactions.stockprices import StockPrices

def _has_rapid_yf_key():
    try:
        from config import config
        return bool(getattr(config.Jupyter, 'RapidYFinanaceKey', ''))
    except Exception:
        return False
_HAS_YF = _has_rapid_yf_key()


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
    """When the RapidAPI returns an empty data array, get_hist_split yields nothing."""
    sp = _make_sp([])

    from config import config
    monkeypatch.setattr(config.Jupyter, 'RapidYFinanaceKey', 'fake-key', raising=False)

    class _FakeResp:
        status = 200
        def read(self):
            import json as _json
            return _json.dumps({"data": [], "status": 200, "message": "Success!"}).encode()

    class _FakeConn:
        def __init__(self, *a, **kw): pass
        def request(self, *a, **kw): pass
        def getresponse(self): return _FakeResp()

    import http.client
    monkeypatch.setattr(http.client, "HTTPSConnection", _FakeConn)
    assert list(sp.get_hist_split("NOSPLITS")) == []


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_YF, reason="RapidYFinanaceKey not configured")
def test_get_hist_split_live_tsla(monkeypatch):
    """Live test: RapidAPI yfinance must return the two well-known TSLA splits:
    5-for-1 on 2020-08-31 and 3-for-1 on 2022-08-25."""
    from config import config
    monkeypatch.setattr(config.Running, 'UseYFinance', True, raising=False)
    sp = _make_sp([])
    splits = list(sp.get_hist_split("TSLA"))
    by_date = {dt.date().isoformat(): ratio for dt, ratio in splits}
    assert by_date.get("2020-08-31") == 5.0
    assert by_date.get("2022-08-25") == 3.0


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_YF, reason="RapidYFinanaceKey not configured")
def test_populate_buydic_live_tsla(monkeypatch):
    """End-to-end: populate_buydic on TSLA should yield both splits, sorted."""
    from config import config
    monkeypatch.setattr(config.Running, 'UseYFinance', True, raising=False)
    sp = _make_sp(["TSLA"])
    sp.populate_buydic()
    dates = [d.date().isoformat() for d in sp._buydic["TSLA"].keys()]
    assert "2020-08-31" in dates
    assert "2022-08-25" in dates
    assert dates == sorted(dates)
