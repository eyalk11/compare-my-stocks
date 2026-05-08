"""Snapshot of the *current graph* in the running app.

Combines two things:
  1. The latest `update_graph called with params:` line in ~/.compare_my_stocks/log.txt
     — i.e. what params the user last asked the engine to plot.
  2. The Serialized snapshot at config.File.DataFilePtr — i.e. what actually got
     rendered (columns/series, date range, value range, last-row totals).

Usage:
    python scripts/inspect_graph.py [<symbol> ...]

Pass symbol names to filter the per-series last-row table.
"""
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(SRC, "compare_my_stocks"))

import pickle  # noqa: E402

from config import config  # noqa: E402
from common.serialization import is_json_file, load_serialized  # noqa: E402


LOG_PATH = os.path.expanduser("~/.compare_my_stocks/log.txt")
UPDATE_RE = re.compile(rb"update_graph called with params:")


def _tail_last_update_graph(path, max_bytes=4 * 1024 * 1024):
    if not os.path.exists(path):
        print(f"log: {path} missing")
        return
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()  # discard partial line
        tail = f.read()
    matches = [ln for ln in tail.splitlines() if UPDATE_RE.search(ln)]
    if not matches:
        print(f"log: no `update_graph called` lines found in last {max_bytes} bytes")
        return
    line = matches[-1].decode("utf-8", errors="replace")
    print(f"log: {path}")
    print(f"calls in tail: {len(matches)}")
    print("last update_graph call:")
    print(f"  {line}")


def _load_data():
    ptr = config.File.DataFilePtr
    if not os.path.exists(ptr):
        print(f"\nDataFilePtr {ptr} missing — has the app generated a graph?")
        return None
    target = open(ptr).read().strip()
    if not os.path.exists(target):
        print(f"\ntarget {target} (from {ptr}) missing")
        return None
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(target))
    age = datetime.datetime.now() - mtime
    print(f"\ndata file: {target}")
    print(f"age:       {age} (mtime {mtime})")
    if is_json_file(target):
        return load_serialized(target)
    return pickle.load(open(target, "rb"))


def _graph_summary(data, filter_syms=None):
    if data is None:
        return
    act = data.act
    if act is None or act.df is None:
        print("act.df is None — nothing was plotted")
        return
    df = act.df
    print(f"\nplotted frame:")
    print(f"  shape   = {df.shape}")
    print(f"  columns = {list(df.columns)}")
    if not df.empty:
        print(f"  date range = {df.index[0]}  →  {df.index[-1]}")
        try:
            vmin = float(df.min().min())
            vmax = float(df.max().max())
            print(f"  value range = {vmin:,.2f}  →  {vmax:,.2f}")
        except Exception as e:
            print(f"  (value range failed: {e})")

        last = df.iloc[-1].dropna()
        if filter_syms:
            last = last[[s for s in filter_syms if s in last.index]]
        print(f"\nlast-row series ({df.index[-1]}):")
        for sym, val in sorted(last.items(), key=lambda kv: -abs(float(kv[1])) if kv[1] == kv[1] else 0):
            print(f"  {sym:<24} {float(val):>14,.2f}")
        try:
            print(f"  {'TOTAL':<24} {float(last.sum()):>14,.2f}")
        except Exception:
            pass

    params = data.parameters
    if params is not None:
        print("\nrendered params (from snapshot):")
        for attr in (
            "type", "unite_by_group", "groups", "_ext", "_selected_stocks",
            "_fromdate", "_todate", "compare_with", "adjusted_for_base_cur",
            "currency_to_adjust", "weighted_for_portfolio", "isline",
            "limit_by", "limit_to_portfolio", "show_transactions_graph",
        ):
            try:
                print(f"  {attr:<22} = {getattr(params, attr)}")
            except AttributeError:
                pass


if __name__ == "__main__":
    syms = [s.upper() for s in sys.argv[1:]] or None
    _tail_last_update_graph(LOG_PATH)
    data = _load_data()
    _graph_summary(data, filter_syms=syms)
