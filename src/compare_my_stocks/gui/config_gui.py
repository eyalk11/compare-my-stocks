"""
Small standalone Qt GUI to view and edit the most important
compare-my-stocks configuration values in ``~/.compare_my_stocks/myconfig.yaml``.

Run with the project's working interpreter:

    .\.venv11\Scripts\python.exe src\compare_my_stocks\gui\config_gui.py
    # or
    python -m compare_my_stocks.gui.config_gui --config "C:\\Users\\me\\.compare_my_stocks\\myconfig.yaml"

The GUI exposes the fields users most commonly need to set:

* IB connection (host / port) and the IB Flex Web Service token + query
* The IB Activity Statement CSV path (``IBStatement.SrcFile``)
* The My Stocks Portfolio CSV path (``MyStocks.SrcFile``)
* RapidAPI keys: ``StockPricesHeaders``, ``SeekingAlphaHeaders``,
  ``Jupyter.RapidYFinanaceKey`` / ``RapidYFinanaceHost``
* Polygon API key
* The default ``Input.InputSource`` (IB / Polygon / Cache / ...)

The Help tab walks the user through how to obtain each of these values.
A timestamped backup of the yaml file is written next to the original
on every save.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
import traceback
from pathlib import Path

# Make the package importable when running this file directly.
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402


HELP_TEXT = r"""
<h2>How to obtain the values on this page</h2>

<h3>1. Interactive Brokers &mdash; Activity Statement (CSV)</h3>
<p>The <b>IB Statement &rarr; SrcFile</b> field is a path to an
<i>Activity Statement</i> CSV exported from the IB Client Portal. This is
used to seed open positions when the Flex query is incomplete or
unavailable.</p>
<ol>
  <li>Log in to <a href="https://www.interactivebrokers.com/sso/Login">Client Portal</a>.</li>
  <li>Go to <b>Performance &amp; Reports &rarr; Statements</b>.</li>
  <li>Pick <b>Activity</b>, set the period (typically "Last 30 days" or
      a custom range that covers your earliest trade), and choose
      <b>Format: CSV</b>.</li>
  <li>Click <b>Run</b> &rarr; <b>Download</b>. Save the file somewhere
      stable (e.g. <code>C:\Users\you\Downloads\Uxxxxx_YYYYMMDD.csv</code>).</li>
  <li>Paste the full path into <b>IB Statement &rarr; SrcFile</b>.</li>
</ol>

<h3>2. Interactive Brokers &mdash; Flex Web Service token + query</h3>
<p>The Flex Web Service lets the app pull trades automatically.</p>
<ol>
  <li>In Client Portal go to <b>Performance &amp; Reports &rarr; Flex Queries</b>.</li>
  <li>Under <b>Flex Web Service</b> click the gear / "Configure" icon and
      generate a token. Copy it into <b>FlexToken</b>.</li>
  <li>Under <b>Trade Confirmation Flex Query</b> (or
      <i>Activity Flex Query</i>) create a new query that includes at
      least <i>Trades</i>, <i>Cash Transactions</i> and
      <i>Open Positions</i>. Save it and copy its <b>Query ID</b>
      (a numeric id) into <b>FlexQuery</b>.</li>
</ol>
<p>Tokens expire periodically. If queries start failing with
<code>code 1012</code>, regenerate the token and paste the new value
here.</p>

<h3>3. IB Gateway / TWS connection</h3>
<p>The app talks to a running IB Gateway or TWS via a sidecar process.
Make sure <b>API &rarr; Settings &rarr; Enable ActiveX and Socket Clients</b>
is on, and that the <b>Socket port</b> matches <b>PortIB</b> below
(this checkout defaults to <code>7596</code>; the IB defaults are 7497
for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for
Gateway live).</p>

