"""JSON-based serialization for the ``Serialized`` namedtuple.

Replaces ``pickle.dump``/``pickle.load`` for the GUI → Jupyter handoff
file.  Non-JSON-native values (DataFrames, ndarrays, datetimes,
IntFlags, ``Parameters``, ``ActOnData``) are encoded with a
``__type__`` tag so the decoder can rebuild them without arbitrary
class resolution from the file.

The envelope is a plain dict with a ``schema_version`` field; pydantic
isn't used because shiboken's import hook (loaded with PySide6 in the
GUI process) interacts badly with pydantic's lazy ``__getattr__``.
"""
import importlib
import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common.common import Serialized

SCHEMA_VERSION = 1
_TAG = "__type__"


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------
def _encode(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, np.generic):
        return _encode(v.item())
    if isinstance(v, Decimal):
        return {_TAG: "decimal", "v": str(v)}
    if isinstance(v, datetime):
        return {_TAG: "datetime", "iso": v.isoformat()}
    if isinstance(v, date):
        return {_TAG: "date", "iso": v.isoformat()}
    if isinstance(v, timedelta):
        return {_TAG: "timedelta", "s": v.total_seconds()}
    if isinstance(v, Enum):
        cls = type(v)
        return {
            _TAG: "enum",
            "cls": f"{cls.__module__}.{cls.__name__}",
            "value": v.value,
        }
    if isinstance(v, np.ndarray):
        return {
            _TAG: "ndarray",
            "shape": list(v.shape),
            "dtype": str(v.dtype),
            "data": v.tolist(),
        }
    if isinstance(v, pd.DataFrame):
        # ``orient='split'`` keeps index + columns + data separable.
        # Multi-index columns survive as nested lists; single-index as flat.
        buf = v.to_json(orient="split", date_format="iso", date_unit="ns")
        return {
            _TAG: "dataframe",
            "split": json.loads(buf),
            "columns_nlevels": v.columns.nlevels,
            "index_dtype": str(v.index.dtype),
        }
    if isinstance(v, pd.Series):
        return {
            _TAG: "series",
            "split": json.loads(v.to_json(orient="split", date_format="iso", date_unit="ns")),
            "name": v.name,
        }
    if isinstance(v, pd.Timestamp):
        return {_TAG: "timestamp", "iso": v.isoformat()}
    if isinstance(v, dict):
        return {str(k): _encode(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_encode(x) for x in v]
    if isinstance(v, tuple):
        return {_TAG: "tuple", "items": [_encode(x) for x in v]}
    if isinstance(v, set):
        return {_TAG: "set", "items": [_encode(x) for x in v]}

    cls = type(v)
    qualified = f"{cls.__module__}.{cls.__name__}"
    if qualified.endswith(".Parameters") or qualified.endswith(".ActOnData"):
        state = v.__getstate__() if hasattr(v, "__getstate__") else dict(v.__dict__)
        return {
            _TAG: "object",
            "cls": qualified,
            "state": _encode(state),
        }
    raise TypeError(f"don't know how to encode {qualified}")


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------
def _resolve(qualified: str):
    module_name, _, attr = qualified.rpartition(".")
    return getattr(importlib.import_module(module_name), attr)


def _decode(v: Any) -> Any:
    if isinstance(v, list):
        return [_decode(x) for x in v]
    if not isinstance(v, dict):
        return v
    tag = v.get(_TAG)
    if tag is None:
        return {k: _decode(val) for k, val in v.items()}

    if tag == "decimal":
        return Decimal(v["v"])
    if tag == "datetime":
        return datetime.fromisoformat(v["iso"])
    if tag == "date":
        return date.fromisoformat(v["iso"])
    if tag == "timedelta":
        return timedelta(seconds=v["s"])
    if tag == "enum":
        return _resolve(v["cls"])(v["value"])
    if tag == "ndarray":
        return np.array(v["data"], dtype=v["dtype"]).reshape(v["shape"])
    if tag == "dataframe":
        df = pd.read_json(io.StringIO(json.dumps(v["split"])), orient="split")
        return df
    if tag == "series":
        s = pd.read_json(
            io.StringIO(json.dumps(v["split"])), orient="split", typ="series"
        )
        s.name = v.get("name")
        return s
    if tag == "timestamp":
        return pd.Timestamp(v["iso"])
    if tag == "tuple":
        return tuple(_decode(x) for x in v["items"])
    if tag == "set":
        return set(_decode(x) for x in v["items"])
    if tag == "object":
        cls = _resolve(v["cls"])
        obj = cls.__new__(cls)
        state = _decode(v["state"])
        if hasattr(obj, "__setstate__"):
            obj.__setstate__(state)
        else:
            obj.__dict__.update(state)
        return obj
    raise ValueError(f"unknown tag {tag!r}")


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------
def _to_doc(s: Serialized) -> dict:
    enc = lambda x: None if x is None else _encode(x)
    return {
        "schema_version": SCHEMA_VERSION,
        "origdata": enc(s.origdata),
        "beforedata": enc(s.beforedata),
        "afterdata": enc(s.afterdata),
        "act": enc(s.act),
        "parameters": enc(s.parameters),
        "Groups": {str(k): list(v) for k, v in (s.Groups or {}).items()},
    }


def _from_doc(doc: dict) -> Serialized:
    sv = doc.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version {sv!r} (expected {SCHEMA_VERSION})"
        )
    dec = lambda x: None if x is None else _decode(x)
    return Serialized(
        origdata=dec(doc.get("origdata")),
        beforedata=dec(doc.get("beforedata")),
        afterdata=dec(doc.get("afterdata")),
        act=dec(doc.get("act")),
        parameters=dec(doc.get("parameters")),
        Groups=dict(doc.get("Groups") or {}),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def dump_serialized(s: Serialized, path) -> None:
    Path(path).write_text(json.dumps(_to_doc(s)), encoding="utf-8")


def load_serialized(path) -> Serialized:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return _from_doc(doc)


def is_json_file(path) -> bool:
    """Cheap probe so callers can fall back to pickle for legacy files."""
    try:
        with open(path, "rb") as f:
            first = f.read(1)
    except OSError:
        return False
    return first in (b"{", b"\xef")  # JSON object or UTF-8 BOM
