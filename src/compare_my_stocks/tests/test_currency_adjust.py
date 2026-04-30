"""Tests for currency-adjustment logic in InputProcessor.

Covers:
- get_currency_on_certain_time: date lookup + ±N day fallback windows
- get_special_symbol_hist: the new #XYZ → real FX-rate series
- Cached-data smoke test that loads ~/.compare_my_stocks/hist_file.cache
  and exercises get_currency_on_certain_time on real ILS history.
"""

import datetime
import os
import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from config import config
from engine.symbols import SpecialSymbol
from input.inputprocessor import InputProcessor


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
