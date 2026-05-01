"""Standalone snapshot of the current portfolio data, similar to what the
embedded Jupyter notebook sees via `load_data()`.

Usage:  python inspect_data.py [<symbol> ...]

Prints:
- Source file path + age
- Parameters used to build the snapshot
- Group definitions
- Per-symbol latest holding × price (= value), cost basis, unrealized P/L
- Portfolio total value
- Optional per-symbol filter when symbols are passed on the cmdline.
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(SRC, "compare_my_stocks"))

import pickle  # noqa: E402

from config import config  # noqa: E402
from common.serialization import is_json_file, load_serialized  # noqa: E402


def _load():
    ptr = config.File.DataFilePtr
    if not os.path.exists(ptr):
        raise SystemExit(f"DataFilePtr {ptr} missing — has the app run?")
    target = open(ptr).read().strip()
    if not os.path.exists(target):
        raise SystemExit(f"target {target} (from {ptr}) missing")
    age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(target))
    print(f"data file: {target}")
    print(f"age:       {age} (mtime {datetime.datetime.fromtimestamp(os.path.getmtime(target))})")
    if is_json_file(target):
        return load_serialized(target)
    return pickle.load(open(target, "rb"))


def _portfolio_summary(data, filter_syms=None):
    act = data.act
    if act is None:
        print("act is None — nothing to summarize")
        return
    df = act.df
    bef = data.beforedata
    after = data.afterdata
    print(f"\nact.df shape: {df.shape if df is not None else None}")
    print(f"beforedata shape: {bef.shape if bef is not None else None}")
    print(f"afterdata shape: {after.shape if after is not None else None}")

    # `act.df` has the per-symbol series the GUI plotted. Take the last row.
    if df is None or df.empty:
        print("act.df empty")
    else:
        last = df.iloc[-1].dropna()
        if filter_syms:
            last = last[[s for s in filter_syms if s in last.index]]
        print(f"\nLast-row snapshot ({df.index[-1]}):")
        for sym, val in sorted(last.items(), key=lambda kv: -abs(float(kv[1])) if kv[1] == kv[1] else 0):
            print(f"  {sym:<24} {float(val):>14,.2f}")
        try:
            total = float(last.sum())
            print(f"  {'TOTAL':<24} {total:>14,.2f}")
        except Exception as e:
            print(f"  (sum failed: {e})")

    # Parameters
    params = data.parameters
    if params is not None:
        print("\nparameters:")
        try:
            print(f"  type            = {params.type}")
            print(f"  unite_by_group  = {params.unite_by_group}")
            print(f"  groups          = {params.groups}")
            print(f"  ext             = {params._ext}")
            print(f"  selected_stocks = {params._selected_stocks}")
            print(f"  fromdate        = {params._fromdate}")
            print(f"  todate          = {params._todate}")
            print(f"  adjusted_for_base_cur = {params.adjusted_for_base_cur}")
            print(f"  currency_to_adjust    = {params.currency_to_adjust}")
            print(f"  weighted_for_portfolio= {params.weighted_for_portfolio}")
        except AttributeError as e:
            print(f"  (param attr missing: {e}); raw: {params!r}")

    # Groups
    if data.Groups:
        print(f"\ngroups: {len(data.Groups)} defined")
        for g, syms in list(data.Groups.items())[:10]:
            syms = list(syms)
            head = ", ".join(syms[:8])
            more = "" if len(syms) <= 8 else f" … (+{len(syms) - 8})"
            print(f"  {g}: {head}{more}")


if __name__ == "__main__":
    syms = [s.upper() for s in sys.argv[1:]] or None
    data = _load()
    _portfolio_summary(data, filter_syms=syms)
