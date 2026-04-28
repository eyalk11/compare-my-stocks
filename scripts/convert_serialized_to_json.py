"""One-shot: convert a pickle ``Serialized`` data file to the new JSON format.

Usage:
    python scripts/convert_serialized_to_json.py <input.pkl> [<output.json>]

If <output.json> is omitted, writes alongside the input with a ``.json``
suffix.  The original file is left untouched.

Older pickles (pre-Groups, pre-parameters) are accepted: missing fields
get filled with ``None`` / empty dict.
"""
import pickle
import sys
from collections import namedtuple
from pathlib import Path

# Make ``src`` importable when run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "src" / "compare_my_stocks"))

from common import common as _common  # noqa: E402
from common.common import Serialized  # noqa: E402
from common.serialization import dump_serialized  # noqa: E402

# Schema variants seen in the wild, oldest first.  The current shape is
# the last entry and matches ``common.common.Serialized``.
_HISTORICAL_FIELDS = [
    ("origdata", "beforedata", "afterdata", "act"),
    ("origdata", "beforedata", "afterdata", "act", "parameters"),
    ("origdata", "beforedata", "afterdata", "act", "parameters", "Groups"),
]


def _load_with_compat(path: Path):
    """Try loading ``path`` against each historical schema until one fits."""
    last_err = None
    original_cls = _common.Serialized
    try:
        for fields in _HISTORICAL_FIELDS:
            _common.Serialized = namedtuple("Serialized", list(fields))
            try:
                with open(path, "rb") as f:
                    raw = pickle.load(f)
                return raw, fields
            except TypeError as e:
                last_err = e
                continue
        raise RuntimeError(f"no schema variant accepted the file: {last_err}")
    finally:
        _common.Serialized = original_cls


def _upgrade(raw, fields) -> Serialized:
    values = {f: getattr(raw, f) for f in fields}
    return Serialized(
        origdata=values.get("origdata"),
        beforedata=values.get("beforedata"),
        afterdata=values.get("afterdata"),
        act=values.get("act"),
        parameters=values.get("parameters"),
        Groups=values.get("Groups") or {},
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1
    src = Path(argv[1])
    dst = Path(argv[2]) if len(argv) > 2 else src.with_suffix(src.suffix + ".json")
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2
    raw, fields = _load_with_compat(src)
    print(f"loaded with {len(fields)}-field schema: {fields}")
    data = _upgrade(raw, fields)
    dump_serialized(data, dst)
    print(f"wrote {dst} ({dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
