"""Engine-level tests: required_syms (the symbol-set assembler),
SymbolsHandler.get_options_from_groups (the group → symbols expander), and
end-to-end engine tests — test_realengine (live IB Gateway, integration)
and test_synthetic_engine (synthetic IB source, no live deps)."""

import datetime
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import Types, UniteType, UseCache, InputSourceType
from engine.compareengine import InternalCompareEngine
from engine.parameters import Parameters
from engine.symbolshandler import SymbolsHandler


# ============================================================================
# CompareEngine.required_syms
# ============================================================================

class _StubEngine(InternalCompareEngine):
    """Concrete subclass that overrides every abstract method with no-ops
    so we can instantiate without spinning up CompareEngine's full graph."""
    InputSource = property(lambda self: None)
    adjust_date = property(lambda self: 0)
    colswithoutext = property(lambda self: set())
    final_columns = property(lambda self: [])
    def get_portfolio_stocks(self): return []
    input_processor = property(lambda self: None)
    maxValue = property(lambda self: 0)
    maxdate = property(lambda self: None)
    minValue = property(lambda self: 0)
    mindate = property(lambda self: None)
    def process(self, *a, **k): pass
    def serialized_data(self): return {}
    def show_hide(self, *a, **k): pass
    to_use_ext = True
    transaction_handler = None
    usable_symbols = property(lambda self: set())
    used_unitetype = None


def _bare_engine(*, type_, unite_by_group, compare_with, use_groups,
                 ext, selected_stocks, group_members,
                 to_use_ext=True, portfolio=None):
    """Build a minimal engine via __new__ that exposes only what
    required_syms reads. Lets us drive the function without spinning up
    the full CompareEngine + InputProcessor + Qt machinery."""
    eng = _StubEngine.__new__(_StubEngine)
    eng.used_type = None  # so it falls back to params.type
    eng.used_unitetype = None  # so it falls back to params.unite_by_group
    eng.to_use_ext = to_use_ext

    params = MagicMock()
    params.type = type_
    params.unite_by_group = unite_by_group
    params.compare_with = compare_with
    params.use_groups = use_groups
    params.ext = ext
    params.selected_stocks = selected_stocks
    params.groups = list(group_members.keys())
    params.limit_to_portfolio = False
    params.cur_category = 'Test'
    eng._params = params

    # SymbolsHandler internals (Groups property reads _groups_by_cat[cur_category])
    eng._categories = ['Test']
    eng._groups_by_cat = {'Test': dict(group_members)}
    eng._cur_category = None  # let cur_category property fall back

    # Portfolio helper used when ADDPROT is set
    eng.transaction_handler = MagicMock()
    eng.transaction_handler.get_portfolio_stocks = MagicMock(
        return_value=list(portfolio or []))
    return eng


