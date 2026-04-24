"""Focused unit tests for StockPrices.populate_buydic / get_hist_split."""
from collections import OrderedDict
from unittest.mock import patch

import pytest

from transactions.stockprices import StockPrices

# Importing config wires up StockPricesHeaders (RapidAPI key) from the user's
# myconfig.yaml. Required only for the live-API test below.
try:
    from config import config as _config
    from transactions.earningscommon import RapidApi as _RapidApi
    _HAS_KEY = bool(_config.StockPricesHeaders.X_RapidAPI_Key)
except Exception:
    _HAS_KEY = False


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


def test_get_hist_split_raises_on_api_message():
    sp = _make_sp([])
    with patch.object(StockPrices, "is_initialized", return_value=True), \
         patch.object(StockPrices, "get_json", return_value={"message": "rate limit"}), \
         patch("transactions.stockprices.time.sleep" if False else "time.sleep", return_value=None):
        with pytest.raises(Exception, match="rate limit"):
            list(sp.get_hist_split("AAPL"))


def test_get_hist_split_on_string_404_body_raises_attribute_error():
    """Document current behavior: get_json returning a non-dict (404 body)
    blows up with AttributeError. populate_buydic catches it."""
    sp = _make_sp(["FOO"])
    with patch.object(StockPrices, "is_initialized", return_value=True), \
         patch.object(StockPrices, "get_json", return_value="Not Found"), \
         patch("time.sleep", return_value=None):
        with pytest.raises(AttributeError, match="items"):
            list(sp.get_hist_split("FOO"))

    # And populate_buydic swallows that same error gracefully:
    with patch.object(StockPrices, "is_initialized", return_value=True), \
         patch.object(StockPrices, "get_json", return_value="Not Found"), \
         patch("time.sleep", return_value=None):
        sp.populate_buydic()
    assert "FOO" not in sp._buydic


@pytest.mark.skipif(not _HAS_KEY, reason="StockPrices RapidAPI key not configured")
def test_stockprices_api_live_tsla():
    """Live integration test: hit the real stock-prices2 RapidAPI with TSLA.
    Verifies auth, endpoint reachability, and JSON shape. get_hist_split
    itself returns nothing because the quarterly-sampled endpoint never
    lands on an actual split day (known limitation of the production code)."""
    sp = object.__new__(StockPrices)
    _RapidApi.__init__(sp, "StockPrices")
    assert sp.headers.get("X-RapidAPI-Key"), "RapidAPI key not loaded"

    with patch("time.sleep", return_value=None):
        js = sp.get_json(
            {"ticker": "TSLA"},
            "https://stock-prices2.p.rapidapi.com/api/v1/resources/stock-prices/10y-3mo-interval",
        )

    assert isinstance(js, dict) and js, "expected a non-empty dict response"
    assert "message" not in js, f"API error: {js.get('message')}"
    sample_key = next(iter(js))
    row = js[sample_key]
    for field in ("Close", "Open", "High", "Low", "Volume", "Stock Splits"):
        assert field in row, f"missing field {field} in response row"

    # get_hist_split should also complete without error (yields nothing
    # for TSLA given the quarterly sampling).
    with patch("time.sleep", return_value=None):
        splits = list(sp.get_hist_split("TSLA"))
    assert isinstance(splits, list)


def test_get_hist_split_uninitialized_yields_nothing():
    """get_hist_split is a generator; when not initialized it returns early
    and therefore yields nothing (no API call)."""
    sp = _make_sp([])
    with patch.object(StockPrices, "is_initialized", return_value=False), \
         patch.object(StockPrices, "get_json") as gj:
        assert list(sp.get_hist_split("AAPL")) == []
    gj.assert_not_called()
