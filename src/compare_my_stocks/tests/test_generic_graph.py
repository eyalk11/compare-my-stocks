"""Generic graph-from-params test.

Drives the GraphGenerator end-to-end against a synthetic price panel so any
Parameters configuration can be exercised without a live data source.

Also supports running the same parameter grid against the *real* in-tree
cache at ``src/compare_my_stocks/data/HistFile.cache`` (the same files
``startvenv11_curdat.ps1`` copies to ``C:\\temp\\data``). Those tests
hash the cache file before and after to assert nothing on disk changed.
"""
import datetime as _dt
import hashlib
import os
import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock

import matplotlib
matplotlib.use("Agg")  # headless — no GUI windows during tests

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import Types, UniteType, UseCache
from engine.parameters import Parameters
from graph.graphgenerator import GraphGenerator


REAL_CACHE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "HistFile.cache"
)


# ---------------------------------------------------------------------------
# Synthetic data
# ---------------------------------------------------------------------------
def make_synthetic_prices(
    symbols=("AAPL", "MSFT", "GOOGL"),
    days=120,
    start=_dt.datetime(2026, 1, 2),
    seed=0,
    base_price=100.0,
    daily_vol=0.02,
):
    """Random-walk price panel: business-day index, one column per symbol."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=days)
    data = {}
    for i, sym in enumerate(symbols):
        steps = rng.normal(loc=0.0005, scale=daily_vol, size=days)
        prices = (base_price + i * 25) * np.exp(np.cumsum(steps))
        data[sym] = prices
    return pd.DataFrame(data, index=idx)


# ---------------------------------------------------------------------------
# Real-cache loader (uses the in-tree src/compare_my_stocks/data/HistFile.cache)
# ---------------------------------------------------------------------------
def load_real_prices_from_cache(cache_path: Path = REAL_CACHE_PATH,
                                max_symbols: int | None = 5,
                                max_days: int | None = 200) -> pd.DataFrame:
    """Load the in-tree HistFile.cache directly (no engine/config bootstrap)
    and return a price DataFrame: index=dates, columns=symbols, values=mid
    of (Close + Open) — same convention as InputProcessor.simplify_hist.

    Reads the file via pickle only; never writes back. Tests calling this
    should hash the file before/after to assert the cache is untouched
    (see ``test_real_cache_immutable_after_graph``)."""
    if not cache_path.exists():
        pytest.skip(f"Real cache not present at {cache_path}")
    with open(cache_path, "rb") as f:
        hist_by_date, _symbinfo, _cache_date, _currency, _ = pickle.load(f)

    # Same fixup as InputData._repair_timestamp_keys: pickled Timestamps
    # sometimes have .value in seconds rather than nanoseconds, which
    # otherwise produces a 1970-epoch DatetimeIndex full of NaN rows.
    _NS_PER_SEC = 1_000_000_000
    _NS_THRESHOLD = 10**17
    sample_key = next(iter(hist_by_date.keys()), None)
    if isinstance(sample_key, pd.Timestamp) and sample_key.value < _NS_THRESHOLD:
        hist_by_date = {
            (pd.Timestamp(int(k.value) * _NS_PER_SEC)
             if isinstance(k, pd.Timestamp) and k.value < _NS_THRESHOLD else k): v
            for k, v in hist_by_date.items()
        }

    rows: dict = {}
    for date, symdic in hist_by_date.items():
        row = {}
        for sym, val in symdic.items():
            try:
                dica, _dicb = val
                row[sym] = (dica["Close"] + dica["Open"]) / 2
            except Exception:
                continue
        if row:
            rows[date] = row

    df = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    if max_symbols is not None and df.shape[1] > max_symbols:
        # Densest columns first so the graph has real data to plot.
        nonnan = df.notna().sum().sort_values(ascending=False)
        df = df[list(nonnan.index[:max_symbols])]
    if max_days is not None and len(df) > max_days:
        df = df.iloc[-max_days:]
    df = df.dropna(how="all")
    return df


def _hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Graph driver
# ---------------------------------------------------------------------------
def gen_graph_from_params(params: Parameters, df: pd.DataFrame | None = None,
                          symbols=("AAPL", "MSFT", "GOOGL"), days=120):
    """Run GraphGenerator.gen_actual_graph against synthetic data driven by
    `params`. Returns (axes, generator) for assertion convenience."""
    if df is None:
        df = make_synthetic_prices(symbols=symbols, days=days)

    eng = MagicMock()
    eng.params = params

    fig, axes = plt.subplots(figsize=(8, 4))
    gg = GraphGenerator(eng, axes)
    gg.gen_actual_graph(
        cols=list(df.columns),
        dt=df,
        isline=params.isline,
        starthidden=params.starthidden,
        just_upd=False,
        type=params.type,
        unitetype=params.unite_by_group,
        orig_data=df,
        adjust_date=False,
        plot_data=None,
        additional_df=None,
    )
    return axes, gg, fig


# ---------------------------------------------------------------------------
# Possible parameter configurations to exercise
# ---------------------------------------------------------------------------
POSSIBLE_PARAMETERS = [
    pytest.param(
        Parameters(
            type=Types.PRICE,
            unite_by_group=UniteType.NONE,
            isline=True,
            use_groups=False,
            groups=["FANG"],
            use_cache=UseCache.DONT,
            show_graph=False,
        ),
        id="price-line",
    ),
    pytest.param(
        Parameters(
            type=Types.PRICE | Types.RELTOSTART | Types.PRECENTAGE,
            unite_by_group=UniteType.NONE,
            isline=True,
            use_groups=False,
            groups=["FANG"],
            use_cache=UseCache.DONT,
            show_graph=False,
        ),
        id="price-pct-rel-to-start",
    ),
    pytest.param(
        Parameters(
            type=Types.VALUE,
            unite_by_group=UniteType.NONE,
            isline=False,  # scatter-style render path
            use_groups=False,
            groups=["FANG"],
            use_cache=UseCache.DONT,
            show_graph=False,
        ),
        id="value-scatter",
    ),
    pytest.param(
        Parameters(
            type=Types.PROFIT | Types.RELTOMAX,
            unite_by_group=UniteType.NONE,
            isline=True,
            use_groups=False,
            groups=["FANG"],
            use_cache=UseCache.DONT,
            show_graph=False,
            starthidden=True,
        ),
        id="profit-rel-to-max-hidden",
    ),
]


@pytest.fixture(params=["synthetic", "real"])
def price_panel(request):
    """Drives every parametrized test against both the synthetic
    random-walk panel and the in-tree HistFile.cache. The 'real' branch
    is auto-skipped if the cache file is absent."""
    if request.param == "synthetic":
        return make_synthetic_prices()
    return load_real_prices_from_cache()


@pytest.mark.parametrize("params", POSSIBLE_PARAMETERS)
def test_graph_from_panel(params, price_panel, tmp_path):
    """For every Parameters config × every data source (synthetic + real
    in-tree cache): produce a graph and assert the plot survived."""
    df = price_panel
    expected_lines = df.shape[1]

    # Snapshot the real cache so we can prove the test didn't mutate it.
    pre_hash = _hash_file(REAL_CACHE_PATH) if REAL_CACHE_PATH.exists() else None

    axes, gg, fig = gen_graph_from_params(params, df=df)

    try:
        assert len(axes.lines) == expected_lines

        title = axes.get_title()
        assert title
        if params.type & Types.PROFIT:
            assert "profit" in title.lower()
        elif params.type & Types.PRICE:
            assert "price" in title.lower()
        elif params.type & Types.VALUE:
            assert "value" in title.lower()

        assert axes.legend_ is not None
        assert axes.xaxis.get_major_formatter().__class__.__name__ == "DateFormatter"

        out = tmp_path / "graph.png"
        fig.savefig(out)
        assert out.exists() and out.stat().st_size > 0
    finally:
        plt.close(fig)

    # Equivalent of the startvenv11_curdat invariant: nothing in
    # src/compare_my_stocks/data/ should be modified by tests.
    if pre_hash is not None:
        assert _hash_file(REAL_CACHE_PATH) == pre_hash, (
            f"In-tree cache {REAL_CACHE_PATH} was modified by the test"
        )


def test_real_cache_immutable_after_graph():
    """Standalone immutability check: load + render against the real
    in-tree cache and assert its on-disk bytes are unchanged. Mirrors
    the contract of startvenv11_curdat.ps1, which copies the same files
    to C:\\temp\\data so the live install never touches them."""
    if not REAL_CACHE_PATH.exists():
        pytest.skip(f"Real cache not present at {REAL_CACHE_PATH}")
    pre_hash = _hash_file(REAL_CACHE_PATH)
    df = load_real_prices_from_cache()
    assert df.shape[1] > 0 and len(df) > 0

    p = Parameters(
        type=Types.PRICE,
        unite_by_group=UniteType.NONE,
        isline=True,
        use_groups=False,
        groups=[],
        use_cache=UseCache.DONT,
        show_graph=False,
    )
    _, _, fig = gen_graph_from_params(p, df=df)
    plt.close(fig)
    assert _hash_file(REAL_CACHE_PATH) == pre_hash


def test_graph_from_custom_dataframe(tmp_path):
    """Caller can pass any DataFrame — useful when synthetic randomness
    isn't enough and a known panel is needed."""
    idx = pd.bdate_range("2026-01-02", periods=30)
    df = pd.DataFrame(
        {
            "AAA": np.linspace(100, 130, 30),
            "BBB": np.linspace(200, 180, 30),
        },
        index=idx,
    )
    p = Parameters(
        type=Types.PRICE,
        unite_by_group=UniteType.NONE,
        isline=True,
        use_groups=False,
        groups=[],
        use_cache=UseCache.DONT,
        show_graph=False,
    )
    axes, gg, fig = gen_graph_from_params(p, df=df)
    try:
        assert len(axes.lines) == 2
        # Monotonic ramps -> first/last value sanity.
        line_aaa = next(l for l in axes.lines if l.get_label() == "AAA")
        ydata = line_aaa.get_ydata()
        assert ydata[0] == pytest.approx(100.0)
        assert ydata[-1] == pytest.approx(130.0)
    finally:
        plt.close(fig)
