"""Unit tests for compare_my_stocks/jupyter/jupytertools.py.

Most functions are pure DataFrame/scalar utilities — exercised here without
any notebook / config / file-system setup.
"""
import math
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from compare_my_stocks.jupyter import jupytertools as jt


# -------------------------- text_to_num / human_to_int --------------------------

@pytest.mark.parametrize("text,expected", [
    ("1K", Decimal("1000")),
    ("2.5M", Decimal("2.5") * 10 ** 6),
    ("3B", Decimal("3") * 10 ** 9),
    ("1T", Decimal("1") * 10 ** 12),
    ("42", Decimal("42")),
    ("3.14", Decimal("3.14")),
])
def test_text_to_num(text, expected):
    assert jt.text_to_num(text) == expected


def test_human_to_int_returns_nan_on_garbage():
    v = jt.human_to_int("not-a-number", "not-a-number")
    assert isinstance(v, float) and math.isnan(v)


def test_human_to_int_passes_through_numeric_text():
    assert jt.human_to_int("1.5K", "1.5K") == Decimal("1.5") * 10 ** 3


# ----------------------------- convert_to_dec -----------------------------

def test_convert_to_dec_handles_percent_and_magnitude():
    df = pd.DataFrame({"x": ["1K", "2%", "3.5"]})
    out = jt.convert_to_dec(df)
    assert out["x"].tolist() == [1000.0, 2.0, 3.5]


def test_convert_to_dec_nan_for_garbage():
    df = pd.DataFrame({"x": ["abc", "5"]})
    out = jt.convert_to_dec(df)
    assert math.isnan(out["x"].iloc[0])
    assert out["x"].iloc[1] == 5.0


# ----------------------------- add_change_from -----------------------------

def test_add_change_from_max():
    before = pd.DataFrame({"AAA": [100.0, 110.0, 90.0],
                           "BBB": [50.0, 40.0, 60.0]})
    df = pd.DataFrame({"AAA": [90.0], "BBB": [60.0]})
    data = SimpleNamespace(beforedata=before)
    out = jt.add_change_from(df, data, max=True)
    # Last row added named "Change from max"
    assert "Change from max" in out.index
    row = out.loc["Change from max"]
    # AAA: 90/110 - 1 = -18.18%, BBB: 60/60 - 1 = 0%
    assert row["AAA"].endswith("%") and row["AAA"].startswith("-18")
    assert row["BBB"] == "0.00%"


def test_add_change_from_min():
    before = pd.DataFrame({"AAA": [100.0, 110.0, 90.0]})
    df = pd.DataFrame({"AAA": [90.0]})
    data = SimpleNamespace(beforedata=before)
    out = jt.add_change_from(df, data, max=False)
    assert "Change from min" in out.index
    # 90/90 - 1 == 0%
    assert out.loc["Change from min", "AAA"] == "0.00%"


# --------------------------- add_target_price_change ---------------------------

def test_add_target_price_change_appends_row():
    df = pd.DataFrame({"AAA": ["120", "100"]}, index=["Target Price", "Price"])
    out = jt.add_target_price_change(df)
    assert "Target Price Change" in out.index
    # 120 / 100 * 100 - 100 == 20.0
    assert float(out.loc["Target Price Change", "AAA"]) == 20.0


# ----------------------------- highlight_it -----------------------------

def test_highlight_it_returns_styler():
    df = pd.DataFrame({"A": ["10", "20"], "B": ["30", "5"]}, index=["r1", "r2"])
    styler = jt.highlight_it(df)
    # pandas Styler has a `to_html` method
    assert hasattr(styler, "to_html")
    html = styler.to_html()
    assert "color:" in html


# ----------------------------- calc_closeness -----------------------------

def test_calc_closeness_zero_diagonal():
    rng = np.random.default_rng(0)
    n = 60  # > 2 * interval(=30)
    arr = rng.uniform(100, 200, size=(n, 3))
    df = pd.DataFrame(arr, columns=pd.Index(["A", "B", "C"], name="Symbols"))
    out = jt.calc_closeness(df, interval=30)
    assert out.shape == (3, 3)
    # symmetric
    assert np.allclose(out.values, out.values.T)
    # zero diagonal (norm of zero vector)
    assert all(out.values[i, i] == 0 for i in range(3))


# --------------------------- date conversion roundtrip ---------------------------

def test_convert_dates_df_roundtrip():
    import datetime as _dt
    dates = [_dt.date(2024, 1, 1), _dt.date(2024, 6, 15)]
    df = pd.DataFrame({"v": [1, 2]}, index=dates)
    fwd = jt.convert_dates_df(df.copy())
    # Now numeric matplotlib dates
    assert all(isinstance(x, float) for x in fwd.index)
    back = jt.convert_df_dates(fwd)
    assert list(back.index) == dates


# ----------------------------- unite_if_needed -----------------------------

def test_unite_if_needed_non_group_passthrough():
    data = SimpleNamespace(Groups={})
    out = jt.unite_if_needed("AAA", data, query_func=lambda s: {"k": s})
    assert out == {"k": "AAA"}


def test_unite_if_needed_aggregates_group():
    data = SimpleNamespace(Groups={"FANG": ["AAA", "BBB"]})

    # query_func returns a dict mapping a date-like key -> string number
    def qf(sym):
        return {"d1": "100", "d2": "200"} if sym == "AAA" else {"d1": "200", "d2": "400"}

    out = jt.unite_if_needed("FANG", data, query_func=qf)
    assert isinstance(out, dict)
    # Mean of AAA/BBB at d1 = 150 → numerized; at d2 = 300
    assert set(out.keys()) == {"d1", "d2"}
    assert isinstance(out["d1"], str)


def test_query_symbol_raises():
    # NotImplemented is a falsy *constant* (not the exception); the function
    # uses `raise NotImplemented()` which raises TypeError because
    # NotImplemented isn't callable.
    with pytest.raises((TypeError, NotImplementedError)):
        jt.query_symbol("AAA")


# ----------------------------- display_graph -----------------------------

def test_display_graph_is_noop():
    assert jt.display_graph() is None


# ----------------------------- load_data -----------------------------

def test_load_data_logs_when_missing(monkeypatch, caplog):
    from config import config as _cfg
    monkeypatch.setattr(_cfg.File, "DataFilePtr", "/nonexistent/path/__nope__", raising=False)
    with caplog.at_level("ERROR"):
        result = jt.load_data()
    assert result is None
    assert any("data file" in rec.message.lower() for rec in caplog.records)
