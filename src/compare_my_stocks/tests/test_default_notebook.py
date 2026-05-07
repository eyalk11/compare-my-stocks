"""Execute the embedded default notebook end-to-end against real serialized data.

Strategy: point ``config.File.DataFilePtr`` at a temp pointer that contains the
path to a serialized data file, then run every cell of
``data/jupyter/defaultnotebook.ipynb`` in-process via nbclient. The notebook
already has a fallback path for when ``RapidYFinanaceKey`` is absent (its
``query_symbol`` raises and the markdown fallback renders), so it runs
hermetically without network access.

The test prefers a synthetic serialized data file generated in a tmp dir, so
the test does not rely on the developer's ``~/.compare_my_stocks`` state. If
synthesizing data is not possible (e.g. ActOnData wiring breaks), it falls
back to the user's real ``~/.compare_my_stocks/serialized.dat.json`` and skips
when that is also unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "jupyter" / "defaultnotebook.ipynb"
)


def _build_synthetic_serialized(tmp_path: Path) -> Path:
    """Build a tiny synthetic Serialized + dump it to JSON. Returns the path
    written. Raises if the project's serialization isn't compatible."""
    from common.common import Serialized
    from processing.actondata import ActOnData
    from common.serialization import dump_serialized

    # Three symbols, 60 daily rows — enough for calc_closeness (interval=30 →
    # needs ~2*interval rows) and matplotlib date conversion.
    from matplotlib.dates import date2num

    rng = np.random.default_rng(42)
    # The real serialized.act.df / afterdata indices are matplotlib float
    # ordinals (date2num); the notebook's convert_df_dates relies on that.
    raw_idx = pd.date_range("2024-01-01", periods=60, freq="D")
    idx = pd.Index([float(date2num(d.to_pydatetime())) for d in raw_idx])
    cols = ["AAA", "BBB", "CCC"]
    df = pd.DataFrame(rng.uniform(100, 200, size=(60, 3)), index=idx, columns=cols)

    # ActOnData needs arr/df/type/fulldf/compare_with/inputData. We pass the
    # bare minimum that survives __getstate__ + json round-trip.
    from common.common import Types
    act = ActOnData(
        arr=df.to_numpy(),
        df=df,
        type=Types.PRICE,
        fulldf=df,
        compare_with=None,
        inputData=None,
    )

    s = Serialized(
        origdata=df.copy(),
        beforedata=df.copy(),
        afterdata=df.copy(),
        act=act,
        parameters=None,
        Groups={},
    )

    out = tmp_path / "synth_serialized.json"
    dump_serialized(s, out)
    return out


def _existing_real_serialized() -> Path | None:
    """Fallback: look for the developer's actual serialized data."""
    candidates = [
        Path(os.path.expanduser("~/.compare_my_stocks/serialized.dat.json")),
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 0:
            return c
    return None


@pytest.fixture
def serialized_data_path(tmp_path: Path) -> Path:
    """Provide a serialized-data file the notebook can load. Prefer synthetic;
    fall back to the user's real file; skip if neither works."""
    try:
        return _build_synthetic_serialized(tmp_path)
    except Exception as e:  # pragma: no cover - depends on local serialization wiring
        real = _existing_real_serialized()
        if real is None:
            pytest.skip(f"no serialized data available (synth failed: {e!r})")
        return real


@pytest.fixture
def data_file_pointer(tmp_path: Path, serialized_data_path: Path, monkeypatch):
    """Build an isolated COMPARE_STOCK_PATH dir with a copy of the user's
    config + a DATA_FILE pointer to our synthetic serialized data.

    The notebook runs in a kernel subprocess that re-loads config from disk,
    so we cannot patch it in-process — instead we redirect the whole data
    directory via the ``COMPARE_STOCK_PATH`` env var (which the subprocess
    kernel inherits). The user's real ``~/.compare_my_stocks`` is left
    untouched.
    """
    import shutil

    real_data = Path(os.path.expanduser("~/.compare_my_stocks"))
    # Config can live either at the data-dir root or under data/ — accept both.
    candidates = [real_data / "myconfig.yaml", real_data / "data" / "myconfig.yaml"]
    real_cfg = next((c for c in candidates if c.exists()), None)
    if real_cfg is None:
        pytest.skip(f"no myconfig.yaml under {real_data} — cannot seed isolated dir")

    iso = tmp_path / "compare_my_stocks_iso"
    iso.mkdir()
    shutil.copy(real_cfg, iso / "myconfig.yaml")

    pointer = iso / "DATA_FILE"
    pointer.write_text(str(serialized_data_path), encoding="utf-8")

    monkeypatch.setenv("COMPARE_STOCK_PATH", str(iso))
    return pointer


def test_default_notebook_executes(data_file_pointer):
    """Run every cell in defaultnotebook.ipynb. Test passes if no cell raises."""
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")  # needed by nbclient

    nb = nbformat.read(NOTEBOOK_PATH, as_version=4)

    # Append an assertion cell that proves load_data actually returned our
    # synthetic Serialized (rather than silently logging "data file not
    # available" and leaving mydata=None).
    nb.cells.append(nbformat.v4.new_code_cell(
        "assert mydata is not None, 'load_data returned None — DataFilePtr not redirected'\n"
        "assert hasattr(mydata, 'act') and mydata.act is not None\n"
        "assert mydata.act.df.shape[0] > 0 and mydata.act.df.shape[1] > 0\n"
    ))

    # Run with the same Python interpreter used by pytest (the venv11 kernel
    # may not be registered as a named kernelspec, so we ask nbclient to use
    # the default kernel and pin it to "python3" via the metadata).
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }

    client = nbclient.NotebookClient(
        nb, timeout=120, kernel_name="python3",
        resources={"metadata": {"path": str(NOTEBOOK_PATH.parent)}},
    )
    client.execute()

    # Sanity check: the load_data cell should have produced a non-None mydata
    # (we can't introspect the kernel post-shutdown, so we settle for "no cell
    # raised" plus checking the recorded outputs include something for the
    # 'Data' / 'Correlation' cells).
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    # At least one cell must have produced output (the correlation table or
    # the fallback markdown both count).
    assert any(c.get("outputs") for c in code_cells), \
        "no code cell produced any output — notebook may have silently no-op'd"
