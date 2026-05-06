"""Generic graph-from-params test.

Drives the GraphGenerator end-to-end against a synthetic price panel so any
Parameters configuration can be exercised without a live data source.
"""
import datetime as _dt
import os
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


@pytest.mark.parametrize("params", POSSIBLE_PARAMETERS)
def test_graph_from_synthetic(params, tmp_path):
    """For every Parameters config: produce a graph from a synthetic price
    panel and assert the plotted lines + title made it through."""
    axes, gg, fig = gen_graph_from_params(params)

    try:
        # The DataFrame had 3 columns -> 3 plotted lines.
        assert len(axes.lines) == 3

        # Title comes from params.type via GraphGenerator.get_title().
        title = axes.get_title()
        assert title  # non-empty
        if params.type & Types.PROFIT:
            assert "profit" in title.lower()
        elif params.type & Types.PRICE:
            assert "price" in title.lower()
        elif params.type & Types.VALUE:
            assert "value" in title.lower()

        # Smoke-test: legend exists, x-axis is dates.
        assert axes.legend_ is not None
        assert axes.xaxis.get_major_formatter().__class__.__name__ == "DateFormatter"

        # Save the figure so a developer can eyeball it on demand
        # (only kept inside tmp_path; pytest cleans it up).
        out = tmp_path / "graph.png"
        fig.savefig(out)
        assert out.exists() and out.stat().st_size > 0
    finally:
        plt.close(fig)


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