<h3>4. RapidAPI keys</h3>
<p>The app uses up to three RapidAPI endpoints:</p>
<ul>
  <li><b>StockPricesHeaders</b> &mdash; used by the StockPrices /
      split-adjustment path. Subscribe to a Yahoo Finance / stock price
      API on RapidAPI and paste the host (e.g.
      <code>yfinance-stock-market-data.p.rapidapi.com</code>) into
      <b>X_RapidAPI_Host</b> and the key into <b>X_RapidAPI_Key</b>.</li>
  <li><b>SeekingAlphaHeaders</b> &mdash; optional, used by the earnings
      / fundamentals lookups. Subscribe to a Seeking Alpha endpoint
      on RapidAPI and fill in host + key the same way.</li>
  <li><b>Jupyter &rarr; RapidYFinanaceKey / RapidYFinanaceHost</b> &mdash;
      used inside the embedded Jupyter notebook for ad-hoc lookups.</li>
</ul>
<p>To get a RapidAPI key:</p>
<ol>
  <li>Sign up at <a href="https://rapidapi.com">rapidapi.com</a>.</li>
  <li>Search for the API you want (e.g. "yfinance" or
      "seeking alpha").</li>
  <li>Pick the free tier (or a paid one if you need more requests),
      <b>Subscribe</b>.</li>
  <li>On the API's page open the <b>Endpoints</b> tab. The right-hand
      pane shows the <code>X-RapidAPI-Host</code> and
      <code>X-RapidAPI-Key</code> values &mdash; copy them here.</li>
</ol>

<h3>5. Polygon API key</h3>
<p>Used when <b>Input source</b> is set to <i>Polygon</i>. Sign up at
<a href="https://polygon.io">polygon.io</a>, copy the API key from the
dashboard, paste it into <b>Polygon Key</b>.</p>

<h3>Where this file lives</h3>
<p>The values are written back to the same yaml file you opened (by
default <code>~/.compare_my_stocks/myconfig.yaml</code>). A timestamped
<code>.bak.&lt;ts&gt;</code> copy is created next to it on every save.</p>
"""


def _default_config_path() -> Path:
    env = os.environ.get("COMPARE_STOCK_CONFIG_FILE")
    if env:
        return Path(env)
    base = os.environ.get("COMPARE_STOCK_PATH") or str(
        Path.home() / ".compare_my_stocks"
    )
    p = Path(base) / "myconfig.yaml"
    if p.exists():
        return p
    p2 = Path(base) / "data" / "myconfig.yaml"
    return p2 if p2.exists() else p


def _load_typed(path: Path):
    """Typed load via the project's unsafe loader — used only to populate the form."""
    from config.newconfig import ConfigLoader

    yaml = ConfigLoader.get_yaml()
    with open(path, "rt", encoding="utf-8") as f:
        return yaml.load(f)


def _split_leading_comments(text: str):
    """Split a leading block of `#` / blank lines from the rest.

    ruamel-yaml's round-trip mode discards file-level comments that appear
    before a tagged root mapping. We preserve them by stripping them off
    before parsing and re-emitting them on dump.
    """
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].lstrip().startswith("#") or not lines[i].strip()):
        i += 1
    return "".join(lines[:i]), "".join(lines[i:])


def _load_rt(path: Path):
    """Round-trip load — preserves comments, ordering, omitted defaults, existing tags."""
    from ruamel.yaml import YAML

    yaml = YAML()  # default is round-trip
    yaml.preserve_quotes = True
    with open(path, "rt", encoding="utf-8") as f:
        text = f.read()
    header, body = _split_leading_comments(text)
    data = yaml.load(body)
    if data is not None:
        # Stash the header on the parsed object so _dump_rt can re-emit it.
        data._cmsg_header = header  # type: ignore[attr-defined]
    return yaml, data


def _dump_rt(yaml, data, path: Path) -> None:
    """Whole-file round-trip dump — used by tests and as a last-resort fallback.

    Note: ruamel-yaml normalizes indentation under tagged root mappings on
    dump (`!Config\\n  Child:` → `!Config\\nChild:`), so production saves
    use :func:`_apply_text_edits` instead, which only rewrites the lines
    of edited values and leaves the rest of the file byte-for-byte intact.
    """
    import io
    buf = io.StringIO()
    yaml.dump(data, buf)
    header = getattr(data, "_cmsg_header", "") or ""
    with open(path, "wt", encoding="utf-8") as f:
        f.write(header)
        f.write(buf.getvalue())


