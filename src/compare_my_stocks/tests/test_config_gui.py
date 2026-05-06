"""Round-trip tests for the small config GUI's save path.

The GUI used to dump the typed config object via ruamel's `unsafe` mode,
which leaked `_changed_keys: !!set {...}` internals, forced every default
field into the file, and stripped header comments. The save path now
patches a round-trip parse instead, leaving omitted defaults / comments /
tags alone.
"""
from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pytest


SAMPLE_YAML = textwrap.dedent(
    """\
    #yaml-language-server: $schema=myconfig.schema.json
    !Config
      Sources: !SourcesConf
        IBSource: !IBSourceConf
          HostIB: '127.0.0.1'
          PortIB: 7596
          IBSrvPort: 9091
          # keep this comment
          PromptOnConnectionFail: true
        PolySource: !PolyConf
          Key: "OLDKEY"
      TransactionHandlers: !TransactionHandlersConf
        IBStatement: !IBStatementConf
          SrcFile: "C:\\\\path\\\\old.csv"
        IB: !IBConf
          FlexToken: '111'
          FlexQuery: '222'
          DoQuery: false
          Use: !UseCache FORCEUSE
      Input: !InputConf
        InputSource: !InputSourceType IB
      Running: !RunningConf
        VerifySaving: !VerifySave "Ask"
        LoadLastAtBegin: true
    """
)


@pytest.fixture
def sample_path(tmp_path: Path) -> Path:
    p = tmp_path / "myconfig.yaml"
    p.write_text(SAMPLE_YAML, encoding="utf-8")
    return p


def _import_helpers():
    # Importing config_gui pulls in PySide6 but does not start an event loop.
    from gui import config_gui  # type: ignore
    return config_gui


def test_rt_save_preserves_comments_and_tags(sample_path: Path):
    cg = _import_helpers()

    yaml, data = cg._load_rt(sample_path)
    cg._rt_set(data, ["Sources", "IBSource"], "HostIB", "10.0.0.5")
    cg._rt_set(data, ["Sources", "IBSource"], "PortIB", 4002)
    cg._rt_set(data, ["Sources", "PolySource"], "Key", "NEWKEY")
    cg._rt_set(data, ["TransactionHandlers", "IBStatement"], "SrcFile",
               r"C:\new\path.csv")
    cg._rt_set(data, ["TransactionHandlers", "IB"], "FlexToken", "999")
    cg._dump_rt(yaml, data, sample_path)

    out = sample_path.read_text(encoding="utf-8")

    # Edits applied
    assert "10.0.0.5" in out
    assert "4002" in out
    assert "NEWKEY" in out
    assert "OLDKEY" not in out
    assert "999" in out
    assert "111" not in out

    # Header / inline comments preserved
    assert "yaml-language-server" in out
    assert "keep this comment" in out

    # No typed-dump leakage
    assert "_changed_keys" not in out
    assert "!!python/object/apply" not in out

    # Top-level !Config tag preserved
    assert "!Config" in out

    # Sections the user did NOT have in the source file are NOT introduced
    # (this is the bug we are guarding against — typed re-dump would emit
    # File:, Symbols:, Voila:, UI:, Earnings:, Testing:, TrackStock:, etc.).
    for section in ("File:", "Symbols:", "Voila:", "Earnings:",
                    "Testing:", "TrackStock:", "UI:", "Jupyter:"):
        # match only at column 0 (top-level mapping keys), not as a substring
        # of e.g. `SrcFile:`.
        assert f"\n{section}" not in "\n" + out, (
            f"Unexpected top-level section {section!r} introduced by save"
        )


def test_rt_save_preserves_enum_tags(sample_path: Path):
    cg = _import_helpers()
    from common.common import InputSourceType, VerifySave  # type: ignore

    yaml, data = cg._load_rt(sample_path)
    cg._rt_set(data, ["Input"], "InputSource", InputSourceType.Cache)
    cg._rt_set(data, ["Running"], "VerifySaving", VerifySave.ForceSave)
    # Enum at a path that didn't exist before
    cg._rt_set(data, ["TransactionHandlers", "IB"], "Use",
               __import__("common.common", fromlist=["UseCache"]).UseCache.DONT)
    cg._dump_rt(yaml, data, sample_path)

    out = sample_path.read_text(encoding="utf-8")

    # Enums round-trip with their !TypeName tag (the unsafe loader needs the
    # tag to re-hydrate them on next read).
    assert "!InputSourceType" in out and "Cache" in out
    assert "!VerifySave" in out and "ForceSave" in out
    assert "!UseCache" in out and "DONT" in out

    # File still parses as round-trip YAML with the expected tags.
    from ruamel.yaml import YAML
    rt = YAML()
    reparsed = rt.load(io.StringIO(out))
    assert reparsed.tag.value == "!Config"