class TestRequiredSyms:
    """required_syms folds compare_with + ext + portfolio + (groups or
    selected_stocks) into a single set of tickers to fetch. The matrix
    of toggles is wide; these tests pin the obvious cases."""

    def test_use_groups_off_returns_selected_stocks(self):
        eng = _bare_engine(
            type_=Types.PRICE, unite_by_group=UniteType.NONE,
            compare_with=None, use_groups=False,
            ext=[], selected_stocks=['AAPL', 'MSFT'],
            group_members={'FANG': ['META', 'AAPL', 'GOOGL']},
        )
        result = eng.required_syms()
        assert result == {'AAPL', 'MSFT'}

    def test_use_groups_on_expands_groups(self):
        eng = _bare_engine(
            type_=Types.PRICE, unite_by_group=UniteType.NONE,
            compare_with=None, use_groups=True,
            ext=[], selected_stocks=[],
            group_members={'FANG': ['META', 'AAPL', 'GOOGL']},
        )
        result = eng.required_syms()
        assert result == {'META', 'AAPL', 'GOOGL'}

    def test_compare_with_only_added_when_unite_symbols_requested(self):
        """compare_with joins `selected` only when want_unite_symbols=True
        AND Types.COMPARE is set. Default call must not pull it in."""
        eng = _bare_engine(
            type_=Types.PRICE | Types.COMPARE, unite_by_group=UniteType.NONE,
            compare_with='QQQ', use_groups=False,
            ext=[], selected_stocks=['AAPL'],
            group_members={},
        )
        # Default: want_unite_symbols=False → QQQ not added.
        assert 'QQQ' not in eng.required_syms()
        # With the flag, QQQ is added.
        assert 'QQQ' in eng.required_syms(want_unite_symbols=True)

    def test_compare_with_skipped_when_compare_flag_off(self):
        eng = _bare_engine(
            type_=Types.PRICE, unite_by_group=UniteType.NONE,  # no COMPARE
            compare_with='QQQ', use_groups=False,
            ext=[], selected_stocks=['AAPL'],
            group_members={},
        )
        # Even with want_unite_symbols=True, no COMPARE → QQQ skipped.
        assert 'QQQ' not in eng.required_syms(want_unite_symbols=True)

    def test_ext_included_when_to_use_ext(self):
        eng = _bare_engine(
            type_=Types.PRICE, unite_by_group=UniteType.NONE,
            compare_with=None, use_groups=False,
            ext=['SPY', 'QQQ'], selected_stocks=['AAPL'],
            group_members={},
        )
        assert eng.required_syms() == {'AAPL', 'SPY', 'QQQ'}

    def test_ext_skipped_when_to_use_ext_off(self):
        eng = _bare_engine(
            type_=Types.PRICE, unite_by_group=UniteType.NONE,
            compare_with=None, use_groups=False,
            ext=['SPY', 'QQQ'], selected_stocks=['AAPL'],
            group_members={}, to_use_ext=False,
        )
        assert eng.required_syms() == {'AAPL'}

    def test_addprot_drops_compare_with(self):
        """When ADDPROT is set the line `selected = set(portfolio)` REPLACES
        whatever compare_with had added to `selected` a few lines above
        (line 83 vs. line 78). Subsequent ext/selected_stocks merges still
        run, but compare_with is gone."""
        eng = _bare_engine(
            type_=Types.PRICE | Types.COMPARE, unite_by_group=UniteType.ADDPROT,
            compare_with='QQQ', use_groups=False,
            ext=['SPY'], selected_stocks=['IGNORED'],
            group_members={}, portfolio=['AAPL', 'GOOGL'],
        )
        result = eng.required_syms(
            want_unite_symbols=True, want_portfolio_if_needed=True)
        # QQQ would have been added by the compare_with branch, but the
        # ADDPROT branch overwrites `selected` and QQQ is lost.
        assert 'QQQ' not in result
        assert {'AAPL', 'GOOGL', 'SPY', 'IGNORED'}.issubset(result)

    def test_only_unite_with_nontrivial_unite_returns_short_circuit(self):
        """When unite is non-trivial (SUM here, not just ADDTOTALS) AND
        only_unite=True AND want_unite_symbols=True, the function returns
        early without unioning groups/selected_stocks."""
        eng = _bare_engine(
            type_=Types.PRICE | Types.COMPARE, unite_by_group=UniteType.SUM,
            compare_with='QQQ', use_groups=True,
            ext=['SPY'], selected_stocks=['IGNORED'],
            group_members={'FANG': ['META', 'AAPL']},
        )
        result = eng.required_syms(want_unite_symbols=True, only_unite=True)
        # Should be just compare_with + ext, no group expansion.
        assert result == {'QQQ', 'SPY'}
        assert 'META' not in result
        assert 'AAPL' not in result

    def test_only_unite_preserves_selected_stocks_when_use_groups_off(self):
        """With use_groups=False the user is hand-picking stocks, so unite
        must NOT erase them — they should survive as individual columns
        alongside any group sums produced downstream."""
        eng = _bare_engine(
            type_=Types.PRICE | Types.COMPARE, unite_by_group=UniteType.SUM,
            compare_with='QQQ', use_groups=False,
            ext=['SPY'], selected_stocks=['TSLA', 'WIZZ'],
            group_members={'FANG': ['META', 'AAPL']},
        )
        result = eng.required_syms(want_unite_symbols=True, only_unite=True)
        # compare_with + ext + selected_stocks; group members still excluded.
        assert result == {'QQQ', 'SPY', 'TSLA', 'WIZZ'}
        assert 'META' not in result
        assert 'AAPL' not in result


