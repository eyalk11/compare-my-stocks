"""Tests for currency-adjustment logic in InputProcessor + DataGenerator.

Covers:
- get_currency_on_certain_time: date lookup + ±N day fallback windows
- get_special_symbol_hist: the new #XYZ → real FX-rate series
- build_adjust_panel: rate-multiplication of TOADJUST columns, TOKEEP
  pass-through, TOADJUSTLONG sub-panel assembly.
- DataGenerator.readjust_for_currency: TOADJUST scalar 1/rate scaling and
  TOADJUSTLONG time-series scaling.
- Cached-data smoke test that loads ~/.compare_my_stocks/hist_file.cache
  and exercises get_currency_on_certain_time on real ILS history.
"""

import datetime
import os
import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from config import config
from engine.symbols import SpecialSymbol
from engine.symbolsinterface import SymbolsInterface
from input.inputprocessor import InputProcessor
from processing.datagenerator import DataGenerator


HIST_CACHE = os.path.expanduser('~/.compare_my_stocks/hist_file.cache')


@pytest.fixture
def proc():
    """An InputProcessor instance built via __new__ to avoid the Qt-heavy
    __init__ (QSemaphore / DoLongProcessSlots / etc. need a QApplication
    that isn't running in the test session). We only exercise pure-Python
    methods on it, so __init__ state isn't needed."""
    p = InputProcessor.__new__(InputProcessor)
    p.data = MagicMock()  # _data is a @property delegating to self.data
    return p


# ============================================================================
# get_currency_on_certain_time
# ============================================================================

class TestGetCurrencyOnCertainTime:
    """The method takes (currency, datetime) and returns (mid_price, queried).
    It walks ±1 day, ±2 days searching get_currency_hist for any data."""

    def _hist_df(self, dates, opens, closes):
        return pd.DataFrame(
            {'Open': opens, 'High': opens, 'Low': closes, 'Close': closes,
             'Volume': [1] * len(dates)},
            index=pd.to_datetime(dates),
        )

    def test_exact_date_returns_mid_of_open_close(self, proc):
        t = datetime.datetime(2024, 6, 3)
        df = self._hist_df(['2024-06-03'], [3.0], [3.4])
        with patch.object(proc, 'get_currency_hist', return_value=df) as mock:
            val, queried = proc.get_currency_on_certain_time('ILS', t)
        assert val == pytest.approx((3.0 + 3.4) / 2)
        # First call uses ±1-day window around t.
        args, kwargs = mock.call_args_list[0]
        assert args[0] == 'ILS'

    def test_falls_back_to_wider_window(self, proc):
        """When the ±1d window is empty, the loop tries ±2d."""
        t = datetime.datetime(2024, 6, 3)
        empty = pd.DataFrame()
        good = self._hist_df(['2024-06-01'], [4.0], [4.2])
        with patch.object(proc, 'get_currency_hist', side_effect=[empty, good]):
            val, queried = proc.get_currency_on_certain_time('ILS', t)
        assert val == pytest.approx(4.1)

    def test_no_data_returns_none(self, proc):
        t = datetime.datetime(2024, 6, 3)
        with patch.object(proc, 'get_currency_hist', return_value=pd.DataFrame()):
            val, queried = proc.get_currency_on_certain_time('ILS', t)
        assert val is None
        assert queried is False


# ============================================================================
# get_special_symbol_hist (the new #XYZ behavior)
# ============================================================================

