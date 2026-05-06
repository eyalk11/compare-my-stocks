"""Engine-level tests: required_syms (the symbol-set assembler) and
SymbolsHandler.get_options_from_groups (the group → symbols expander)."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import Types, UniteType
from engine.compareengine import InternalCompareEngine
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