# ============================================================================
# SymbolsHandler.get_options_from_groups
# ============================================================================

def _make_handler(groups, *, limit_to_portfolio=False, portfolio=None):
    """Bare SymbolsHandler instance. We inject Groups via _groups_by_cat,
    since that's what the Groups @property reads."""
    h = SymbolsHandler()
    h._categories = ['Test']
    h._groups_by_cat = {'Test': groups}
    params = MagicMock()
    params.cur_category = 'Test'
    params.limit_to_portfolio = limit_to_portfolio
    h._params = params
    h.get_portfolio_stocks = MagicMock(return_value=list(portfolio or []))
    return h


class TestGetOptionsFromGroups:
    """Expanding a list of group names into the union of their symbols.
    Special cases: 'Portfolio' pseudo-group, limit_to_portfolio
    intersection, missing group raises (and the wrapper logs)."""

    def test_returns_empty_for_empty_list(self):
        h = _make_handler({'FANG': ['META', 'AAPL']})
        assert h.get_options_from_groups([]) == []

    def test_expands_single_group(self):
        h = _make_handler({'FANG': ['META', 'AAPL', 'GOOGL']})
        result = set(h.get_options_from_groups(['FANG']))
        assert result == {'META', 'AAPL', 'GOOGL'}

    def test_expands_multiple_groups_and_dedupes(self):
        h = _make_handler({
            'FANG': ['META', 'AAPL', 'GOOGL'],
            'Tech': ['AAPL', 'MSFT', 'NVDA'],   # AAPL overlaps
        })
        result = set(h.get_options_from_groups(['FANG', 'Tech']))
        assert result == {'META', 'AAPL', 'GOOGL', 'MSFT', 'NVDA'}

    def test_portfolio_pseudo_group_uses_portfolio_helper(self):
        """The literal name 'Portfolio' substitutes the portfolio holdings."""
        h = _make_handler({'FANG': ['META']}, portfolio=['SPY', 'QQQ'])
        result = set(h.get_options_from_groups(['Portfolio']))
        assert result == {'SPY', 'QQQ'}

    def test_limit_to_portfolio_intersects(self):
        """When limit_to_portfolio is on, the result is intersected with
        the portfolio set — so 'Tech' filtered against a portfolio of just
        AAPL only yields AAPL."""
        h = _make_handler(
            {'Tech': ['AAPL', 'MSFT', 'NVDA']},
            limit_to_portfolio=True, portfolio=['AAPL', 'AMZN'],
        )
        result = set(h.get_options_from_groups(['Tech']))
        assert result == {'AAPL'}

    def test_unknown_group_swallowed_returns_none(self):
        """get_options_from_groups raises on unknown name, but the
        @simple_exception_handling decorator catches it (on_exception
        returns True → swallow) and the function returns None.
        Callers that .union(None) will then crash — caveat lector."""
        h = _make_handler({'FANG': ['META']})
        # Should NOT raise; result is None (the pre-exception ret value).
        result = h.get_options_from_groups(['NotARealGroup'])
        assert result is None


# ============================================================================
# CompareEngine end-to-end (real IB Gateway, integration; and synthetic IB)
# ============================================================================

# Imported lazily here so test_engine.py can still be imported when the
# integration test fixtures (additional_process etc.) aren't relevant.
from tests.testtools import (
    UseInput,
    DATADIR,
    assert_datadir_unchanged,
    additional_process,
    realeng,
    mock_config_to_default,
    generate_config,
    get_eng,
    make_synthetic_ibsource,
)
from config import config as _cfg, ConfigLoader as _ConfigLoader


