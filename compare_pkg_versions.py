"""Compare installed package versions between two Python interpreters."""
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
]

PYTHON_39 = r"C:\autoproj\compare-my-stocks\.venv11\Scripts\python.exe"
PYTHON_311 = r"C:\Users\ekarni\.pyenv\pyenv-win\versions\3.11\python.exe"


def get_versions(python_cmd: str) -> dict[str, str]:
    cmd = [python_cmd, "-m", "pip", "list", "--format=json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        pkgs = json.loads(result.stdout)
        return {p["name"].lower().replace("_", "-"): p["version"] for p in pkgs}
    except Exception as e:
        print(f"Failed to query {python_cmd}: {e}", file=sys.stderr)
        return {}


def main():
    print(f"Querying {PYTHON_39}...")
    v39 = get_versions(PYTHON_39)
    print(f"Querying {PYTHON_311}...")
    v311 = get_versions(PYTHON_311)

    col = 32
    header = f"{'Package':<{col}} {'venv11':<20} {'Python 3.11':<20} {'Match'}"
    print("\n" + header)
    print("-" * len(header))

    different = []
    missing = []

    for pkg in PACKAGES:
        key = pkg.lower().replace("_", "-")
        ver39 = v39.get(key, "—")
        ver311 = v311.get(key, "—")
        if ver39 == "—" or ver311 == "—":
            status = "MISSING"
            missing.append(pkg)
        elif ver39 == ver311:
            status = "ok"
        else:
            status = "DIFF"
            different.append(pkg)
        print(f"{pkg:<{col}} {ver39:<20} {ver311:<20} {status}")

    print()
    if different:
        print(f"Version differences ({len(different)}): {', '.join(different)}")
    if missing:
        print(f"Missing in one env ({len(missing)}): {', '.join(missing)}")
    if not different and not missing:
        print("All packages match.")


if __name__ == "__main__":
    main()
