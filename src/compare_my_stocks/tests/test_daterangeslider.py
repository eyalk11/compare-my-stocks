"""Tests that QDateRangeSlider.update_obj derives its range from start/end
(as forminitializer feeds it from hist_file via mindate/maxdate) and that it
does not raise when the range collapses to a single day -- which is the
boundary case that was crashing MainWindow.run when there were no
transactions overlapping the loaded history range.
"""
import sys

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_slider():
    from gui.daterangeslider import QDateRangeSlider
    return QDateRangeSlider()


def test_update_obj_year_range(qapp):
    s = _make_slider()
    s.start = pd.Timestamp("2025-04-25")
    s.end = pd.Timestamp("2026-04-24")
    s.update_obj()
    assert len(s.options) == 365
    assert s.singleStep() == pytest.approx(1.0)
    assert s.pageStep() == pytest.approx(5.0)


def test_update_obj_single_day_does_not_raise(qapp):
    s = _make_slider()
    s.start = pd.Timestamp("2025-04-25")
    s.end = pd.Timestamp("2025-04-25")
    s.update_obj()
    assert len(s.options) == 1


def test_update_obj_uninitialized_returns_true(qapp):
    s = _make_slider()
    assert s.update_obj() is True


def test_range_from_inputdata_mindate_maxdate(qapp):
    """Simulate the forminitializer wiring: slider.start/end = inputdata.mindate/maxdate
    (which inputprocessor sets from min/max of hist_file's _hist_by_date keys).
    Even with NO transactions overlapping the history window, the slider must
    cover the full history range from hist_file."""
    hist_keys = pd.date_range("2025-04-25", "2026-04-24", freq="D")
    mindate, maxdate = min(hist_keys), max(hist_keys)
    s = _make_slider()
    s.start = mindate
    s.end = maxdate
    s.update_obj()
    assert len(s.options) == len(hist_keys)