# Shared parameter grid — same shape as test_generic_graph.POSSIBLE_PARAMETERS
# so synthetic-engine and graph-only tests cover the same Parameters surface.
POSSIBLE_PARAMETERS = [
    pytest.param(
        Parameters(
            type=Types.PRICE, unite_by_group=UniteType.NONE,
            isline=True, use_groups=True, groups=['FANG'],
            use_cache=UseCache.FORCEUSE, show_graph=False,
        ),
        id="price-line",
    ),
    pytest.param(
        Parameters(
            type=Types.PRICE | Types.RELTOSTART | Types.PRECENTAGE,
            unite_by_group=UniteType.NONE,
            isline=True, use_groups=True, groups=['FANG'],
            use_cache=UseCache.FORCEUSE, show_graph=False,
        ),
        id="price-pct-rel-to-start",
    ),
    pytest.param(
        Parameters(
            type=Types.VALUE, unite_by_group=UniteType.NONE,
            isline=False, use_groups=True, groups=['FANG'],
            use_cache=UseCache.FORCEUSE, show_graph=False,
        ),
        id="value-scatter",
    ),
    pytest.param(
        Parameters(
            type=Types.PROFIT | Types.RELTOMAX,
            unite_by_group=UniteType.NONE,
            isline=True, use_groups=True, groups=['FANG'],
            use_cache=UseCache.FORCEUSE, show_graph=False,
            starthidden=True,
        ),
        id="profit-rel-to-max-hidden",
    ),
]


def _maybe_guard_datadir(useinp, request):
    """If USEDATADIR is set: pre-flight that the in-tree cache is loadable
    in this env (skips with a clear reason otherwise), then activate the
    assert_datadir_unchanged guard so the test fails on any data-dir mutation."""
    if not (useinp & UseInput.USEDATADIR):
        return
    import pickle as _pkl
    _hf = os.path.join(DATADIR, "HistFile.cache")
    try:
        with open(_hf, "rb") as _f:
            _pkl.load(_f)
    except Exception as _e:
        pytest.skip(f"In-tree cache {_hf} cannot be loaded in this env: {_e!r}")
    request.getfixturevalue("assert_datadir_unchanged")


# ---------------------------------------------------------------------------
# test_realengine — two variants share the same body via _realengine_body:
#   * test_realengine (cache-only): pins to in-tree HistFile.cache via the
#     USEDATADIR-style config; deterministic, no IB Gateway required. Not
#     marked integration.
#   * test_realengine_live: hits a live IB Gateway / sidecar to fetch a
#     now-10d → now window; integration-marked.
# ---------------------------------------------------------------------------
def _realengine_body(eng, fromdate, todate, expect_live, disconnect_after):
    p = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE,
        isline=True, use_groups=True, groups=['FANG'],
        use_cache=UseCache.FORCEUSE, show_graph=False,
    )
    p.fromdate = fromdate
    p.todate = todate
    try:
        eng.gen_graph(p)
        assert eng.call_graph_generator.call_args is not None
        df = eng.call_graph_generator.call_args.args[0]
        if expect_live:
            assert df.shape[0] >= 1
            assert df.shape[1] >= 2
        else:
            assert df.shape[0] >= 22
    finally:
        if disconnect_after:
            eng.input_processor.InputSource.disconnect()


@pytest.mark.parametrize("useinp", [
    UseInput.LOADDEFAULTCONFIG,
    UseInput.LOADDEFAULTCONFIG | UseInput.USEDATADIR,
])
def test_realengine(mock_config_to_default, realeng, useinp, request):
    logging.info("Starting test_realengine, useinp=%s", useinp)
    _maybe_guard_datadir(useinp, request)
    _realengine_body(
        realeng,
        # Window inside the in-tree HistFile.cache (Apr 2025 → Apr 2026).
        # ~25 trading days to comfortably clear the `df.shape[0] >= 22` floor.
        fromdate=datetime.datetime(2025, 12, 15),
        todate=datetime.datetime(2026, 2, 1),
        expect_live=False,
        disconnect_after=False,
    )


@pytest.mark.integration
@pytest.mark.parametrize("useinp", [
    UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT,
    UseInput.WITHINPUT,
    UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT | UseInput.USEDATADIR,
])
def test_realengine_live(mock_config_to_default, realeng, useinp, request):
    logging.info("Starting test_realengine_live, useinp=%s", useinp)
    _maybe_guard_datadir(useinp, request)
    _realengine_body(
        realeng,
        fromdate=datetime.datetime.now() - datetime.timedelta(days=10),
        todate=datetime.datetime.now(),
        expect_live=True,
        disconnect_after=True,
    )