class TestGetSpecialSymbolHist:
    """SpecialSymbol('#XYZ') should produce a daily OHLCV series whose
    Open/High/Low/Close all equal the XYZ→Basecur rate at that date,
    forward-filled across weekends and gaps. For XYZ == Basecur, flat 1.0."""

    def test_base_currency_is_flat_one(self, proc):
        sym = SpecialSymbol(config.Symbols.Basecur)
        start = datetime.datetime(2024, 6, 3)
        end = datetime.datetime(2024, 6, 5)
        _dic, df = proc.get_special_symbol_hist(sym, start, end)
        assert len(df) == 3
        assert (df['Close'] == 1.0).all()
        assert (df['Open'] == 1.0).all()

    def test_foreign_currency_uses_get_currency_on_certain_time(self, proc):
        sym = SpecialSymbol('EUR')
        start = datetime.datetime(2024, 6, 3)
        end = datetime.datetime(2024, 6, 5)
        rates = {
            datetime.datetime(2024, 6, 3): (1.10, True),
            datetime.datetime(2024, 6, 4): (1.11, True),
            datetime.datetime(2024, 6, 5): (1.12, True),
        }
        with patch.object(proc, 'get_currency_on_certain_time',
                          side_effect=lambda curr, t, cache_only=False: rates[t]):
            _dic, df = proc.get_special_symbol_hist(sym, start, end)
        assert list(df['Close']) == [1.10, 1.11, 1.12]

    def test_missing_dates_are_forward_filled(self, proc):
        """A None for a given date inherits the previous date's value."""
        sym = SpecialSymbol('EUR')
        start = datetime.datetime(2024, 6, 3)
        end = datetime.datetime(2024, 6, 5)
        # Day 2 has no data → should reuse day 1's 1.10
        seq = {
            datetime.datetime(2024, 6, 3): (1.10, True),
            datetime.datetime(2024, 6, 4): (None, False),
            datetime.datetime(2024, 6, 5): (1.12, True),
        }
        with patch.object(proc, 'get_currency_on_certain_time',
                          side_effect=lambda curr, t, cache_only=False: seq[t]):
            _dic, df = proc.get_special_symbol_hist(sym, start, end)
        assert list(df['Close']) == [1.10, 1.10, 1.12]

    def test_leading_none_is_skipped(self, proc):
        """If the first date has no rate, that row is dropped (no value to fill from)."""
        sym = SpecialSymbol('EUR')
        start = datetime.datetime(2024, 6, 3)
        end = datetime.datetime(2024, 6, 4)
        seq = {
            datetime.datetime(2024, 6, 3): (None, False),
            datetime.datetime(2024, 6, 4): (1.11, True),
        }
        with patch.object(proc, 'get_currency_on_certain_time',
                          side_effect=lambda curr, t, cache_only=False: seq[t]):
            _dic, df = proc.get_special_symbol_hist(sym, start, end)
        assert len(df) == 1
        assert df['Close'].iloc[0] == 1.11


# ============================================================================
# Real cached data: ~/.compare_my_stocks/hist_file.cache
# ============================================================================

@pytest.fixture(scope='module')
def cached_currency_hist():
    """Load the on-disk pickled hist cache and return the currency_hist
    DataFrame. Skips the test if the cache isn't present or unreadable."""
    if not os.path.exists(HIST_CACHE):
        pytest.skip(f"No hist cache at {HIST_CACHE}")
    try:
        with open(HIST_CACHE, 'rb') as f:
            _hist_by_date, _symbinfo, cache_date, currency_hist, _ = pickle.load(f)
    except Exception as e:
        pytest.skip(f"Could not load hist cache: {e}")
    if currency_hist is None or len(currency_hist) == 0:
        pytest.skip("currency_hist in cache is empty")
    if isinstance(currency_hist, dict):
        currency_hist = pd.DataFrame(currency_hist)
    return currency_hist, cache_date


