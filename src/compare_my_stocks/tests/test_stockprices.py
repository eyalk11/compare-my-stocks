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


def test_get_hist_split_disabled_yields_nothing(monkeypatch):
    """UseYFinance=False → generator yields nothing without making any HTTP call."""
    sp = _make_sp([])
    from config import config
    monkeypatch.setattr(config.Running, "UseYFinance", False, raising=False)
    import http.client
    def _boom(*a, **kw):
        raise AssertionError("HTTPSConnection should not be constructed when disabled")
    monkeypatch.setattr(http.client, "HTTPSConnection", _boom)
    assert list(sp.get_hist_split("AAA")) == []


def test_get_hist_split_no_key_yields_nothing(monkeypatch):
    """Missing RapidYFinanaceKey → generator returns without HTTP call."""
    sp = _make_sp([])
    from config import config
    monkeypatch.setattr(config.Running, "UseYFinance", True, raising=False)
    monkeypatch.setattr(config.Jupyter, "RapidYFinanaceKey", "", raising=False)
    import http.client
    def _boom(*a, **kw):
        raise AssertionError("no HTTP without API key")
    monkeypatch.setattr(http.client, "HTTPSConnection", _boom)
    assert list(sp.get_hist_split("AAA")) == []


def test_get_hist_split_parses_splits(monkeypatch):
    """Happy-path: API returns two splits → both yielded as (datetime, ratio)."""
    sp = _make_sp([])
    from config import config
    monkeypatch.setattr(config.Running, "UseYFinance", True, raising=False)
    monkeypatch.setattr(config.Jupyter, "RapidYFinanaceKey", "k", raising=False)

    payload = {
        "data": [
            {"date": 1598832000000, "stockSplits": 5},  # 2020-08-31
            {"date": 1661385600000, "stockSplits": 3},  # 2022-08-25
        ]
    }

    class _Resp:
        status = 200
        def read(self):
            import json as _j
            return _j.dumps(payload).encode()

    class _Conn:
        def __init__(self, *a, **kw): pass
        def request(self, *a, **kw): pass
        def getresponse(self): return _Resp()

    import http.client
    monkeypatch.setattr(http.client, "HTTPSConnection", _Conn)
    out = list(sp.get_hist_split("TSLA"))
    assert [r for _, r in out] == [5.0, 3.0]


def test_get_hist_split_non_200_yields_nothing(monkeypatch):
    """Non-200 (and non-429) → log warning, yield nothing."""
    sp = _make_sp([])
    from config import config
    monkeypatch.setattr(config.Running, "UseYFinance", True, raising=False)
    monkeypatch.setattr(config.Jupyter, "RapidYFinanaceKey", "k", raising=False)

    class _Resp:
        status = 500
        def read(self): return b'{"error": "internal"}'

    class _Conn:
        def __init__(self, *a, **kw): pass
        def request(self, *a, **kw): pass
        def getresponse(self): return _Resp()

    import http.client
    monkeypatch.setattr(http.client, "HTTPSConnection", _Conn)
    assert list(sp.get_hist_split("BAD")) == []


def test_get_hist_split_retries_on_429(monkeypatch):
    """429 on first attempt → sleep + retry → 200 yields parsed splits."""
    sp = _make_sp([])
    from config import config
    monkeypatch.setattr(config.Running, "UseYFinance", True, raising=False)
    monkeypatch.setattr(config.Jupyter, "RapidYFinanaceKey", "k", raising=False)

    calls = {"n": 0}

    class _Resp429:
        status = 429
        def read(self): return b''

    class _Resp200:
        status = 200
        def read(self):
            import json as _j
            return _j.dumps({"data": [{"date": 1598832000000, "stockSplits": 5}]}).encode()

    class _Conn:
        def __init__(self, *a, **kw): pass
        def request(self, *a, **kw): pass
        def getresponse(self):
            calls["n"] += 1
            return _Resp429() if calls["n"] == 1 else _Resp200()

    import http.client, time
    monkeypatch.setattr(http.client, "HTTPSConnection", _Conn)
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)
    out = list(sp.get_hist_split("TSLA"))
    assert calls["n"] == 2
    assert out and out[0][1] == 5.0


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_YF, reason="RapidYFinanaceKey not configured")
def test_get_hist_split_live_tsla(monkeypatch):
    """Live test: RapidAPI yfinance must return the two well-known TSLA splits:
    5-for-1 on 2020-08-31 and 3-for-1 on 2022-08-25."""
    from config import config
    monkeypatch.setattr(config.Running, 'UseYFinance', True, raising=False)
    sp = _make_sp([])
    splits = list(sp.get_hist_split("TSLA"))
    if not splits:
        pytest.skip("RapidAPI yfinance returned no data (likely HTTP 500 / 429)")
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
