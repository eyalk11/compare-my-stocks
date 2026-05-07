"""Unit tests for InternalCompareEngine.call_graph_generator.

Builds an engine via __new__ with all collaborators mocked — no Qt, no
DataGenerator, no real graph. Covers:
  * empty df → emits "No Data" and returns without invoking the generator
  * non-empty df → invokes _generator.gen_actual_graph and emits success
  * generator raises TypeError → emits failure and re-raises
  * transaction lookup is performed only for non-percentage / non-united types
"""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from common.common import Types, UniteType
from engine.compareengine import InternalCompareEngine


class _StubEngine(InternalCompareEngine):
    """Concrete subclass that fills in every abstract member with no-ops."""
    InputSource = property(lambda self: None)
    adjust_date = property(lambda self: 0)
    colswithoutext = property(lambda self: set())
    final_columns = property(lambda self: [])
    def get_portfolio_stocks(self): return []
    input_processor = property(lambda self: None)
    maxValue = property(lambda self: 0)
    maxdate = property(lambda self: None)
    minValue = property(lambda self: 0)
    mindate = property(lambda self: None)
    def process(self, *a, **k): pass
    def serialized_data(self): return {}
    def show_hide(self, *a, **k): pass
    to_use_ext = True
    transaction_handler = None
    usable_symbols = property(lambda self: set())
    used_unitetype = None


def _make_engine(*, type_=Types.PRICE, unite=UniteType.NONE):
    eng = _StubEngine.__new__(_StubEngine)
    eng.statusChanges = MagicMock()
    eng.finishedGeneration = MagicMock()
    eng._inp = MagicMock()
    eng._inp.failed_to_get_new_data = None
    eng._tr = MagicMock()
    eng._generator = MagicMock()

    params = MagicMock()
    params.unite_by_group = unite
    params.isline = True
    params.starthidden = False
    params.is_forced = True
    eng._params = params
    eng.used_unitetype = unite
    return eng


def test_call_graph_generator_empty_df_emits_no_data():
    eng = _make_engine()
    eng.call_graph_generator(pd.DataFrame(), just_upd=0, type=Types.PRICE, orig_data=None)
    eng.statusChanges.emit.assert_called_with("No Data For Graph!")
    eng._generator.gen_actual_graph.assert_not_called()


def test_call_graph_generator_happy_path_emits_success():
    eng = _make_engine()
    df = pd.DataFrame({"AAA": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
    eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    eng._generator.gen_actual_graph.assert_called_once()
    # Success status emitted
    msgs = [c.args[0] for c in eng.statusChanges.emit.call_args_list]
    assert any("Generated Graph" in m for m in msgs)
    # finishedGeneration fires
    eng.finishedGeneration.emit.assert_called_once_with(1)
    # is_forced reset
    assert eng._params.is_forced is False


def test_call_graph_generator_old_data_message_when_failed_to_get_new():
    eng = _make_engine()
    eng._inp.failed_to_get_new_data = True
    df = pd.DataFrame({"AAA": [1.0]}, index=pd.date_range("2024-01-01", periods=1))
    eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    msgs = [c.args[0] for c in eng.statusChanges.emit.call_args_list]
    assert any("old data" in m for m in msgs)


def test_call_graph_generator_typeerror_emits_failure_and_reraises():
    eng = _make_engine()
    eng._generator.gen_actual_graph.side_effect = TypeError("boom")
    df = pd.DataFrame({"AAA": [1.0]}, index=pd.date_range("2024-01-01", periods=1))
    with pytest.raises(TypeError):
        eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    msgs = [c.args[0] for c in eng.statusChanges.emit.call_args_list]
    assert any("failed generating graph" in m for m in msgs)


def test_call_graph_generator_fetches_transaction_data_for_price_type():
    """Plain PRICE without unite → transaction handler is queried."""
    eng = _make_engine(type_=Types.PRICE, unite=UniteType.NONE)
    df = pd.DataFrame({"AAA": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
    eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    eng._tr.get_data_for_graph.assert_called_once()


def test_call_graph_generator_skips_transaction_data_for_percentage():
    """PRECENTAGE flag set → transaction lookup skipped."""
    eng = _make_engine()
    df = pd.DataFrame({"AAA": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
    eng.call_graph_generator(
        df, just_upd=0, type=Types.PRICE | Types.PRECENTAGE, orig_data=None,
    )
    eng._tr.get_data_for_graph.assert_not_called()


def test_call_graph_generator_skips_transaction_data_for_united_sum():
    eng = _make_engine(unite=UniteType.SUM)
    eng._params.unite_by_group = UniteType.SUM
    df = pd.DataFrame({"AAA": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
    eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    eng._tr.get_data_for_graph.assert_not_called()


def test_call_graph_generator_resets_failed_to_get_new_data():
    eng = _make_engine()
    eng._inp.failed_to_get_new_data = "stale"
    df = pd.DataFrame({"AAA": [1.0]}, index=pd.date_range("2024-01-01", periods=1))
    eng.call_graph_generator(df, just_upd=0, type=Types.PRICE, orig_data=None)
    assert eng._inp.failed_to_get_new_data is None