# ---------------------------------------------------------------------------
# test_adjust_currency — cache-only sibling here; the live (now-10d → now)
# variant lives in test_it.py and reuses _adjust_currency_body. The in-tree
# HistFile.cache is regenerated via scripts/fetch_polygon_cache.py and now
# includes ILS FX rows so adjustment can resolve from cache alone.
# ---------------------------------------------------------------------------
def _adjust_currency_body(eng, fromdate, todate, stub_fx_source=False,
                          use_cache=UseCache.FORCEUSE):
    import numpy
    p = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE,
        isline=True, use_groups=False, groups=['FANG'],
        use_cache=use_cache, show_graph=False,
        adjust_to_currency=True, currency_to_adjust='ILS',
    )
    p.fromdate = fromdate
    p.todate = todate
    eng.params = p
    eng.to_use_ext = eng.params.use_ext
    eng.used_unitetype = eng.params.unite_by_group
    eng.process()
    if stub_fx_source:
        # After cache load but before currency adjustment: stub the source so
        # get_currency_hist's "re-query" path returns None (cached FX used as
        # is) AND get_current_currency returns a real numeric rate (needed
        # by readjust_for_currency's `newdf[x].mul(1 / rate)`). Done here,
        # not earlier, because process() still expects a real source for
        # symbol-history unpacking.
        from unittest.mock import MagicMock
        src = MagicMock()
        src.get_currency_history = MagicMock(return_value=None)
        # USD→ILS spot rate ~3.7 — only matters that it's a finite float.
        src.get_current_currency = MagicMock(return_value=3.7)
        eng.input_processor._inputsource = src
    eng.call_data_generator()
    arr = numpy.isnan(eng._datagen.orig_df).all(axis=1)
    assert arr.loc[arr == False].size >= 2


@pytest.fixture
def cacheonly_eng(mock_config_to_default, useinp):
    """CompareEngine pinned to the bundled HistFile.cache, with NO live IB
    sidecar (AddProcess=None, InputSource=Cache). Mirrors get_eng() in
    testtools but skips additional_process — currency adjustment uses cached
    FX so a live sidecar is unnecessary.

    Order matters: ConfigLoader.config is shared across tests, so resetting
    these fields here (after mock_config_to_default may have set them via
    update_from) protects against earlier-test pollution.
    """
    from config import config as _cfg
    _cfg.Sources.IBSource.AddProcess = None
    _cfg.Input.InputSource = InputSourceType.Cache
    # Belt-and-suspenders: directly pin the bundled-cache paths here. update_
    # _from() in generate_config has subtle field-tracking behavior that
    # sometimes leaves File.FullData pointing at a stale per-user copy when
    # tests run in suite order.
    from tests.testtools import DATADIR, get_eng
    _cfg.File.HistF = os.path.join(DATADIR, "HistFile.cache")
    _cfg.File.FullData = os.path.join(DATADIR, "__nonexistent_fulldata__.bin")
    eng = get_eng()
    # Reset per-test FX state so cached relevant_currencies_rates from an
    # earlier test (test_realengine_live) don't shadow our stub.
    eng.input_processor._relevant_currencies_rates = {}
    return eng


@pytest.mark.parametrize("useinp", [
    UseInput.LOADDEFAULTCONFIG | UseInput.USEDATADIR,
])
def test_adjust_currency(cacheonly_eng, useinp, request):
    """Cache-only currency adjustment. Pinned to USEDATADIR so HistF points
    at the bundled HistFile.cache (regenerated with ILS FX rows by
    scripts/fetch_polygon_cache.py). No live IB sidecar — see cacheonly_eng."""
    _maybe_guard_datadir(useinp, request)
    _adjust_currency_body(
        cacheonly_eng,
        fromdate=datetime.datetime(2026, 1, 1),
        todate=datetime.datetime(2026, 2, 1),
        stub_fx_source=True,
    )


