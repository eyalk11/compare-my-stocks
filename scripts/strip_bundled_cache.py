"""Strip ib_insync/ib_async Contract objects from a HistFile.cache before bundling.

The bundled cache must be loadable on installs that don't have ib_insync (e.g. the
[full_no_ib] / [mini] extras). symbol_info[sym]['contract'] holds an
ib_insync.contract.Contract instance, which would raise ImportError on unpickle in
those environments. The scalar contract fields (conId, exchange, currency, ...) are
already duplicated as top-level keys in symbol_info[sym], so dropping 'contract'
loses nothing the rest of the code depends on.

Usage:
    python strip_bundled_cache.py [path/to/HistFile.cache]

Default path is src/compare_my_stocks/data/HistFile.cache. Writes in place; a .pre_strip
backup is kept next to the file the first time we touch it.
"""
import pickle
import shutil
import sys
from pathlib import Path

DEFAULT = Path(__file__).parent / "src" / "compare_my_stocks" / "data" / "HistFile.cache"


def strip(path: Path) -> None:
    with path.open("rb") as f:
        hist_by_date, symbinfo, cache_date, currency_hist, tail = pickle.load(f)

    stripped = 0
    for sym, info in symbinfo.items():
        if isinstance(info, dict) and info.pop("contract", None) is not None:
            stripped += 1

    backup = path.with_suffix(path.suffix + ".pre_strip")
    if not backup.exists():
        shutil.copy2(path, backup)

    with path.open("wb") as f:
        pickle.dump((hist_by_date, symbinfo, cache_date, currency_hist, tail), f)

    print(f"stripped 'contract' from {stripped}/{len(symbinfo)} symbols in {path}")
    print(f"backup: {backup}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not target.exists():
        sys.exit(f"not found: {target}")
    strip(target)
