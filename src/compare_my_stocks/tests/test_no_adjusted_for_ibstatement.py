"""Reproduce the KeyError seen in datagenerator.readjust_for_currency:411

    KeyError: "[('avg_cost_by_stock', 'WIZZ'), ('avg_cost_by_stock', 'TSLA')] not in index"

The proximate cause is that adjusted_panel lacks ('avg_cost_by_stock', sym)
columns for some symbols. Those columns come from
inputprocessor.build_adjust_panel -> avg_cost_panel built from
self._data._avg_cost_by_stock_adjusted, which is only written inside the
per-symbol loop in process_buys (inputprocessor.py:725-732). A symbol that
never gets a yielded BuyOp (e.g. because its currency lookup raised inside
SimpleExceptionContext) never enters that loop and so never gets an entry.

The classifier that decides "needs currency adjustment vs not" is
get_buy_operations_with_adjusted (inputprocessor.py:327). This test loads
the real ibstatement.cache from the user's data dir and feeds those
synthetic BuyDictItems to that classifier, with currency lookups stubbed in
two flavors: (a) succeed for everything, (b) fail for the GBP rate. Then we
check _no_adjusted_for and which symbols actually got yielded.

Marked `liveuser` because it depends on the user's ibstatement.cache.
"""
from __future__ import annotations

import datetime
import os
import pickle
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from PySide6.QtCore import QSemaphore

from common.common import InputSourceType
from config import config as live_config
from input.inputdata import InputDataImpl
from input.inputprocessor import InputProcessor

# Use a non-listening port so any stray IB connect attempt fails fast and
# does not steal the live TWS session on 7596.
TEST_IB_PORT = 27597


CACHE = Path.home() / ".compare_my_stocks" / "ibstatement.cache"


def _load_ibstatement_cache():
    if not CACHE.exists():
        pytest.skip(f"{CACHE} missing; run the app once to populate it")
    with open(CACHE, "rb") as f:
        obj = pickle.load(f)
    # Tuple shape: (buydic, buysymbols, _)
    assert isinstance(obj, tuple) and len(obj) >= 1
    buydic = obj[0]
    assert isinstance(buydic, dict) and buydic, "ibstatement.cache buydic is empty"
    return buydic


def _build_processor(symbol_currency: dict[str, str]) -> InputProcessor:
    """Construct an InputProcessor wired up just enough to run
    get_buy_operations_with_adjusted. Uses a non-listening IB port and
    disables prompts so it is safe to run alongside a live session."""
    live_config.Sources.IBSource.PortIB = TEST_IB_PORT
    live_config.Sources.IBSource.PromptOnConnectionFail = False
    live_config.TransactionHandlers.IB.PromptOnQueryFail = False
    live_config.Input.InputSource = InputSourceType.Cache

    symb = MagicMock()
    txh = MagicMock()
    proc = InputProcessor(symb, txh, inputsource=None)
    proc.data = InputDataImpl(semaphore=QSemaphore(100))
    for sym, curr in symbol_currency.items():
        proc.data.symbol_info[sym] = {"currency": curr}
    proc.data._err_transactions = set()
    return proc


def _filter_items(buydic, symbols):
    """Yield (timestamp, BuyDictItem) tuples for the given symbols, in the
    order get_buy_operations_with_adjusted will iterate them."""
    for t, v in buydic.items():
        if v.Symbol in symbols:
            yield (t, v)


def test_wizz_not_in_no_adjusted_for_when_currency_known():
    """Sanity: if WIZZ.currency = 'GBP' (≠ Basecur USD) AND the currency
    lookup succeeds, WIZZ ends up *not* in _no_adjusted_for."""
    buydic = _load_ibstatement_cache()
    proc = _build_processor({"TSLA": "USD", "WIZZ": "GBP"})
    proc.get_currency_on_certain_time = MagicMock(return_value=(0.79, False))
    items = list(_filter_items(buydic, {"TSLA", "WIZZ"}))
    assert items, "ibstatement.cache has no TSLA/WIZZ entries — fixture broken"

    yielded = list(proc.get_buy_operations_with_adjusted(items))
    yielded_syms = {op.buydic.Symbol for op in yielded}

    # TSLA's currency == Basecur USD → classified as no-adjustment, but still
    # yielded with currency=None so the per-symbol loop runs for it.
    assert "TSLA" in yielded_syms
    assert "TSLA" in proc._data._no_adjusted_for

    # WIZZ in GBP, lookup ok → yielded with the rate, NOT in _no_adjusted_for.
    assert "WIZZ" in yielded_syms
    assert "WIZZ" not in proc._data._no_adjusted_for