def _format_yaml_scalar(new_val, existing):
    """Render ``new_val`` as a YAML scalar suitable for replacing ``existing``
    at its file location. Preserves any tag the existing scalar already has.
    """
    import re
    from ruamel.yaml.comments import TaggedScalar

    is_enum = hasattr(new_val, "name") and hasattr(type(new_val), "__members__")
    if is_enum:
        return f"!{type(new_val).__name__} {new_val.name}"

    tag_prefix = ""
    if isinstance(existing, TaggedScalar) and existing.tag.value:
        # existing.tag.value is e.g. '!UseCache' or 'UseCache' depending on
        # the parser; normalize to the !-prefixed form.
        t = existing.tag.value
        tag_prefix = (t if t.startswith("!") else f"!{t}") + " "

    if new_val is None:
        return tag_prefix.rstrip() if tag_prefix else ""
    if isinstance(new_val, bool):
        return f"{tag_prefix}{'true' if new_val else 'false'}"
    if isinstance(new_val, (int, float)):
        return f"{tag_prefix}{new_val}"

    s = str(new_val)
    needs_quote = (
        any(c in s for c in ":#'\"\\")
        or s.lower() in ("true", "false", "null", "yes", "no", "on", "off", "")
        or bool(re.match(r"^[-+]?[\d.]", s))
    )
    if needs_quote:
        if "'" in s and '"' not in s:
            return f'{tag_prefix}"{s}"'
        return f"{tag_prefix}'{s.replace(chr(39), chr(39)*2)}'"
    return f"{tag_prefix}{s}"


def _apply_text_edits(path: Path, rt_root, edited_fields) -> tuple[int, list[str]]:
    """Patch the value text of each edited field in-place, preserving every
    other byte of the file (indentation, comments, ordering, omitted fields).

    Returns ``(applied_count, skipped_attrs)``.
    """
    import re

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Header lines (leading comments) were stripped before parsing, so the
    # rt_root's recorded line numbers are 0-based against the *body*. Re-add
    # the header offset.
    header = getattr(rt_root, "_cmsg_header", "") or ""
    header_offset = header.count("\n") if header else 0

    applied = 0
    skipped: list[str] = []
    for f in edited_fields:
        node = rt_root
        ok = True
        for p in f.owner_path:
            if not hasattr(node, "get") or p not in node:
                ok = False
                break
            node = node[p]
        if not ok or f.attr not in node:
            skipped.append(".".join(f.owner_path + [f.attr]))
            continue

        lc = getattr(node, "lc", None)
        if lc is None:
            skipped.append(".".join(f.owner_path + [f.attr]))
            continue
        info = lc.value(f.attr)  # (val_line, val_col)
        if not info:
            skipped.append(".".join(f.owner_path + [f.attr]))
            continue
        val_line = info[0] + header_offset
        val_col = info[1]
        if val_line >= len(lines):
            skipped.append(".".join(f.owner_path + [f.attr]))
            continue

        existing = node[f.attr]
        new_val = f.getter(f.widget)
        formatted = _format_yaml_scalar(new_val, existing)

        old_line = lines[val_line]
        nl = "\n" if old_line.endswith("\n") else ""
        body = old_line.rstrip("\n")
        prefix = body[:val_col]
        rest = body[val_col:]
        # preserve trailing inline comment (whitespace + '#...')
        m = re.search(r"\s+#", rest)
        comment = rest[m.start():] if m else ""
        lines[val_line] = prefix + formatted + comment + nl
        applied += 1

    path.write_text("".join(lines), encoding="utf-8")
    return applied, skipped


def _rt_navigate_create(root, path_parts):
    """Walk into a CommentedMap, creating empty maps at missing keys."""
    from ruamel.yaml.comments import CommentedMap

    node = root
    for p in path_parts:
        if p not in node or node[p] is None:
            node[p] = CommentedMap()
        node = node[p]
    return node


