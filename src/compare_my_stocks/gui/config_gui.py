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


def _load_yaml(path: Path):
    """Load the yaml using the project's unsafe loader (preserves enum tags)."""
    from config.newconfig import ConfigLoader

    yaml = ConfigLoader.get_yaml()
    with open(path, "rt", encoding="utf-8") as f:
        return yaml, yaml.load(f)


def _dump_yaml(yaml, cfg, path: Path) -> None:
    with open(path, "wt", encoding="utf-8") as f:
        yaml.dump(cfg, f)


class _Field:
    """One row of the form, bound to ``getattr/setattr`` on a config object."""

    def __init__(self, owner, attr, widget, getter, setter):
        self.owner = owner
        self.attr = attr
        self.widget = widget
        self.getter = getter  # widget -> value
        self.setter = setter  # widget, value -> None

    def load(self):
        if self.owner is None:
            return
        val = getattr(self.owner, self.attr, None)
        self.setter(self.widget, val)

    def save(self):
        if self.owner is None:
            return
        setattr(self.owner, self.attr, self.getter(self.widget))


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

        self.yaml = None
        self.cfg = None
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

        for f in self._fields:
            f.load()

        self.statusBar().showMessage(f"Loaded {path}")

    # --- io ---------------------------------------------------------------
    def _load(self):
        try:
            self.yaml, self.cfg = _load_yaml(self.path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Load failed",
                f"Could not load {self.path}:\n\n{e}\n\n{traceback.format_exc()}",
            )
            raise

    def reload(self):
        self._load()
        for f in self._fields:
            f.owner = self._resolve_owner(f.owner_path)
            f.load()
        self.statusBar().showMessage(f"Reloaded {self.path}")

    def save(self):
        for f in self._fields:
            try:
                f.save()
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Save warning",
                    f"Could not write field {f.attr}: {e}",
                )
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self.path.with_suffix(self.path.suffix + f".bak.{ts}")
            shutil.copy2(self.path, backup)
            _dump_yaml(self.yaml, self.cfg, self.path)
            self.statusBar().showMessage(f"Saved {self.path} (backup: {backup.name})")
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
        return widget

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
