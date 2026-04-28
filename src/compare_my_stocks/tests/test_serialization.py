"""Round-trip tests for common.serialization."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from common.common import LimitType, Serialized, Types, UniteType, UseCache
from common.serialization import (
    SCHEMA_VERSION,
    _decode,
    _encode,
    dump_serialized,
    is_json_file,
    load_serialized,
)
from engine.parameters import Parameters
from processing.actondata import ActOnData


# ---------------------------------------------------------------------------
# Primitive round-trips
# ---------------------------------------------------------------------------
class TestEncodePrimitives:
    @pytest.mark.parametrize(
        "value",
        [None, True, False, 0, 1, -1, 3.14, "x", ""],
    )
    def test_passthrough(self, value):
        assert _encode(value) == value
        assert _decode(_encode(value)) == value

    def test_decimal(self):
        d = Decimal("3.14159")
        assert _decode(_encode(d)) == d

    def test_datetime(self):
        dt = datetime(2024, 5, 1, 12, 30, 45)
        assert _decode(_encode(dt)) == dt

    def test_date(self):
        d = date(2024, 5, 1)
        assert _decode(_encode(d)) == d

    def test_timedelta(self):
        td = timedelta(days=2, seconds=300)
        assert _decode(_encode(td)) == td

    @pytest.mark.parametrize(
        "value",
        [
            Types.PRECENTAGE,
            Types.PRECENTAGE | Types.RELTOSTART,
            UseCache.USEIFAVAILABLE,
            UniteType.NONE,
            LimitType.RANGE,
        ],
    )
    def test_intflag(self, value):
        roundtripped = _decode(_encode(value))
        assert roundtripped == value
        assert type(roundtripped) is type(value)

    def test_tuple(self):
        t = (1, "two", 3.0)
        assert _decode(_encode(t)) == t

    def test_set(self):
        s = {1, 2, 3}
        assert _decode(_encode(s)) == s

    def test_nested(self):
        v = {"a": [1, (2, 3)], "b": {"c": Decimal("1.5")}}
        assert _decode(_encode(v)) == v


# ---------------------------------------------------------------------------
# Numpy / pandas round-trips
# ---------------------------------------------------------------------------
class TestEncodeNumpyPandas:
    def test_ndarray_2d(self):
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        out = _decode(_encode(arr))
        assert isinstance(out, np.ndarray)
        assert (out == arr).all()
        assert out.dtype == arr.dtype
        assert out.shape == arr.shape

    def test_ndarray_int(self):
        arr = np.array([1, 2, 3], dtype=np.int64)
        out = _decode(_encode(arr))
        assert (out == arr).all()
        assert out.dtype == np.int64

    def test_dataframe_simple(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        out = _decode(_encode(df))
        assert isinstance(out, pd.DataFrame)
        assert (out.values == df.values).all()
        assert list(out.columns) == list(df.columns)

    def test_dataframe_datetime_index(self):
        df = pd.DataFrame(
            {"x": [1.0, 2.0, 3.0]},
            index=pd.date_range("2024-01-01", periods=3, freq="D"),
        )
        out = _decode(_encode(df))
        assert (out.values == df.values).all()
        # split orient encodes index as iso strings; values match by position.

    def test_series(self):
        s = pd.Series([1.0, 2.0, 3.0], name="x")
        out = _decode(_encode(s))
        assert isinstance(out, pd.Series)
        assert (out.values == s.values).all()
        assert out.name == "x"

    def test_np_scalar(self):
        v = np.float64(3.14)
        assert _decode(_encode(v)) == pytest.approx(3.14)


# ---------------------------------------------------------------------------
# Object round-trips (Parameters, ActOnData)
# ---------------------------------------------------------------------------
class TestEncodeObjects:
    def test_parameters_roundtrip(self):
        p = Parameters()
        p.fromdate = datetime(2024, 1, 1)
        p.todate = datetime(2024, 12, 31)
        p.groups = ["G1", "G2"]
        p.selected_stocks = ["AAPL", "MSFT"]
        p.compare_with = "SPY"
        p.type = Types.PRECENTAGE | Types.RELTOSTART
        p.use_cache = UseCache.USEIFAVAILABLE
        p.limit_by = LimitType.RANGE

        out = _decode(_encode(p))
        assert isinstance(out, Parameters)
        assert out.compare_with == "SPY"
        assert out.fromdate == datetime(2024, 1, 1)
        assert out.todate == datetime(2024, 12, 31)
        assert out.groups == ["G1", "G2"]
        assert out.selected_stocks == ["AAPL", "MSFT"]
        assert out.type == (Types.PRECENTAGE | Types.RELTOSTART)
        assert out.use_cache == UseCache.USEIFAVAILABLE
        assert out.limit_by == LimitType.RANGE

    def test_parameters_excludes_baseclass(self):
        # __getstate__ excludes _baseclass; loaded object must not carry it.
        p = Parameters()
        out = _decode(_encode(p))
        assert "_baseclass" not in out.__dict__

    def test_actondata_roundtrip(self):
        df = pd.DataFrame({"AAPL": [1.0, 2.0, 3.0], "MSFT": [10.0, 20.0, 30.0]})
        arr = np.array([[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]])
        act = ActOnData(arr, df, Types.PRECENTAGE, df.copy(), "SPY", inputData=None)

        out = _decode(_encode(act))
        assert isinstance(out, ActOnData)
        assert out.compare_with == "SPY"
        assert out.type == Types.PRECENTAGE
        assert (out.arr == arr).all()
        assert (out.df.values == df.values).all()
        assert (out.fulldf.values == df.values).all()

    def test_actondata_excludes_ds(self):
        df = pd.DataFrame({"x": [1.0]})
        act = ActOnData(np.array([[1.0]]), df, Types.PRECENTAGE, df, "x", inputData="not-pickled")
        out = _decode(_encode(act))
        assert "_ds" not in out.__dict__


# ---------------------------------------------------------------------------
# Full Serialized envelope
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_serialized():
    df = pd.DataFrame(
        {"AAPL": [1.0, 2.0, 3.0], "MSFT": [10.0, 20.0, 30.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    arr = np.array([[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]])
    p = Parameters()
    p.fromdate = datetime(2024, 1, 1)
    p.todate = datetime(2024, 12, 31)
    p.compare_with = "SPY"
    p.selected_stocks = ["AAPL", "MSFT"]
    p.type = Types.PRECENTAGE | Types.RELTOSTART
    act = ActOnData(arr, df, Types.PRECENTAGE, df.copy(), "SPY", inputData=None)
    return Serialized(
        origdata=df,
        beforedata=df.copy(),
        afterdata=df.copy(),
        act=act,
        parameters=p,
        Groups={"G1": ["AAPL", "MSFT"], "G2": ["TSLA"]},
    )


class TestDumpLoad:
    def test_roundtrip_via_disk(self, sample_serialized, tmp_path):
        out = tmp_path / "data.json"
        dump_serialized(sample_serialized, out)
        assert out.exists()
        assert out.stat().st_size > 0

        loaded = load_serialized(out)
        assert isinstance(loaded, Serialized)
        assert loaded.Groups == {"G1": ["AAPL", "MSFT"], "G2": ["TSLA"]}
        assert (loaded.origdata.values == sample_serialized.origdata.values).all()
        assert (loaded.beforedata.values == sample_serialized.beforedata.values).all()
        assert (loaded.afterdata.values == sample_serialized.afterdata.values).all()
        assert loaded.parameters.compare_with == "SPY"
        assert loaded.parameters.type == (Types.PRECENTAGE | Types.RELTOSTART)
        assert loaded.act.compare_with == "SPY"
        assert (loaded.act.arr == sample_serialized.act.arr).all()
        assert (loaded.act.df.values == sample_serialized.act.df.values).all()

    def test_schema_version_present(self, sample_serialized, tmp_path):
        import json

        out = tmp_path / "data.json"
        dump_serialized(sample_serialized, out)
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["schema_version"] == SCHEMA_VERSION

    def test_unsupported_schema_version_rejected(self, sample_serialized, tmp_path):
        import json

        out = tmp_path / "data.json"
        dump_serialized(sample_serialized, out)
        doc = json.loads(out.read_text(encoding="utf-8"))
        doc["schema_version"] = 999
        out.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ValueError, match="schema_version"):
            load_serialized(out)

    def test_is_json_file_detects_format(self, sample_serialized, tmp_path):
        json_path = tmp_path / "new.json"
        dump_serialized(sample_serialized, json_path)
        assert is_json_file(json_path)

        pickle_path = tmp_path / "old.pkl"
        import pickle

        with open(pickle_path, "wb") as f:
            pickle.dump(sample_serialized, f)
        assert not is_json_file(pickle_path)

    def test_groups_with_empty_dict(self, sample_serialized, tmp_path):
        s = sample_serialized._replace(Groups={})
        out = tmp_path / "data.json"
        dump_serialized(s, out)
        assert load_serialized(out).Groups == {}

    def test_none_fields(self, tmp_path):
        s = Serialized(
            origdata=None,
            beforedata=None,
            afterdata=None,
            act=None,
            parameters=None,
            Groups={},
        )
        out = tmp_path / "data.json"
        dump_serialized(s, out)
        loaded = load_serialized(out)
        assert loaded.origdata is None
        assert loaded.act is None
        assert loaded.parameters is None