def _rt_set(root, path_parts, attr, new_val):
    """Set root[path_parts...][attr] = new_val, preserving any existing tag on the leaf.

    For enum values, emit (or preserve) a !EnumTypeName TaggedScalar so the unsafe
    loader can re-hydrate them on next read.
    """
    from ruamel.yaml.comments import TaggedScalar

    node = _rt_navigate_create(root, path_parts)
    existing = node.get(attr, None) if hasattr(node, "get") else None

    is_enum = hasattr(new_val, "name") and hasattr(type(new_val), "__members__")

    if is_enum:
        tag = f"!{type(new_val).__name__}"
        # TaggedScalar.tag is read-only in recent ruamel — always replace the node
        # rather than mutating in place.
        node[attr] = TaggedScalar(value=new_val.name, tag=tag)
        return

    if isinstance(existing, TaggedScalar):
        existing.value = "" if new_val is None else str(new_val)
        return

    node[attr] = new_val


class _Field:
    """One row of the form, bound to ``getattr/setattr`` on a config object.

    ``dirty`` tracks whether the user actually edited this field. Only
    dirty fields are persisted on save — otherwise loading the form
    pre-fills every widget from typed-config defaults, and saving would
    write defaults onto fields the user never touched.
    """

    def __init__(self, owner, attr, widget, getter, setter):
        self.owner = owner
        self.attr = attr
        self.widget = widget
        self.getter = getter  # widget -> value
        self.setter = setter  # widget, value -> None
        self.dirty = False

    def load(self):
        if self.owner is None:
            return
        val = getattr(self.owner, self.attr, None)
        self.setter(self.widget, val)


def _line(initial=""):
    le = QtWidgets.QLineEdit()
    return le, (lambda w: w.text() or None), (lambda w, v: w.setText("" if v is None else str(v)))


def _line_required():
    le = QtWidgets.QLineEdit()
    return le, (lambda w: w.text()), (lambda w, v: w.setText("" if v is None else str(v)))


def _spin(minv=0, maxv=999999):
    sb = QtWidgets.QSpinBox()
    sb.setRange(minv, maxv)
    return sb, (lambda w: w.value()), (lambda w, v: w.setValue(int(v) if v is not None else 0))


def _check():
    cb = QtWidgets.QCheckBox()
    return cb, (lambda w: w.isChecked()), (lambda w, v: w.setChecked(bool(v)))


def _file_picker(parent, line_edit: QtWidgets.QLineEdit, caption: str):
    btn = QtWidgets.QPushButton("Browse…")
    def pick():
        start = line_edit.text() or str(Path.home())
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(parent, caption, start, "CSV (*.csv);;All files (*)")
        if fn:
            line_edit.setText(fn)
    btn.clicked.connect(pick)
    row = QtWidgets.QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(line_edit, 1)
    row.addWidget(btn)
    container = QtWidgets.QWidget()
    container.setLayout(row)
    return container


