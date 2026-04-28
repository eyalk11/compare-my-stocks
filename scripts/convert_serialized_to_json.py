"""One-shot: convert a pickle ``Serialized`` data file to the new JSON format.

Usage:
    python scripts/convert_serialized_to_json.py <input.pkl> [<output.json>]

If <output.json> is omitted, writes alongside the input with a ``.json``
suffix.  The original file is left untouched.
"""
import pickle
import sys
from pathlib import Path

# Make ``src`` importable when run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT / "src" / "compare_my_stocks"))

from common.serialization import dump_serialized  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 1
    src = Path(argv[1])
    dst = Path(argv[2]) if len(argv) > 2 else src.with_suffix(src.suffix + ".json")
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2
    with open(src, "rb") as f:
        data = pickle.load(f)
    dump_serialized(data, dst)
    print(f"wrote {dst} ({dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
