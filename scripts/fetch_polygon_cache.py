"""Build a HistFile.cache seed via Polygon, reusing InputProcessor + PolySource.

Drives the real pipeline (same construction as the inp_poly test fixture in
src/compare_my_stocks/tests/testtools.py) so the on-disk cache shape stays
consistent with whatever inputdata.save_data writes. The PolySource path
populates symbol_info as plain dicts, so the result is bundle-safe (no
ib_insync.Contract) for [full_no_ib] / [mini] installs.

Usage:
    python fetch_polygon_cache.py [--symbols AAPL,QQQ,...] [--years 5]
                                  [--currencies ILS,EUR,...]
                                  [--out path/to/HistFile.cache]
                                  [--key POLYGON_API_KEY]

Defaults: symbols = union of groups in ~/.compare_my_stocks/groups.json
(alpha-numeric tickers only; crypto-style names skipped) or a small fallback.
Currencies default to "ILS" so cache-only test_adjust_currency can resolve
USD→ILS without a live IB Gateway.
Output: src/compare_my_stocks/data/HistFile.cache.
API key: --key, $POLYGON_API_KEY, or config.Sources.PolySource.Key in myconfig.yaml.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from copy import copy
from pathlib import Path
from unittest.mock import MagicMock, Mock

REPO = Path(__file__).resolve().parent.parent  # scripts/ is one below repo root
SRC = REPO / "src"
PKG = SRC / "compare_my_stocks"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(PKG))

# Has to be set before importing the package, since runsit/config import on load.
os.environ.setdefault("SILENT", "False")
import builtins  # noqa: E402

builtins.SILENT = False  # type: ignore[attr-defined]

DEFAULT_OUT = PKG / "data" / "HistFile.cache"
FALLBACK_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
                    "QQQ", "SPY", "VOO", "VTI"]


def discover_symbols() -> list[str]:
    groups_path = Path.home() / ".compare_my_stocks" / "groups.json"
    if not groups_path.exists():
        return FALLBACK_SYMBOLS
    try:
        data = json.loads(groups_path.read_text())
    except Exception as e:
        logging.warning(f"could not parse {groups_path}: {e}")
        return FALLBACK_SYMBOLS
    syms: set[str] = set()

    def walk(node):
        if isinstance(node, list):
            for s in node:
                if isinstance(s, str):
                    syms.add(s)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(data)
    cleaned = [s for s in syms if s.isupper() and s.replace(".", "").replace("-", "").isalnum()]
    return sorted(cleaned) or FALLBACK_SYMBOLS


def _fetch_currency_hist(client, currencies_csv: str, startdate, enddate):
    """Build a currency_hist DataFrame with MultiIndex columns
    (CUR, OHLC-field) matching the live-cache shape. Empty DF on no
    currencies or empty result."""
    import pandas
    if not currencies_csv.strip():
        return pandas.DataFrame()
    codes = [c.strip().upper() for c in currencies_csv.split(",") if c.strip()]
    frames = []
    for code in codes:
        ticker = f"C:USD{code}"  # Polygon FX format
        try:
            aggs = list(client.list_aggs(
                ticker=ticker, multiplier=1, adjusted=True, timespan="day",
                from_=startdate.date(), to=enddate.date(), limit=5000))
        except Exception as e:
            logging.warning(f"FX fetch failed for {ticker}: {e}")
            continue
        if not aggs:
            logging.warning(f"FX fetch returned no bars for {ticker}")
            continue
        df = pandas.DataFrame(aggs).rename(
            columns={"open": "Open", "close": "Close", "high": "High", "low": "Low"})
        df["date"] = df["timestamp"].apply(
            lambda x: datetime.datetime.fromtimestamp(x / 1000).date())
        df["date"] = pandas.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df = df[["Open", "Close", "High", "Low"]]
        df.columns = pandas.MultiIndex.from_product([[code], df.columns])
        frames.append(df)
        logging.info(f"FX {code}: {len(df)} bars [{df.index.min().date()} .. {df.index.max().date()}]")
    if not frames:
        return pandas.DataFrame()
    return pandas.concat(frames, axis=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", help="comma-separated tickers; default: groups.json or fallback")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--months", type=int, default=None,
                    help="If set, overrides --years (window = months*30 days).")
    ap.add_argument("--currencies", default="ILS",
                    help="comma-separated currency codes vs USD (e.g. ILS,EUR). "
                         "Empty string disables FX fetch.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--key", help="Polygon API key (else POLYGON_API_KEY env or myconfig.yaml)")
    ap.add_argument("--no-strip", action="store_true",
                    help="Skip the strip_bundled_cache post-step.")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    # Imports must follow sys.path tweaks above.
    from common.common import Types, UniteType, UseCache, InputSourceType  # noqa: E402
    from config import config  # noqa: E402
    from engine.parameters import Parameters  # noqa: E402
    from input.inputdata import InputDataImpl  # noqa: E402
    from input.inputprocessor import InputProcessor  # noqa: E402
    from input.polygon import PolySource  # noqa: E402
    from transactions.transactionhandlermanager import TransactionHandlerManager  # noqa: E402

    api_key = args.key or os.environ.get("POLYGON_API_KEY") \
        or getattr(getattr(config.Sources, "PolySource", None), "Key", None)
    if not api_key:
        sys.exit("no Polygon API key (use --key, POLYGON_API_KEY env, or set Sources.PolySource.Key)")
    config.Sources.PolySource.Key = api_key
    config.Input.InputSource = InputSourceType.Polygon
    config.TransactionHandlers.SaveCaches = False
    # ForceSave — skips the QMessageBox prompt (which needs a QApplication)
    # AND the DONT-branch early return that would otherwise skip writing the
    # file when no prior cache was loaded.
    from common.common import VerifySave  # noqa: E402
    config.Running.VerifySaving = VerifySave.ForceSave
    config.File.HistF = str(args.out.resolve())
    config.File.HistFBackup = str(args.out.resolve()) + ".back"
    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Backup any existing cache before overwriting — easy revert if the
    # regenerated cache is broken or missing expected symbols/currencies.
    if args.out.exists():
        import shutil
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = args.out.with_name(args.out.name + f".bak.{ts}")
        shutil.copy2(args.out, backup)
        logging.info(f"backed up existing cache → {backup}")

    symbols = ([s.strip().upper() for s in args.symbols.split(",")]
               if args.symbols else discover_symbols())
    enddate = datetime.datetime.now(tz=datetime.timezone.utc)
    if args.months is not None:
        startdate = enddate - datetime.timedelta(days=30 * args.months)
        window_label = f"{args.months}m"
    else:
        startdate = enddate - datetime.timedelta(days=365 * args.years)
        window_label = f"{args.years}y"
    logging.info(f"fetching {len(symbols)} symbols, {window_label} window -> {args.out}")

    # Same construction as tests/testtools.py::inp_poly.
    eng = MagicMock()
    params = Parameters(
        type=Types.PRICE, unite_by_group=UniteType.NONE, isline=True,
        use_groups=False, use_ext=False,
        _selected_stocks=symbols, groups=[], _ext=[],
        use_cache=UseCache.DONT, show_graph=False,
    )
    params._fromdate = startdate
    params._todate = enddate
    params.transactions_fromdate = startdate
    params.transactions_todate = enddate
    eng.params = params
    # required_syms() is called inside process_history; return our symbol set.
    eng.required_syms = Mock(return_value=set(symbols))

    import pandas  # noqa: E402

    poly = PolySource(notify=lambda msg: logging.warning(f"poly: {msg}"))
    tr = TransactionHandlerManager(None)
    tr._buydic = {}  # process_transactions is stubbed out, so initialize what buydic property returns
    inp = InputProcessor(eng, tr, poly)
    inp.data = InputDataImpl(semaphore=inp._semaphore)
    inp.data.currency_hist = _fetch_currency_hist(
        poly.client, args.currencies, startdate, enddate)
    tr._inp = inp
    inp.process_params = copy(params)
    inp.process_params.use_cache = UseCache.DONT

    # Skip transaction processing entirely — we only want price history.
    inp.process_transactions = lambda: None

    inp.process(set(), params=params)

    inp.save_data()
    if not args.out.exists():
        logging.error("save_data did not produce a file")
        return 1
    logging.info(f"wrote {args.out} ({args.out.stat().st_size/1e6:.1f} MB, "
                 f"{len(inp.data._hist_by_date)} dates, {len(inp.data.symbol_info)} symbols)")

    if not args.no_strip:
        # Polygon path already produces plain-dict symbol_info, so the strip
        # step is usually a no-op, but it guarantees the bundle stays
        # importable on environments without ib_insync.
        try:
            from strip_bundled_cache import strip as _strip
            _strip(args.out)
        except Exception as e:
            logging.warning(f"strip step skipped: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