@pytest.fixture
def real_user_config(tmp_path: Path) -> Path:
    """Copy of the in-tree default config (src/compare_my_stocks/data/myconfig.yaml)."""
    src = (Path(__file__).resolve().parent.parent / "data" / "myconfig.yaml")
    if not src.exists():
        pytest.skip(f"No reference config at {src}")
    p = tmp_path / "myconfig.yaml"
    p.write_bytes(src.read_bytes())
    return p


def test_gui_save_only_writes_edited_fields(real_user_config: Path, qtbot=None):
    """Drive the actual GUI: change exactly one field, save, assert that's the
    only thing that changed in the file."""
    cg = _import_helpers()
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    original_text = real_user_config.read_text(encoding="utf-8")

    win = cg.ConfigEditor(real_user_config)
    try:
        # Find the HostIB QLineEdit and edit it via setText (which fires
        # textChanged → marks dirty, just like a real edit would).
        target = None
        for f in win._fields:
            if f.owner_path == ["Sources", "IBSource"] and f.attr == "HostIB":
                target = f
                break
        assert target is not None, "HostIB field not found in GUI"
        original_host = target.widget.text()
        assert original_host == "127.0.0.1"

        target.widget.setText("9.9.9.9")
        assert target.dirty is True
        assert sum(1 for f in win._fields if f.dirty) == 1, \
            "exactly one field should be dirty"

        win.save()
    finally:
        win.deleteLater()
        app.processEvents()

    new_text = real_user_config.read_text(encoding="utf-8")

    # ruamel reformats on dump (whitespace, quoting, line wrapping, bool
    # case). Compare semantically: walk both parsed structures, collect
    # (dotted-path -> value) pairs, assert exactly one entry differs.
    from ruamel.yaml import YAML
    rt = YAML(typ="unsafe")
    # Re-use the project's class registration so tagged scalars round-trip.
    from config.newconfig import ConfigLoader  # type: ignore
    rt = ConfigLoader.get_yaml()

    def _flatten(obj, prefix=""):
        out = {}
        if hasattr(obj, "__dict__") and not isinstance(obj, (str, bytes)):
            items = vars(obj).items()
        elif isinstance(obj, dict):
            items = obj.items()
        else:
            return {prefix: obj}
        for k, v in items:
            if str(k).startswith("_"):
                continue
            key = f"{prefix}.{k}" if prefix else str(k)
            if hasattr(v, "__dict__") and not isinstance(v, (str, bytes, int, float, bool)):
                out.update(_flatten(v, key))
            elif isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
        return out

    import io
    before = _flatten(rt.load(io.StringIO(original_text)))
    after = _flatten(rt.load(io.StringIO(new_text)))

    diffs = {k: (before.get(k), after.get(k))
             for k in set(before) | set(after)
             if before.get(k) != after.get(k)}

    assert diffs == {"Sources.IBSource.HostIB": ("127.0.0.1", "9.9.9.9")}, (
        f"expected only HostIB to change, got: {diffs}"
    )

    # No leakage from the typed-dump bug.
    assert "_changed_keys" not in new_text

    # No leakage from the typed-dump bug.
    assert "_changed_keys" not in new_text


def test_rt_save_creates_missing_intermediate_paths(tmp_path: Path):
    cg = _import_helpers()

    src = tmp_path / "minimal.yaml"
    src.write_text("!Config\n  Sources: !SourcesConf\n    IBSource: !IBSourceConf\n      HostIB: '127.0.0.1'\n",
                   encoding="utf-8")
    yaml, data = cg._load_rt(src)
    # PolySource map doesn't exist yet — _rt_set should create it.
    cg._rt_set(data, ["Sources", "PolySource"], "Key", "ABC123")
    cg._dump_rt(yaml, data, src)

    out = src.read_text(encoding="utf-8")
    assert "PolySource" in out
    assert "ABC123" in out
    # Original key is still there
    assert "127.0.0.1" in out
