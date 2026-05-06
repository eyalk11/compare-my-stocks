"""Regression tests for forminitializer slider sync.

When the data range changes (Type/Unite switch -> minMaxChanged emits new bounds),
update_rangeb / update_range_num / update_ranges(FORCE) must reset
Parameters.valuerange and numrange too. Otherwise the stale values from a
previous Type filter out every symbol on the next render and the user sees
"No Data For Graph!".
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from engine.parameters import Parameters
from gui.forminitializer import FormInitializer
from gui.formobserverinterface import ResetRanges


class _TestableFI(FormInitializer):
    """FormInitializer with concrete window/graphObj setters so we can construct
    the object without spinning up the real Qt MainWindow."""
    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, value):
        self._window = value

    @property
    def graphObj(self):
        return self._graphObj

    @graphObj.setter
    def graphObj(self, value):
        self._graphObj = value


def _make(min_v, max_v, n_options):
    obj = _TestableFI.__new__(_TestableFI)
    obj.disable_slider_values_updates = False
    obj.window = SimpleNamespace(min_crit=MagicMock(), max_num=MagicMock())
    obj.graphObj = SimpleNamespace(
        params=Parameters(valuerange=[12.09, 332.0825], numrange=(0, 5)),
        minValue=min_v,
        maxValue=max_v,
        colswithoutext={f"S{i}" for i in range(n_options)},
    )
    return obj


def test_update_rangeb_resets_stale_valuerange():
    obj = _make(0.0, 169564.895, 4)
    obj.update_rangeb((0.0, 169564.895))
    assert obj.graphObj.params.valuerange == [0.0, 169564.895]


def test_update_range_num_resets_numrange():
    obj = _make(0.0, 100.0, 10)
    obj.update_range_num(10)
    assert obj.graphObj.params.numrange == (None, None)


def test_update_ranges_force_resets_both():
    obj = _make(0.0, 169564.895, 4)
    obj.update_ranges(reset_type=ResetRanges.FORCE)
    assert obj.graphObj.params.valuerange == [0.0, 169564.895]
    assert obj.graphObj.params.numrange == (None, None)


def test_update_ranges_non_force_leaves_params_alone():
    obj = _make(0.0, 169564.895, 4)
    original = list(obj.graphObj.params.valuerange)
    obj.update_ranges(reset_type=ResetRanges.IfAPROP)
    assert obj.graphObj.params.valuerange == original