class TestCachedCurrencyHist:
    """Sanity checks against the real cache the user has on disk."""

    def test_cache_has_known_currencies(self, cached_currency_hist):
        currency_hist, _ = cached_currency_hist
        # Top-level columns are currency codes.
        currencies = set(currency_hist.columns.get_level_values(0))
        # ILS is the most likely to be present given the user's portfolio
        # (Israeli account); EUR/GBP also commonly cached. We just assert
        # there is at least one non-base currency cached.
        assert len(currencies) >= 1, f"No currencies cached: {currencies}"

    def test_ils_rate_is_in_sane_range(self, cached_currency_hist):
        """USDILS has historically been in [2, 5] for the last 20 years."""
        currency_hist, _ = cached_currency_hist
        currencies = set(currency_hist.columns.get_level_values(0))
        if 'ILS' not in currencies:
            pytest.skip("ILS not in cached currency_hist")
        ils = currency_hist['ILS'].dropna(how='all')
        last_close = ils['Close'].dropna().iloc[-1]
        assert 2.0 < last_close < 5.0, f"USDILS last close out of range: {last_close}"

    def test_get_currency_on_certain_time_with_cache(self, proc, cached_currency_hist):
        """End-to-end: feed cached currency_hist into a bare InputProcessor
        and confirm get_currency_on_certain_time returns a sensible value."""
        currency_hist, cache_date = cached_currency_hist
        currencies = set(currency_hist.columns.get_level_values(0))
        if 'ILS' not in currencies:
            pytest.skip("ILS not in cached currency_hist")

        # Wire the loaded DataFrame into the bare proc.data mock.
        proc.data.currency_hist = currency_hist
        # Pick a date inside the cached range.
        ils_dates = currency_hist['ILS'].dropna(how='all').index
        if len(ils_dates) < 5:
            pytest.skip("Not enough ILS history in cache")
        target = ils_dates[len(ils_dates) // 2].to_pydatetime()

        val, queried = proc.get_currency_on_certain_time(
            'ILS', target, cache_only=True
        )
        assert val is not None, f"No rate for ILS at {target}"
        assert 2.0 < val < 5.0, f"USDILS at {target} out of range: {val}"


# ============================================================================
# build_adjust_panel
# ============================================================================

def _build_reg_panel(symbols, dates):
    """Construct a minimal MultiIndex _reg_panel with all the Name-levels
    that build_adjust_panel touches.

    rel_profit_by_stock and unrel_profit are populated with predictable
    values so we can verify the rate-multiplication and the
    tot_profit = rel + unrel recomputation. Other levels (holding, value,
    etc.) get distinguishable but inert values so we can detect copies."""
    names = ['holding_by_stock', 'rel_profit_by_stock', 'avg_cost_by_stock',
             'unrel_profit', 'value', 'alldates', 'tot_profit_by_stock']
    cols = pd.MultiIndex.from_product([names, symbols], names=['Name', 'Symbols'])
    df = pd.DataFrame(index=dates, columns=cols, dtype=float)
    for name in names:
        for i, sym in enumerate(symbols):
            base = {'rel_profit_by_stock': 100.0, 'unrel_profit': 50.0,
                    'holding_by_stock': 10.0, 'avg_cost_by_stock': 25.0,
                    'value': 200.0, 'alldates': 150.0,
                    'tot_profit_by_stock': 999.0}[name]
            df[(name, sym)] = base + i  # vary per-symbol so we can tell them apart
    return df


def _adjusted_dict(symbols, dates, base):
    """Build a dict-of-dicts {sym: {date: value}} as used for the
    *_adjusted attributes consumed by return_subpanel."""
    return {sym: {d: base + i for d in dates} for i, sym in enumerate(symbols)}


class TestBuildAdjustPanel:
    """build_adjust_panel multiplies TOADJUST columns by per-symbol rates,
    keeps TOKEEP columns as-is, and overlays the TOADJUSTLONG panels with
    the *_adjusted dicts on _data."""

    def _setup(self, proc, symbols=('AAPL', 'TSM'), rates=(0.5, 2.0)):
        dates = pd.date_range('2024-01-01', periods=3)
        proc.data = MagicMock()
        proc.data._reg_panel = _build_reg_panel(list(symbols), dates)
        proc.data._adjusted_value = _adjusted_dict(symbols, dates, base=300.0)
        proc.data._alldates_adjusted = _adjusted_dict(symbols, dates, base=400.0)
        proc.data._unrel_profit_adjusted = _adjusted_dict(symbols, dates, base=500.0)
        proc.data._avg_cost_by_stock_adjusted = _adjusted_dict(symbols, dates, base=600.0)
        currency_dict = dict(zip(symbols, rates))
        return currency_dict, dates

    def test_rel_profit_is_multiplied_by_rate(self, proc):
        currency_dict, dates = self._setup(proc, ('AAPL', 'TSM'), (0.5, 2.0))
        result = proc.build_adjust_panel(currency_dict)
        # rel_profit base values: AAPL=100, TSM=101. Rates: 0.5, 2.0.
        assert result[('rel_profit_by_stock', 'AAPL')].iloc[0] == pytest.approx(50.0)
        assert result[('rel_profit_by_stock', 'TSM')].iloc[0] == pytest.approx(202.0)

    def test_holding_passes_through_unchanged(self, proc):
        currency_dict, _ = self._setup(proc, ('AAPL',), (0.5,))
        result = proc.build_adjust_panel(currency_dict)
        # holding base = 10; rate must NOT be applied to holdings.
        assert result[('holding_by_stock', 'AAPL')].iloc[0] == pytest.approx(10.0)

    def test_value_panel_comes_from_adjusted_value_not_reg_panel(self, proc):
        currency_dict, _ = self._setup(proc, ('AAPL',), (0.5,))
        result = proc.build_adjust_panel(currency_dict)
        # _adjusted_value base = 300, _reg_panel value base = 200.
        # build_adjust_panel must use _adjusted_value (the pre-built FX
        # adjusted series), not the raw reg_panel.
        assert result[('value', 'AAPL')].iloc[0] == pytest.approx(300.0)

    def test_tot_profit_is_recomputed_from_rel_plus_unrel(self, proc):
        currency_dict, _ = self._setup(proc, ('AAPL',), (0.5,))
        result = proc.build_adjust_panel(currency_dict)
        # rel_profit AAPL after rate: 100*0.5 = 50.
        # unrel_profit AAPL from _unrel_profit_adjusted base = 500.
        # tot = 50 + 500 = 550. Note: original _reg_panel had tot=999, must
        # be discarded since build_adjust_panel recomputes it.
        assert result[('tot_profit_by_stock', 'AAPL')].iloc[0] == pytest.approx(550.0)

    def test_returns_false_when_no_relevant_symbols(self, proc):
        currency_dict, _ = self._setup(proc, ('AAPL',), (0.5,))
        # Use a currency_dict with symbols NOT in _reg_panel.
        result = proc.build_adjust_panel({'XYZ': 0.5, 'ABC': 0.3})
        assert result is False


# ============================================================================
# DataGenerator.readjust_for_currency
# ============================================================================

def _make_dg(adjusted_panel, reg_panel, currency_hist, rate, fromdate, todate):
    """Construct a DataGenerator-like object that reads from a mocked _inp.

    We don't go through DataGenerator.__init__ (which expects a
    full CompareEngine) — instead we instantiate via __new__ and set
    only the attributes readjust_for_currency uses."""
    dg = DataGenerator.__new__(DataGenerator)
    inp = MagicMock()
    inp.adjusted_panel = adjusted_panel
    inp.reg_panel = reg_panel
    inp.get_currency_hist = MagicMock(return_value=currency_hist)
    inp.get_relevant_currency = MagicMock(return_value=rate)
    # _data and symbol_info: fill_same_currency consults these; default to
    # an empty set so it does nothing (no symbols already match ncurrency).
    inp.symbol_info = {}
    inp._data = MagicMock()
    inp._data.get_currency_for_sym = MagicMock(return_value='USD')
    inp._reg_panel = reg_panel
    dg._inp = inp
    eng = MagicMock()
    eng.params.fromdate = fromdate
    eng.params.todate = todate
    eng.params.is_forced = False
    dg._eng = eng  # DataGenerator.params is a @property → self._eng.params
    return dg


class TestReadjustForCurrency:
    """readjust_for_currency rebases an already-base-currency adjusted_panel
    into a different home currency. TOADJUST cols get a scalar 1/rate; the
    TOADJUSTLONG cols (alldates, unrel_profit, value, ...) get multiplied
    by the historical FX series (Open+Close)/2 reindexed to panel dates."""

    def _panel(self, symbols, dates, base_per_name):
        names = ['holding_by_stock', 'rel_profit_by_stock', 'avg_cost_by_stock',
                 'unrel_profit', 'value', 'alldates', 'tot_profit_by_stock']
        cols = pd.MultiIndex.from_product([names, symbols], names=['Name', 'Symbols'])
        df = pd.DataFrame(index=dates, columns=cols, dtype=float)
        for name in names:
            for sym in symbols:
                df[(name, sym)] = float(base_per_name[name])
        return df

    def test_toadjust_is_scaled_by_inverse_rate(self):
        dates = [20100.0, 20101.0, 20102.0]   # matplotlib date numbers
        symbols = ['AAPL']
        base = {'holding_by_stock': 10, 'rel_profit_by_stock': 100,
                'avg_cost_by_stock': 25, 'unrel_profit': 50,
                'value': 200, 'alldates': 150, 'tot_profit_by_stock': 999}
        adjusted = self._panel(symbols, dates, base)
        reg = self._panel(symbols, dates, base)
        # Flat FX history: rate is 1.0 every day so TOADJUSTLONG mul is a no-op.
        ch_index = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        currency_hist = pd.DataFrame(
            {'Open': [1.0, 1.0, 1.0], 'Close': [1.0, 1.0, 1.0]},
            index=ch_index,
        )
        # ndays maps to the same dates as the panel after date2num conversion.
        import matplotlib.dates as mdates
        currency_hist.index = pd.Index(mdates.date2num(currency_hist.index.to_pydatetime()))
        # Use rate=2.0 → TOADJUST cols should be multiplied by 1/2 = 0.5.
        # Distinct currency per test — readjust_for_currency is @cached
        # by (ncurrency, fromdate, todate) with a 300s TTL, so reusing
        # 'EUR' across tests returns stale results.
        dg = _make_dg(adjusted, reg, currency_hist, rate=2.0,
                      fromdate=datetime.datetime(2024, 1, 1),
                      todate=datetime.datetime(2024, 1, 3))
        result = dg.readjust_for_currency('EUR_TOADJUST_TEST')
        # rel_profit_by_stock is in TOADJUST → must be base * 1/rate = 100 * 0.5 = 50
        assert result[('rel_profit_by_stock', 'AAPL')].iloc[0] == pytest.approx(50.0)

    def test_toadjustlong_is_scaled_by_fx_series(self):
        """alldates is in TOADJUSTLONG → multiplied by (Open+Close)/2 series."""
        symbols = ['AAPL']
        # Panel rows must be matplotlib date numbers — readjust_for_currency
        # converts the FX history's index via date2num and then reindexes.
        import matplotlib.dates as mdates
        dt_index = pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03'])
        date_nums = mdates.date2num(dt_index.to_pydatetime())
        base = {'holding_by_stock': 10, 'rel_profit_by_stock': 100,
                'avg_cost_by_stock': 25, 'unrel_profit': 50,
                'value': 200, 'alldates': 150, 'tot_profit_by_stock': 999}
        adjusted = self._panel(symbols, list(date_nums), base)
        reg = self._panel(symbols, list(date_nums), base)
        currency_hist = pd.DataFrame(
            {'Open': [2.0, 4.0, 6.0], 'Close': [2.0, 4.0, 6.0]},
            index=dt_index,
        )
        dg = _make_dg(adjusted, reg, currency_hist, rate=1.0,  # rate=1 so TOADJUST is no-op
                      fromdate=datetime.datetime(2024, 1, 1),
                      todate=datetime.datetime(2024, 1, 3))
        result = dg.readjust_for_currency('EUR_TOADJUSTLONG_TEST')
        # alldates base = 150, FX (Open+Close)/2 = [2, 4, 6]
        # → 150*2=300, 150*4=600, 150*6=900
        col = result[('alldates', 'AAPL')]
        assert col.iloc[0] == pytest.approx(300.0)
        assert col.iloc[1] == pytest.approx(600.0)
        assert col.iloc[2] == pytest.approx(900.0)

    def test_returns_none_when_no_rate(self):
        """No FX rate available → method bails out (returns None)."""
        dates = [20100.0]
        symbols = ['AAPL']
        adjusted = self._panel(symbols, dates,
                               {'holding_by_stock': 10, 'rel_profit_by_stock': 100,
                                'avg_cost_by_stock': 25, 'unrel_profit': 50,
                                'value': 200, 'alldates': 150,
                                'tot_profit_by_stock': 0})
        reg = adjusted.copy()
        currency_hist = pd.DataFrame(
            {'Open': [1.0], 'Close': [1.0]},
            index=pd.to_datetime(['2024-01-01']),
        )
        dg = _make_dg(adjusted, reg, currency_hist, rate=None,
                      fromdate=datetime.datetime(2024, 1, 1),
                      todate=datetime.datetime(2024, 1, 1))
        result = dg.readjust_for_currency('EUR_NORATE_TEST')
        assert result is None
