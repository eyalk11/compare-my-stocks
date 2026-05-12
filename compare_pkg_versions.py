"""Compare installed package versions between two Python interpreters.

Usage:
    python compare_pkg_versions.py                     # default: .venv11b vs .venv314
    python compare_pkg_versions.py <left> <right>      # custom interpreter paths or labels

Known labels: venv11, venv11b, venv11temp, venv314, venv314b, py311 (pyenv 3.11).
"""
import subprocess
import json
import sys

PACKAGES = [
    "colorlog", "django", "numpy", "ruamel.yaml", "pydantic", "dacite",
    "requests", "pyside6", "matplotlib", "pandas", "python-dateutil", "pytz",
    "qtvoila", "superqt", "mplcursors", "ib-insync", "pyro5", "ibflex",
    "six", "psutil", "dataconf", "toml", "pytest", "ipykernel", "setuptools",
    "nbformat", "memoization", "notebook", "json-editor-pyside6",
    "qt-collapsible-section-pyside6", "jupyter-server", "ipydatagrid", "joblib",
    "polygon-api-client", "multimethod", "ordered-set", "voila",
    "python-composition", "numerize", "ib-async", "pywin32",
    "compare-my-stocks",
]

REPO = r"C:\autoproj\compare-my-stocks"
LABELS = {
    "venv11":     rf"{REPO}\.venv11\Scripts\python.exe",
    "venv11b":    rf"{REPO}\.venv11b\Scripts\python.exe",
    "venv11temp": rf"{REPO}\.venv11temp\Scripts\python.exe",
    "venv314":    rf"{REPO}\.venv314\Scripts\python.exe",
    "venv314b":   rf"{REPO}\.venv314b\Scripts\python.exe",
    "py311":      r"C:\Users\ekarni\.pyenv\pyenv-win\versions\3.11\python.exe",
}

DEFAULT_LEFT = "venv11b"
DEFAULT_RIGHT = "venv314"


def resolve(arg: str) -> tuple[str, str]:
    """Return (label, path) for a CLI arg (label or absolute path)."""
    if arg in LABELS:
        return arg, LABELS[arg]
    return arg, arg


def get_versions(python_cmd: str) -> dict[str, tuple[str, str | None]]:
    """Return {name: (version, editable_path_or_None)}."""
    try:
        all_out = subprocess.run(
            [python_cmd, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        edit_out = subprocess.run(
            [python_cmd, "-m", "pip", "list", "-e", "--format=json"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        pkgs = json.loads(all_out)
        edits = {
            p["name"].lower().replace("_", "-"): p.get("editable_project_location") or p.get("location")
            for p in json.loads(edit_out)
        }
        return {
            p["name"].lower().replace("_", "-"): (p["version"], edits.get(p["name"].lower().replace("_", "-")))
            for p in pkgs
        }
    except Exception as e:
        print(f"Failed to query {python_cmd}: {e}", file=sys.stderr)
        return {}


def fmt(entry: tuple[str, str | None] | str) -> str:
    if entry == "—":
        return "—"
    ver, path = entry
    return f"{ver} (-e {path})" if path else ver


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        left_label, left_path = resolve(DEFAULT_LEFT)
        right_label, right_path = resolve(DEFAULT_RIGHT)
    elif len(args) == 2:
        left_label, left_path = resolve(args[0])
        right_label, right_path = resolve(args[1])
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    print(f"Querying {left_label} → {left_path}...")
    vleft = get_versions(left_path)
    print(f"Querying {right_label} → {right_path}...")
    vright = get_versions(right_path)

    col = 32
    vcol = 40
    header = f"{'Package':<{col}} {left_label:<{vcol}} {right_label:<{vcol}} {'Match'}"
    print("\n" + header)
    print("-" * len(header))

    different = []
    missing = []

    for pkg in sorted(PACKAGES, key=str.lower):
        key = pkg.lower().replace("_", "-")
        vl = vleft.get(key, "—")
        vr = vright.get(key, "—")
        if vl == "—" or vr == "—":
            status = "MISSING"
            missing.append(pkg)
        elif vl == vr:
            status = "ok"
        else:
            status = "DIFF"
            different.append(pkg)
        print(f"{pkg:<{col}} {fmt(vl):<{vcol}} {fmt(vr):<{vcol}} {status}")

    print()
    if different:
        print(f"Version differences ({len(different)}): {', '.join(different)}")
    if missing:
        print(f"Missing in one env ({len(missing)}): {', '.join(missing)}")
    if not different and not missing:
        print("All packages match.")


if __name__ == "__main__":
    main()