@pytest.mark.integration
def test_adjust_currency_live(realeng):
    """Live IB Gateway variant: fetches FX for the last 10d via the real
    IB sidecar. Shares the body with the cache-only sibling above.
    UseCache.DONT forces a live fetch for both price and FX history; the
    cache-only path is exercised by test_adjust_currency."""
    _adjust_currency_body(
        realeng,
        fromdate=datetime.datetime.now() - datetime.timedelta(days=10),
        todate=datetime.datetime.now(),
        use_cache=UseCache.DONT,
    )


# ---------------------------------------------------------------------------
# Live earnings fetch — backs the PERATIO (P/E) and PRICESELLS (price-to-
# sales) panels in DataGenerator (processing/datagenerator.py:183-190).
# Hits the SeekingAlpha RapidAPI directly; needs the API key in config.
# ---------------------------------------------------------------------------
@pytest.mark.integration
def test_live_earnings_fetch_for_peratio_pricesells():
    from transactions.earningsproc import EarningProcessor
    ep = EarningProcessor.__new__(EarningProcessor)
    from transactions.earningscommon import RapidApi
    RapidApi.__init__(ep, 'SeekingAlpha')
    if not ep.is_initialized():
        pytest.skip("SeekingAlpha RapidAPI key not configured")
    rev, inc = ep.get_dfs('AAPL')
    assert not rev.empty and not inc.empty, f"empty rev={rev.shape} inc={inc.shape}"


# ---------------------------------------------------------------------------
# test_synthetic_engine — same engine path, but the IBSource is a
# deterministic in-process mock (make_synthetic_ibsource). No IB Gateway,
# no integration mark. Covers the full Parameters grid × flag combos.
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_eng(useinp, monkeypatch):
    """Build a CompareEngine whose IB source is the deterministic synthetic
    mock. Honors UseInput flags via generate_config (LOADDEFAULTCONFIG /
    WITHINPUT / USEDATADIR). Caches (transactions, hist) are mocked to no-op
    so no on-disk file is mutated."""
    cfg = generate_config(useinp)
    cfg.Input.InputSource = InputSourceType.IB  # engine asks for an IBSource
    _ConfigLoader.config.update_from(cfg, all=True)

    synthetic = make_synthetic_ibsource()
    # Patch the import site that CompareEngine.__init__ calls — this avoids
    # spawning the real ibsrv subprocess.
    monkeypatch.setattr(
        "engine.compareengine.get_ibsource", lambda: synthetic, raising=True
    )

    eng = get_eng()
    # get_eng() instantiated CompareEngine before our patch took effect for
    # __init__ — but because monkeypatch is set first via fixture ordering,
    # the engine's _inp._inputsource IS the synthetic. Belt-and-suspenders:
    eng._inp._inputsource = synthetic
    return eng


@pytest.mark.parametrize("useinp", [
    UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT,
    UseInput.LOADDEFAULTCONFIG | UseInput.WITHINPUT | UseInput.USEDATADIR,
    UseInput.LOADDEFAULTCONFIG | UseInput.USEDATADIR,
])
@pytest.mark.parametrize("params", POSSIBLE_PARAMETERS)
def test_synthetic_engine(params, useinp, synthetic_eng, request):
    """Full engine path — config → InputProcessor → DataGenerator →
    GraphGenerator — driven by the synthetic IBSource. Same parameter grid
    as test_generic_graph.POSSIBLE_PARAMETERS so coverage matches."""
    logging.info("test_synthetic_engine useinp=%s params=%s", useinp, params)
    _maybe_guard_datadir(useinp, request)

    from copy import copy as _copy
    eng = synthetic_eng
    p = _copy(params)
    p.fromdate = datetime.datetime.now() - datetime.timedelta(days=120)
    p.todate = datetime.datetime.now()

    eng.gen_graph(p)
    assert eng.call_graph_generator.call_args is not None, \
        "graph generator was never called — engine path failed silently"
    df = eng.call_graph_generator.call_args.args[0]
    assert df.shape[0] >= 1, f"empty dataframe for {params.id if hasattr(params,'id') else params}"
    assert df.shape[1] >= 1