def test_wizz_routed_to_no_adjusted_when_currency_lookup_fails():
    """Pin down the fix for the silent-drop bug: when the FX lookup raises,
    the BuyOp must still be yielded (with currency=None) and the symbol must
    land in _no_adjusted_for, so the per-symbol write loop in process_buys
    fires and _avg_cost_by_stock_adjusted[sym] gets populated via the
    trivial_currency / fallback branch. Otherwise build_adjust_panel's
    avg_cost_panel ends up missing the column and readjust_for_currency:411
    raises KeyError."""
    buydic = _load_ibstatement_cache()
    proc = _build_processor({"TSLA": "USD", "WIZZ": "GBP"})

    def _lookup(curr, t, cache_only=False):
        if curr == "GBP":
            raise KeyError(f"no GBP rate at {t}")
        return (1.0, False)

    proc.get_currency_on_certain_time = _lookup
    items = list(_filter_items(buydic, {"TSLA", "WIZZ"}))

    yielded = list(proc.get_buy_operations_with_adjusted(items))
    yielded_syms = {op.buydic.Symbol for op in yielded}
    yielded_currencies = {op.buydic.Symbol: op.currency for op in yielded}

    # TSLA still gets yielded (Basecur path, no lookup needed).
    assert "TSLA" in yielded_syms
    # WIZZ is yielded with currency=None — the fix.
    assert "WIZZ" in yielded_syms
    assert yielded_currencies["WIZZ"] is None
    # And it is in _no_adjusted_for, so the elif trivial_currency branch in
    # the per-symbol write loop populates _avg_cost_by_stock_adjusted.
    assert "WIZZ" in proc._data._no_adjusted_for


def test_tsla_when_currency_is_basecur():
    """TSLA in USD (==Basecur) lands in _no_adjusted_for; that is fine
    because the elif trivial_currency branch in the per-symbol write loop
    will populate _avg_cost_by_stock_adjusted from _cur_avg_cost_bystock.
    This test pins down the *classification*, not the loop downstream."""
    buydic = _load_ibstatement_cache()
    proc = _build_processor({"TSLA": "USD"})
    proc.get_currency_on_certain_time = MagicMock(return_value=(1.0, False))
    items = list(_filter_items(buydic, {"TSLA"}))

    list(proc.get_buy_operations_with_adjusted(items))

    assert "TSLA" in proc._data._no_adjusted_for
    assert proc.trivial_currency("TSLA") is True


# --------------------------------------------------------------------------
# Default config: GBp / ILA must be mapped so historical FX lookups don't
# get keyed on a non-ISO display currency.
# --------------------------------------------------------------------------

def test_default_translatecurrency_maps_pence_to_pound():
    """The shipped data/myconfig.yaml must translate 'GBp' to 'GBP' (and
    'ILA' to 'ILS') so callers of get_currency_for_sym() get a real FX
    pair. Without this, an LSE/TASE symbol crashes the panel build.
    Parsed by regex because the shipped YAML uses project-specific tags
    (`!FooConf`, `!!python/tuple`) that need the live config loader."""
    import re
    shipped = (
        Path(__file__).resolve().parents[1] / "data" / "myconfig.yaml"
    ).read_text()
    tc_match = re.search(r"TranslateCurrency:\s*(\{[^}]*\})", shipped)
    cf_match = re.search(r"CurrencyFactor:\s*(\{[^}]*\})", shipped)
    assert tc_match, "TranslateCurrency line not found in shipped config"
    assert cf_match, "CurrencyFactor line not found in shipped config"
    tc_text = tc_match.group(1)
    cf_text = cf_match.group(1)
    assert '"GBp":"GBP"' in tc_text.replace(" ", ""), (
        f"shipped TranslateCurrency missing GBp->GBP — LSE pence-quoted "
        f"symbols will hit the silent-FX-drop bug. Got: {tc_text}"
    )
    assert '"ILA":"ILS"' in tc_text.replace(" ", "")
    assert '"GBp":100' in cf_text.replace(" ", ""), (
        f"GBp must have a 100x divisor. Got: {cf_text}"
    )