class ConfigEditor(QtWidgets.QMainWindow):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.setWindowTitle(f"compare-my-stocks config — {path}")
        self.resize(820, 640)

        self._fields: list[_Field] = []
        self._loading = False  # guard so widget setters during load() don't mark fields dirty

        self.cfg = None       # typed view (read-only, drives the form)
        self.rt_yaml = None   # round-trip YAML object (for writing)
        self.rt_data = None   # round-trip parsed structure (for writing)
        self._load()

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_ib_tab(), "Interactive Brokers")
        tabs.addTab(self._build_transactions_tab(), "Transactions")
        tabs.addTab(self._build_rapid_tab(), "RapidAPI / Polygon")
        tabs.addTab(self._build_input_tab(), "Input source")
        tabs.addTab(self._build_behavior_tab(), "Behavior")
        tabs.addTab(self._build_help_tab(), "Help")
        self.setCentralWidget(tabs)

        tb = self.addToolBar("main")
        act_save = tb.addAction("Save")
        act_save.triggered.connect(self.save)
        act_reload = tb.addAction("Reload")
        act_reload.triggered.connect(self.reload)
        act_open = tb.addAction("Open…")
        act_open.triggered.connect(self.open_other)

        self._loading = True
        try:
            for f in self._fields:
                f.load()
                f.dirty = False
        finally:
            self._loading = False

        self.statusBar().showMessage(f"Loaded {path}")

    # --- io ---------------------------------------------------------------
    def _load(self):
        try:
            self.cfg = _load_typed(self.path)
            self.rt_yaml, self.rt_data = _load_rt(self.path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Load failed",
                f"Could not load {self.path}:\n\n{e}\n\n{traceback.format_exc()}",
            )
            raise

    def reload(self):
        self._load()
        self._loading = True
        try:
            for f in self._fields:
                f.owner = self._resolve_owner(f.owner_path)
                f.load()
                f.dirty = False
        finally:
            self._loading = False
        self.statusBar().showMessage(f"Reloaded {self.path}")

    def save(self):
        # Only persist fields the user actually edited. Untouched fields keep
        # whatever was (or wasn't) in the file — we never write defaults onto
        # keys the user hadn't set.
        dirty_fields = [f for f in self._fields if f.dirty]
        if not dirty_fields:
            self.statusBar().showMessage("No changes to save.")
            return
        for f in dirty_fields:
            try:
                new_val = f.getter(f.widget)
                if f.owner is not None:
                    setattr(f.owner, f.attr, new_val)
                _rt_set(self.rt_data, f.owner_path, f.attr, new_val)
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Save warning",
                    f"Could not write field {f.attr}: {e}",
                )
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self.path.with_suffix(self.path.suffix + f".bak.{ts}")
            shutil.copy2(self.path, backup)
            _dump_rt(self.rt_yaml, self.rt_data, self.path)
            for f in dirty_fields:
                f.dirty = False
            n = len(dirty_fields)
            self.statusBar().showMessage(
                f"Saved {self.path} ({n} field{'' if n==1 else 's'} updated, "
                f"backup: {backup.name})"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Save failed",
                f"Writing {self.path} failed:\n\n{e}",
            )

    def open_other(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open myconfig.yaml", str(self.path.parent),
            "YAML (*.yaml *.yml);;All files (*)",
        )
        if fn:
            self.path = Path(fn)
            self.setWindowTitle(f"compare-my-stocks config — {self.path}")
            self.reload()

    # --- helpers ----------------------------------------------------------
    def _resolve_owner(self, path_parts):
        obj = self.cfg
        for p in path_parts:
            obj = getattr(obj, p, None)
            if obj is None:
                return None
        return obj

    def _bind(self, owner_path, attr, widget, getter, setter):
        owner = self._resolve_owner(owner_path)
        f = _Field(owner, attr, widget, getter, setter)
        f.owner_path = owner_path
        self._fields.append(f)
        self._connect_dirty(f)
        return widget

    def _connect_dirty(self, f):
        """Mark the field as dirty whenever the user changes the widget.

        Most signals fire on programmatic ``setX`` too (used during load), so
        we gate them on ``self._loading``. ``QComboBox.activated`` is the
        user-only signal but we still gate to be safe.
        """
        def _mark(*_):
            if not self._loading:
                f.dirty = True
        w = f.widget
        if isinstance(w, QtWidgets.QLineEdit):
            w.textChanged.connect(_mark)
        elif isinstance(w, QtWidgets.QSpinBox):
            w.valueChanged.connect(_mark)
        elif isinstance(w, QtWidgets.QCheckBox):
            w.toggled.connect(_mark)
        elif isinstance(w, QtWidgets.QComboBox):
            w.currentIndexChanged.connect(_mark)

    def _add_row(self, form, label, owner_path, attr, kind="line", **kw):
        if kind == "line":
            w, g, s = _line()
        elif kind == "line_req":
            w, g, s = _line_required()
        elif kind == "spin":
            w, g, s = _spin(**kw)
        elif kind == "check":
            w, g, s = _check()
        else:
            raise ValueError(kind)
        self._bind(owner_path, attr, w, g, s)
        form.addRow(label, w)
        return w

    def _add_file_row(self, form, label, owner_path, attr, caption):
        w, g, s = _line()
        self._bind(owner_path, attr, w, g, s)
        form.addRow(label, _file_picker(self, w, caption))
        return w

    # --- tabs -------------------------------------------------------------
    def _build_ib_tab(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)

        gb_conn = QtWidgets.QGroupBox("Gateway / TWS connection (Sources.IBSource)")
        f_conn = QtWidgets.QFormLayout(gb_conn)
        self._add_row(f_conn, "HostIB", ["Sources", "IBSource"], "HostIB", "line_req")
        self._add_row(f_conn, "PortIB", ["Sources", "IBSource"], "PortIB", "spin", minv=1, maxv=65535)
        self._add_row(f_conn, "IBSrvPort (sidecar)", ["Sources", "IBSource"], "IBSrvPort", "spin", minv=1, maxv=65535)
        outer.addWidget(gb_conn)

        gb_flex = QtWidgets.QGroupBox("Flex Web Service (TransactionHandlers.IB)")
        f_flex = QtWidgets.QFormLayout(gb_flex)
        self._add_row(f_flex, "FlexToken", ["TransactionHandlers", "IB"], "FlexToken")
        self._add_row(f_flex, "FlexQuery (numeric ID)", ["TransactionHandlers", "IB"], "FlexQuery")
        outer.addWidget(gb_flex)

        outer.addStretch(1)
        hint = QtWidgets.QLabel(
            "<i>See the Help tab for step-by-step instructions on generating "
            "a Flex token and finding the query ID.</i>"
        )
        hint.setWordWrap(True)
        outer.addWidget(hint)
        return page

    def _build_transactions_tab(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)

        gb_st = QtWidgets.QGroupBox("IB Activity Statement CSV (TransactionHandlers.IBStatement)")
        f_st = QtWidgets.QFormLayout(gb_st)
        self._add_file_row(f_st, "SrcFile", ["TransactionHandlers", "IBStatement"], "SrcFile",
                           "Pick IB Activity Statement CSV")
        self._add_row(f_st, "Portfolio name", ["TransactionHandlers", "IBStatement"], "PortofolioName")
        outer.addWidget(gb_st)

        gb_ms = QtWidgets.QGroupBox("My Stocks Portfolio CSV (TransactionHandlers.MyStocks)")
        f_ms = QtWidgets.QFormLayout(gb_ms)
        self._add_file_row(f_ms, "SrcFile", ["TransactionHandlers", "MyStocks"], "SrcFile",
                           "Pick My Stocks Portfolio CSV")
        self._add_row(f_ms, "Portfolio name", ["TransactionHandlers", "MyStocks"], "PortofolioName")
        outer.addWidget(gb_ms)

        outer.addStretch(1)
        return page

    def _build_rapid_tab(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)

        gb_sp = QtWidgets.QGroupBox("StockPricesHeaders (split / price lookups)")
        f_sp = QtWidgets.QFormLayout(gb_sp)
        self._add_row(f_sp, "X-RapidAPI-Host", ["StockPricesHeaders"], "X_RapidAPI_Host")
        self._add_row(f_sp, "X-RapidAPI-Key", ["StockPricesHeaders"], "X_RapidAPI_Key")
        outer.addWidget(gb_sp)

        gb_sa = QtWidgets.QGroupBox("SeekingAlphaHeaders (earnings / fundamentals)")
        f_sa = QtWidgets.QFormLayout(gb_sa)
        self._add_row(f_sa, "X-RapidAPI-Host", ["SeekingAlphaHeaders"], "X_RapidAPI_Host")
        self._add_row(f_sa, "X-RapidAPI-Key", ["SeekingAlphaHeaders"], "X_RapidAPI_Key")
        outer.addWidget(gb_sa)

        gb_jy = QtWidgets.QGroupBox("Jupyter notebook RapidAPI key")
        f_jy = QtWidgets.QFormLayout(gb_jy)
        self._add_row(f_jy, "RapidYFinanaceHost", ["Jupyter"], "RapidYFinanaceHost")
        self._add_row(f_jy, "RapidYFinanaceKey", ["Jupyter"], "RapidYFinanaceKey")
        outer.addWidget(gb_jy)

        gb_pg = QtWidgets.QGroupBox("Polygon (Sources.PolySource)")
        f_pg = QtWidgets.QFormLayout(gb_pg)
        self._add_row(f_pg, "Polygon API Key", ["Sources", "PolySource"], "Key")
        outer.addWidget(gb_pg)

        outer.addStretch(1)
        return page

    def _build_input_tab(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QFormLayout(page)

        from common.common import InputSourceType  # noqa
        cb = QtWidgets.QComboBox()
        members = [m for m in InputSourceType]
        for m in members:
            cb.addItem(m.name, m)
        def get(w):
            return w.currentData()
        def setv(w, v):
            for i in range(w.count()):
                if w.itemData(i) == v or (hasattr(v, "name") and w.itemText(i) == v.name):
                    w.setCurrentIndex(i)
                    return
        self._bind(["Input"], "InputSource", cb, get, setv)
        outer.addRow("Input.InputSource", cb)

        return page

    def _build_behavior_tab(self):
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)

        gb_tx = QtWidgets.QGroupBox("Transactions (TransactionHandlers)")
        f_tx = QtWidgets.QFormLayout(gb_tx)
        self._add_row(f_tx, "JustFromTheEndOfMyStock", ["TransactionHandlers"],
                      "JustFromTheEndOfMyStock", "check")
        self._add_row(f_tx, "SaveCaches", ["TransactionHandlers"], "SaveCaches", "check")
        self._add_row(f_tx, "IncludeNormalizedOnSave", ["TransactionHandlers"],
                      "IncludeNormalizedOnSave", "check")
        outer.addWidget(gb_tx)

        gb_ib = QtWidgets.QGroupBox("IB Flex (TransactionHandlers.IB)")
        f_ib = QtWidgets.QFormLayout(gb_ib)
        self._add_row(f_ib, "DoQuery", ["TransactionHandlers", "IB"], "DoQuery", "check")
        self._add_row(f_ib, "PromptOnQueryFail", ["TransactionHandlers", "IB"],
                      "PromptOnQueryFail", "check")
        self._add_row(f_ib, "OnlyNewerThanIBStatement", ["TransactionHandlers", "IB"],
                      "OnlyNewerThanIBStatement", "check")
        outer.addWidget(gb_ib)

        gb_src = QtWidgets.QGroupBox("IB sidecar (Sources.IBSource)")
        f_src = QtWidgets.QFormLayout(gb_src)
        self._add_row(f_src, "PromptOnConnectionFail", ["Sources", "IBSource"],
                      "PromptOnConnectionFail", "check")
        outer.addWidget(gb_src)

        gb_run = QtWidgets.QGroupBox("Running")
        f_run = QtWidgets.QFormLayout(gb_run)

        from common.common import VerifySave  # noqa
        cb_vs = QtWidgets.QComboBox()
        for m in VerifySave:
            cb_vs.addItem(m.name, m)
        def _vs_get(w):
            return w.currentData()
        def _vs_set(w, v):
            for i in range(w.count()):
                if w.itemData(i) == v or (hasattr(v, "name") and w.itemText(i) == v.name):
                    w.setCurrentIndex(i)
                    return
        self._bind(["Running"], "VerifySaving", cb_vs, _vs_get, _vs_set)
        f_run.addRow("VerifySaving", cb_vs)

        self._add_row(f_run, "LoadLastAtBegin", ["Running"], "LoadLastAtBegin", "check")
        outer.addWidget(gb_run)

        outer.addStretch(1)
        return page

    def _build_help_tab(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        view = QtWidgets.QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setHtml(HELP_TEXT)
        lay.addWidget(view)
        return page


def main(argv=None):
    parser = argparse.ArgumentParser(description="compare-my-stocks small config GUI")
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to myconfig.yaml (default: ~/.compare_my_stocks/myconfig.yaml)")
    args = parser.parse_args(argv)

    path = args.config or _default_config_path()
    if not path.exists():
        print(f"Config file not found: {path}", file=sys.stderr)
        return 2

    app = QtWidgets.QApplication(sys.argv)
    win = ConfigEditor(path)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
