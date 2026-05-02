"""Tests for graph save/load JSON round-trip.

GraphsHandler persists user-saved graph configurations to graphs.json:
- save_graph → internal_save → json.dumps(self.graphs, cls=EnhancedJSONEncoder)
- load_existing_graphs → json.load → Parameters.load_from_json_dict per entry

These tests exercise the encoder + the loader without spinning up
the Qt-dependent GraphsHandler class itself.
"""

import datetime
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(os.path.dirname(os.path.abspath(__file__))).parent))

from common.common import EnhancedJSONEncoder, Types, UniteType
from engine.parameters import Parameters, copyit
from engine.symbols import SimpleSymbol


# ============================================================================
# Encoder behavior
# ============================================================================

class TestEnhancedJSONEncoder:
    """EnhancedJSONEncoder converts dataclasses to dicts and AbstractSymbol
    instances to their .dic — both used by Parameters serialization."""

    def test_dataclass_serialized_as_dict(self):
        p = Parameters(type=Types.PRICE, groups=['FANG'])
        out = json.loads(json.dumps(p, cls=EnhancedJSONEncoder))
        assert isinstance(out, dict)
        # The fields we set come back.
        assert out.get('groups') == ['FANG']
        # int-flag types are serialized as their int value.
        assert out.get('type') == int(Types.PRICE)

    def test_simple_symbol_with_dic_serialized(self):
        """An AbstractSymbol with a .dic falls back to encoder default,
        which returns o.dic."""
        s = SimpleSymbol('AAPL')
        s._dic = {'symbol': 'AAPL', 'conId': 12345}
        out = json.loads(json.dumps(s, cls=EnhancedJSONEncoder))
        assert out == {'symbol': 'AAPL', 'conId': 12345}


# ============================================================================
# Parameters load_from_json_dict
# ============================================================================

class TestLoadFromJsonDict:
    """load_from_json_dict reverses the encoder: parses date-named fields
    via dateutil and instantiates Parameters(**dic)."""

    def test_round_trip_preserves_simple_fields(self):
        p = Parameters(
            type=Types.PRICE | Types.PRECENTAGE,
            groups=['FANG', 'Tech'],
            compare_with='QQQ',
            use_groups=True,
        )
        # Serialize → parse JSON → restore.
        s = json.dumps(p, cls=EnhancedJSONEncoder)
        d = json.loads(s)
        restored = Parameters.load_from_json_dict(d)
        assert restored.groups == p.groups
        assert restored.compare_with == p.compare_with
        assert restored.use_groups == p.use_groups
        # Types is a Flag — equality works on the int value.
        assert int(restored.type) == int(p.type)

    def test_date_fields_round_trip_to_datetime(self):
        """Any field with 'date' in the name is dateutil-parsed back to
        a datetime by load_from_json_dict (parameters.py:90-92)."""
        p = Parameters()
        p.fromdate = datetime.datetime(2024, 1, 15, tzinfo=datetime.timezone.utc)
        p.todate = datetime.datetime(2024, 6, 30, tzinfo=datetime.timezone.utc)
        d = json.loads(json.dumps(p, cls=EnhancedJSONEncoder))
        # The serialized form is a string; loader must re-parse.
        restored = Parameters.load_from_json_dict(d)
        assert isinstance(restored.fromdate, datetime.datetime)
        # Compare ignoring sub-second precision (json may strip).
        assert restored.fromdate.date() == datetime.date(2024, 1, 15)
        assert restored.todate.date() == datetime.date(2024, 6, 30)

    def test_unitetype_round_trip(self):
        p = Parameters(unite_by_group=UniteType.SUM | UniteType.ADDPROT)
        d = json.loads(json.dumps(p, cls=EnhancedJSONEncoder))
        restored = Parameters.load_from_json_dict(d)
        assert int(restored.unite_by_group) == int(UniteType.SUM | UniteType.ADDPROT)


# ============================================================================
# Multi-graph save/load round-trip via files
# ============================================================================

class TestGraphsFileRoundTrip:
    """Mirror the on-disk shape that GraphsHandler.internal_save writes:
    {graph_name: Parameters_dict, ...} dumped as JSON, parsed back into a
    {graph_name: Parameters} dict."""

    def test_round_trip_via_tmpfile(self, tmp_path):
        graphs = {
            'fang_pct': Parameters(
                type=Types.PRICE | Types.PRECENTAGE,
                groups=['FANG'], use_groups=True, compare_with='QQQ'),
            'pharma_diff': Parameters(
                type=Types.PRICE | Types.DIFF,
                groups=['Pharma'], use_groups=True, compare_with='SPY'),
        }
        fp = tmp_path / 'graphs.json'
        fp.write_text(json.dumps(graphs, cls=EnhancedJSONEncoder))

        # Now read back like load_existing_graphs does.
        loaded_raw = json.load(open(fp, 'rt'))
        restored = {k: Parameters.load_from_json_dict(v) for k, v in loaded_raw.items()}

        assert set(restored.keys()) == {'fang_pct', 'pharma_diff'}
        assert restored['fang_pct'].compare_with == 'QQQ'
        assert restored['pharma_diff'].groups == ['Pharma']

    def test_copyit_produces_independent_parameters(self):
        """internal_save uses copyit() to detach the saved entry from the
        live params — mutating the live one mustn't change the saved one."""
        live = Parameters(groups=['FANG'])
        snapshot = copyit(live)
        live.groups.append('Tech')
        # The snapshot's groups list should NOT have Tech.
        assert 'Tech' not in snapshot.groups
        assert snapshot.groups == ['FANG']