def test_get_currency_for_sym_translates_gbp_when_default_loaded():
    """End-to-end: with the default mapping in place,
    InputProcessor.get_buy_operations_with_adjusted classifies a 'GBp'
    symbol as a regular non-base currency ('GBP'), not as a trip-the-bug
    raw 'GBp' string."""
    buydic = _load_ibstatement_cache()
    proc = _build_processor({"WIZZ": "GBp"})
    # Inject the default mapping explicitly so the test does not depend
    # on whichever myconfig.yaml the user happens to have on disk.
    live_config.Symbols.TranslateCurrency = {"ILA": "ILS", "GBp": "GBP"}

    queried_with = []

    def _lookup(curr, t, cache_only=False):
        queried_with.append(curr)
        return (1.30, False)  # GBP/USD-ish

    proc.get_currency_on_certain_time = _lookup
    items = list(_filter_items(buydic, {"WIZZ"}))

    yielded = list(proc.get_buy_operations_with_adjusted(items))
    yielded_syms = {op.buydic.Symbol for op in yielded}

    assert queried_with == ["GBP"], (
        f"FX lookup must be keyed on translated 'GBP', not raw "
        f"display currency. Got: {queried_with}"
    )
    assert "WIZZ" in yielded_syms
    assert "WIZZ" not in proc._data._no_adjusted_for


# --------------------------------------------------------------------------
# Sketch test for the proposed Currency value object. Marked xfail until
# the class lands; this test is the design contract committed to git.
# --------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="Currency value class not implemented yet")
def test_currency_value_object_translates_pence():
    """The proposed Currency class encapsulates raw tag + ISO pair +
    factor + rate fetching. The string 'GBp' must not leak past
    Currency.for_symbol — every consumer (FX lookup, price math) gets a
    consistent base-currency rate."""
    from common.currency import Currency  # type: ignore[import-not-found]

    # Fake symbol_info container shaped like InputDataImpl.
    data = MagicMock()
    data.symbol_info = {"WIZZ": {"currency": "GBp"}}

    live_config.Symbols.TranslateCurrency = {"GBp": "GBP", "ILA": "ILS"}
    live_config.Symbols.CurrencyFactor = {"GBp": 100.0, "ILA": 100.0}
    live_config.Symbols.Basecur = "USD"

    cur = Currency.for_symbol(data, "WIZZ")
    assert cur.raw == "GBp"
    assert cur.pair == "GBP"
    assert cur.factor == 100.0
    assert cur.is_base is False

    seen = []

    def _lookup(pair, base, t):
        seen.append((pair, base))
        # 1 GBP = 1.30 USD at time t
        return 1.30

    rate = cur.rate_at(datetime.datetime(2026, 4, 29), _lookup)

    assert seen == [("GBP", "USD")], (
        "Currency must query the ISO pair GBP/USD, never raw 'GBp'"
    )
    # 1 GBp = 1/100 GBP = 0.013 USD
    assert rate == pytest.approx(0.013, rel=1e-9)


@pytest.mark.xfail(strict=False, reason="Currency value class not implemented yet")
def test_currency_value_object_base_is_one():
    """A symbol already in the base currency reports rate=1/factor and
    needs no FX lookup."""
    from common.currency import Currency  # type: ignore[import-not-found]

    data = MagicMock()
    data.symbol_info = {"AAPL": {"currency": "USD"}}
    live_config.Symbols.TranslateCurrency = {}
    live_config.Symbols.CurrencyFactor = {}
    live_config.Symbols.Basecur = "USD"

    cur = Currency.for_symbol(data, "AAPL")
    assert cur.is_base is True

    def _lookup(*a, **kw):
        raise AssertionError("must not call FX lookup for base currency")

    assert cur.rate_at(datetime.datetime(2026, 4, 29), _lookup) == 1.0
